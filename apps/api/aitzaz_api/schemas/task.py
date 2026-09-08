"""Task schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from aitzaz_api.models.task import TASK_PRIORITIES, TASK_STATUSES
from aitzaz_api.schemas.common import ORMModel


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    priority: str = Field(default="medium")
    due_at: datetime | None = None

    @field_validator("priority")
    @classmethod
    def _valid_priority(cls, value: str) -> str:
        value = value.lower()
        if value not in TASK_PRIORITIES:
            raise ValueError(f"priority must be one of: {', '.join(TASK_PRIORITIES)}")
        return value


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: str | None = None
    priority: str | None = None
    due_at: datetime | None = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, value: str | None) -> str | None:
        if value is not None and value not in TASK_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(TASK_STATUSES)}")
        return value

    @field_validator("priority")
    @classmethod
    def _valid_priority(cls, value: str | None) -> str | None:
        if value is not None and value.lower() not in TASK_PRIORITIES:
            raise ValueError(f"priority must be one of: {', '.join(TASK_PRIORITIES)}")
        return value.lower() if value else value


class TaskResponse(ORMModel):
    id: uuid.UUID
    title: str
    description: str
    status: str
    priority: str
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
