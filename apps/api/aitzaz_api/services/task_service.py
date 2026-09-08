"""Task service — CRUD, transitions and dashboard stats."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from aitzaz_api.core.errors import ConflictError, NotFoundError
from aitzaz_api.models.activity import ActivityType
from aitzaz_api.models.task import TASK_TRANSITIONS, Task, TaskStatus
from aitzaz_api.models.user import User
from aitzaz_api.services.activity_service import log_activity


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def create_task(
    db: Session,
    *,
    user: User,
    title: str,
    description: str = "",
    priority: str = "medium",
    due_at: datetime | None = None,
    status: str = TaskStatus.PENDING,
    source: str = "user",
    ip: str | None = None,
) -> Task:
    task = Task(
        user_id=user.id,
        title=title.strip()[:200],
        description=description or "",
        priority=priority,
        due_at=_aware(due_at),
        status=status,
    )
    db.add(task)
    db.flush()
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.TASK_CREATED,
        message=f"Task created: {task.title}",
        meta={"task_id": str(task.id), "source": source, "priority": task.priority},
        ip=ip,
    )
    db.commit()
    db.refresh(task)
    return task


def create_task_tool_payload(
    db: Session,
    *,
    user: User,
    title: str,
    description: str = "",
    priority: str = "medium",
    due_at: datetime | None = None,
) -> dict[str, Any]:
    """Shaped for the agent's task_create tool (called inside the chat flow,
    which owns the final commit)."""
    task = create_task(
        db,
        user=user,
        title=title,
        description=description,
        priority=priority,
        due_at=due_at,
        source="agent",
    )
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "due_at": task.due_at.isoformat() if task.due_at else None,
    }


def list_tasks(
    db: Session,
    *,
    user: User,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Task], int]:
    query = select(Task).where(Task.user_id == user.id)
    count_query = select(func.count(Task.id)).where(Task.user_id == user.id)
    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
        count_query = count_query.where(Task.priority == priority)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
        count_query = count_query.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
    total = int(db.scalar(count_query) or 0)
    rows = db.scalars(
        query.order_by(Task.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return list(rows), total


def get_task(db: Session, *, user: User, task_id: str) -> Task:
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        raise NotFoundError("Task not found") from None
    task = db.scalar(select(Task).where(Task.id == tid, Task.user_id == user.id))
    if task is None:
        raise NotFoundError("Task not found")
    return task


def update_task(
    db: Session,
    *,
    user: User,
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_at: datetime | None = None,
    ip: str | None = None,
) -> Task:
    task = get_task(db, user=user, task_id=task_id)
    if title is not None:
        task.title = title.strip()[:200]
    if description is not None:
        task.description = description
    if priority is not None:
        task.priority = priority
    if due_at is not None:
        task.due_at = _aware(due_at)
    if status is not None and status != task.status:
        allowed = TASK_TRANSITIONS.get(task.status, set())
        if status not in allowed:
            raise ConflictError(
                f"Cannot change task status from '{task.status}' to '{status}'. "
                f"Allowed: {', '.join(sorted(allowed)) if allowed else 'none (final state)'}"
            )
        task.status = status
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.TASK_UPDATED,
        message=f"Task updated: {task.title} (status: {task.status})",
        meta={"task_id": str(task.id)},
        ip=ip,
    )
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, *, user: User, task_id: str, ip: str | None = None) -> None:
    task = get_task(db, user=user, task_id=task_id)
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.TASK_DELETED,
        message=f"Task deleted: {task.title}",
        meta={"task_id": str(task.id)},
        ip=ip,
    )
    db.delete(task)
    db.commit()


def task_stats(db: Session, *, user: User) -> dict[str, int]:
    rows = db.execute(
        select(Task.status, func.count(Task.id)).where(Task.user_id == user.id).group_by(Task.status)
    ).all()
    counts = {status: int(count) for status, count in rows}
    total = sum(counts.values())
    return {
        "total": total,
        "pending": counts.get(TaskStatus.PENDING, 0),
        "running": counts.get(TaskStatus.RUNNING, 0),
        "waiting_approval": counts.get(TaskStatus.WAITING_APPROVAL, 0),
        "completed": counts.get(TaskStatus.COMPLETED, 0),
        "failed": counts.get(TaskStatus.FAILED, 0),
        "cancelled": counts.get(TaskStatus.CANCELLED, 0),
    }


def active_tasks(db: Session, *, user: User, limit: int = 5) -> list[Task]:
    return list(
        db.scalars(
            select(Task)
            .where(Task.user_id == user.id, Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL]))
            .order_by(Task.created_at.desc())
            .limit(limit)
        ).all()
    )
