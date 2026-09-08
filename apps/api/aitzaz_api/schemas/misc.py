"""Activity, agent, tool, settings and misc schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from aitzaz_api.schemas.activity import ActivityResponse
from aitzaz_api.schemas.common import ORMModel

# --- Tools ----------------------------------------------------------------------

class ToolExecuteRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    tool: str
    ok: bool
    result: object | None = None
    error: str | None = None
    error_code: str | None = None
    duration_ms: int


class ToolResponse(ORMModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    category: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_permission: str | None
    execution: str
    enabled: bool
    is_builtin: bool
    created_at: datetime
    updated_at: datetime


# --- Settings ---------------------------------------------------------------------

class SettingsSectionUpdate(BaseModel):
    section: str
    values: dict[str, Any]

    @field_validator("section")
    @classmethod
    def _known_section(cls, value: str) -> str:
        allowed = {
            "general",
            "ai_provider",
            "appearance",
            "security",
            "notifications",
            "memory",
            "tools",
            "permissions",
        }
        if value not in allowed:
            raise ValueError(f"section must be one of: {', '.join(sorted(allowed))}")
        return value


class SettingsResponse(BaseModel):
    data: dict[str, Any]


# --- Stats / search (dashboard) ------------------------------------------------------

class TaskStats(BaseModel):
    total: int = 0
    pending: int = 0
    running: int = 0
    waiting_approval: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


class DashboardStats(BaseModel):
    tasks: TaskStats
    pending_approvals: int
    memories_count: int
    tools_connected: int
    conversations_count: int
    agent_status: str
    demo_mode: bool
    recent_activity: list[ActivityResponse]


class SearchResults(BaseModel):
    query: str
    tasks: list[dict[str, Any]]
    memories: list[dict[str, Any]]
    conversations: list[dict[str, Any]]
