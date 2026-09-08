"""Activity/audit logging — every meaningful event is recorded here."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aitzaz_api.models.activity import ActivityLog, ActivityType
from aitzaz_api.models.user import User


def log_activity(
    db: Session,
    *,
    user_id: Any,
    activity_type: str | ActivityType,
    message: str,
    meta: dict[str, Any] | None = None,
    ip: str | None = None,
) -> ActivityLog:
    entry = ActivityLog(
        user_id=user_id,
        activity_type=activity_type.value if isinstance(activity_type, ActivityType) else activity_type,
        message=message,
        meta=meta,
        ip=ip,
    )
    db.add(entry)
    db.flush()
    return entry


def list_activity(
    db: Session,
    *,
    user_id: Any,
    activity_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ActivityLog], int]:
    query = select(ActivityLog).where(ActivityLog.user_id == user_id)
    count_query = select(func.count(ActivityLog.id)).where(ActivityLog.user_id == user_id)
    if activity_type:
        query = query.where(ActivityLog.activity_type == activity_type)
        count_query = count_query.where(ActivityLog.activity_type == activity_type)
    total = db.scalar(count_query) or 0
    entries = db.scalars(
        query.order_by(ActivityLog.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return list(entries), int(total)


def recent_activity(db: Session, *, user_id: Any, limit: int = 8) -> list[ActivityLog]:
    return list(
        db.scalars(
            select(ActivityLog)
            .where(ActivityLog.user_id == user_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
        ).all()
    )


def log_error(db: Session, *, user: User | None, where: str, error: str, ip: str | None = None) -> None:
    """Best-effort error audit — never raises."""
    try:
        log_activity(
            db,
            user_id=user.id if user else None,
            activity_type=ActivityType.ERROR,
            message=f"Error in {where}: {error[:500]}",
            ip=ip,
        )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
