"""Approval service — the human-in-the-loop control plane.

Sensitive actions follow:  REQUEST → (human decides) → EXECUTE / REJECT.
Nothing in this service ever performs the underlying action; connectors in
later phases will consume *approved* requests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aitzaz_api.core.errors import ConflictError, NotFoundError
from aitzaz_api.models.activity import ActivityType
from aitzaz_api.models.approval import APPROVAL_STATUSES, Approval, ApprovalStatus
from aitzaz_api.models.task import Task, TaskStatus
from aitzaz_api.models.user import User
from aitzaz_api.services.activity_service import log_activity

#: Pending approvals auto-expire after this long.
APPROVAL_TTL_HOURS = 72


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def sweep_expired(db: Session, *, user: User) -> int:
    """Mark stale pending approvals as expired. Returns count."""
    rows = db.scalars(
        select(Approval).where(
            Approval.user_id == user.id,
            Approval.status == ApprovalStatus.PENDING,
            Approval.expires_at.is_not(None),
            Approval.expires_at < _now(),
        )
    ).all()
    for approval in rows:
        approval.status = ApprovalStatus.EXPIRED
    if rows:
        db.commit()
    return len(rows)


def create_request(
    db: Session,
    *,
    user: User,
    action_type: str,
    description: str,
    payload: dict[str, Any] | None = None,
    task_id: str | None = None,
    source: str = "user",
    ip: str | None = None,
) -> Approval:
    linked_task: Task | None = None
    if task_id:
        try:
            tid = uuid.UUID(task_id)
        except ValueError:
            raise NotFoundError("Linked task not found") from None
        linked_task = db.scalar(select(Task).where(Task.id == tid, Task.user_id == user.id))
        if linked_task is None:
            raise NotFoundError("Linked task not found")
        if linked_task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL):
            raise ConflictError(f"Task is {linked_task.status} and cannot receive approvals")

    now = _now()
    approval = Approval(
        user_id=user.id,
        task_id=linked_task.id if linked_task else None,
        action_type=action_type.strip().lower(),
        description=description.strip(),
        payload=payload or {},
        status=ApprovalStatus.PENDING,
        requested_at=now,
        expires_at=now + timedelta(hours=APPROVAL_TTL_HOURS),
    )
    db.add(approval)
    db.flush()

    if linked_task is not None and linked_task.status != TaskStatus.WAITING_APPROVAL:
        linked_task.status = TaskStatus.WAITING_APPROVAL

    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.APPROVAL_REQUESTED,
        message=f"Approval requested: {approval.action_type} — {approval.description[:100]}",
        meta={"approval_id": str(approval.id), "source": source, "action_type": approval.action_type},
        ip=ip,
    )
    db.commit()
    db.refresh(approval)
    return approval


def create_request_tool_payload(
    db: Session,
    *,
    user: User,
    action_type: str,
    description: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shaped for the agent's approval_request tool (chat flow owns commit)."""
    approval = create_request(
        db,
        user=user,
        action_type=action_type,
        description=description,
        payload=payload or {},
        source="agent",
    )
    return {
        "id": str(approval.id),
        "action_type": approval.action_type,
        "status": approval.status,
    }


def list_approvals(
    db: Session,
    *,
    user: User,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Approval], int]:
    sweep_expired(db, user=user)
    query = select(Approval).where(Approval.user_id == user.id)
    count_query = select(func.count(Approval.id)).where(Approval.user_id == user.id)
    if status:
        if status not in APPROVAL_STATUSES:
            raise NotFoundError(f"Unknown approval status '{status}'")
        query = query.where(Approval.status == status)
        count_query = count_query.where(Approval.status == status)
    total = int(db.scalar(count_query) or 0)
    rows = db.scalars(
        query.order_by(Approval.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return list(rows), total


def get_approval(db: Session, *, user: User, approval_id: str) -> Approval:
    try:
        aid = uuid.UUID(approval_id)
    except ValueError:
        raise NotFoundError("Approval not found") from None
    approval = db.scalar(select(Approval).where(Approval.id == aid, Approval.user_id == user.id))
    if approval is None:
        raise NotFoundError("Approval not found")
    return approval


def decide(
    db: Session,
    *,
    user: User,
    approval_id: str,
    decision: str,
    note: str | None = None,
    ip: str | None = None,
) -> Approval:
    decision = decision.strip().lower()
    if decision not in ("approved", "rejected"):
        raise NotFoundError("decision must be 'approved' or 'rejected'")

    approval = get_approval(db, user=user, approval_id=approval_id)
    if approval.status != ApprovalStatus.PENDING:
        raise ConflictError(
            f"This request was already {approval.status}. Only pending requests can be decided."
        )

    approval.status = decision
    approval.decided_at = _now()
    approval.decision_note = note

    if approval.task_id is not None:
        task = db.get(Task, approval.task_id)
        if task is not None and task.status == TaskStatus.WAITING_APPROVAL:
            task.status = TaskStatus.PENDING if decision == "approved" else TaskStatus.CANCELLED

    activity_type = (
        ActivityType.APPROVAL_APPROVED if decision == "approved" else ActivityType.APPROVAL_REJECTED
    )
    log_activity(
        db,
        user_id=user.id,
        activity_type=activity_type,
        message=f"Approval {decision}: {approval.action_type} — {approval.description[:100]}",
        meta={"approval_id": str(approval.id), "note": note},
        ip=ip,
    )
    db.commit()
    db.refresh(approval)
    return approval


def count_pending(db: Session, *, user: User) -> int:
    return int(
        db.scalar(
            select(func.count(Approval.id)).where(
                Approval.user_id == user.id, Approval.status == ApprovalStatus.PENDING
            )
        )
        or 0
    )
