"""Memory schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from aitzaz_api.schemas.common import ORMModel

MEMORY_CATEGORIES = ["preference", "fact", "conversation", "task", "system"]


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    category: str = Field(default="fact")
    importance: int = Field(default=3, ge=1, le=5)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    category: str | None = None
    importance: int | None = Field(default=None, ge=1, le=5)


class MemoryResponse(ORMModel):
    id: uuid.UUID
    category: str
    content: str
    importance: int
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_json")
    created_at: datetime
    updated_at: datetime
