"""Agent schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from aitzaz_api.schemas.common import ORMModel


class AgentResponse(ORMModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    system_instructions: str
    capabilities: list[str]
    tools: list[str]
    default_config: dict[str, Any]
    status: str
    is_builtin: bool
    created_at: datetime
    updated_at: datetime
