"""Activity log — the audit trail of everything that happens."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aitzaz_api.db.base import Base


class ActivityType(StrEnum):
    REGISTERED = "user_registered"
    LOGIN = "login"
    LOGOUT = "logout"
    AI_MESSAGE = "ai_message"
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TOOL_EXECUTED = "tool_executed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    MEMORY_CREATED = "memory_created"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_DELETED = "memory_deleted"
    SETTINGS_UPDATED = "settings_updated"
    PROFILE_UPDATED = "profile_updated"
    CONVERSATION_CREATED = "conversation_created"
    CONVERSATION_DELETED = "conversation_deleted"
    ERROR = "error"

    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    activity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    user = relationship("User", back_populates="activity_logs")
