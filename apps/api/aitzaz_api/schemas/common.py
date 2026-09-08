"""Shared schema helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = {"from_attributes": True}


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ToolCallInfo(BaseModel):
    slug: str
    arguments: dict | None = None
    ok: bool
    result: object | None = None
    error: str | None = None
    duration_ms: int = 0


def utc_now() -> datetime:
    from datetime import datetime as dt

    return dt.now(UTC)
