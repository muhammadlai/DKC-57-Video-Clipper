"""Approval schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from aitzaz_api.models.approval import APPROVAL_ACTION_TYPES
from aitzaz_api.schemas.common import ORMModel


class ApprovalCreate(BaseModel):
    action_type: str
    description: str = Field(min_length=1, max_length=1000)
    payload: dict[str, Any] = Field(default_factory=dict)
    task_id: uuid.UUID | None = None

    @field_validator("action_type")
    @classmethod
    def _known_action(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in APPROVAL_ACTION_TYPES:
            raise ValueError(f"action_type must be one of: {', '.join(APPROVAL_ACTION_TYPES)}")
        return value


class ApprovalDecision(BaseModel):
    decision: str  # "approved" | "rejected"
    note: str | None = Field(default=None, max_length=1000)


class ApprovalResponse(ORMModel):
    id: uuid.UUID
    task_id: uuid.UUID | None
    action_type: str
    description: str
    payload: dict[str, Any]
    status: str
    requested_at: datetime
    decided_at: datetime | None
    expires_at: datetime | None
    decision_note: str | None
    created_at: datetime
    updated_at: datetime
