"""Approval model — the ASK FOR APPROVAL → EXECUTE control plane.

The agent can *prepare* sensitive external actions (emails, purchases,
deletions…), but they only execute after an explicit human decision recorded
here. Phase 1 wires the architecture; real connectors arrive in Phase 8.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aitzaz_api.db.base import Base, TimestampMixin


class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


APPROVAL_STATUSES = [
    ApprovalStatus.PENDING,
    ApprovalStatus.APPROVED,
    ApprovalStatus.REJECTED,
    ApprovalStatus.EXPIRED,
]

#: Action types Phase 1 can *request* (none are actually connected).
APPROVAL_ACTION_TYPES = [
    "send_email",
    "send_message",
    "purchase",
    "transfer_money",
    "delete_files",
    "change_settings",
    "submit_form",
    "make_call",
    "post_publicly",
    "external_action",
]


class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    #: structured payload the connector will use once approved
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=ApprovalStatus.PENDING, nullable=False, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="approvals")
    task = relationship("Task", back_populates="approvals")
