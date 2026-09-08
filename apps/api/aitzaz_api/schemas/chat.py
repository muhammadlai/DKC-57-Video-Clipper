"""Chat schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from aitzaz_api.schemas.common import ORMModel, ToolCallInfo


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=6000)
    conversation_id: uuid.UUID | None = None


class MessageResponse(ORMModel):
    id: uuid.UUID
    role: str
    content: str
    meta: dict[str, Any] | None = None
    created_at: datetime


class ConversationResponse(ORMModel):
    id: uuid.UUID
    title: str
    agent_id: uuid.UUID | None = None
    created_at: datetime
    last_message_at: datetime | None = None
    message_count: int = 0


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    user_message: MessageResponse
    assistant_message: MessageResponse
    tool_calls: list[ToolCallInfo] = []
    provider: str
    model: str
    demo_mode: bool
