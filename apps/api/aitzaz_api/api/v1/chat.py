"""Chat endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from aitzaz_api.core.deps import CurrentUser, DbSession, get_client_ip
from aitzaz_api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    MessageResponse,
)
from aitzaz_api.services import chat_service

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def send_message(
    payload: ChatRequest,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> ChatResponse:
    data = chat_service.send_message(
        db,
        user=user,
        message=payload.message,
        conversation_id=str(payload.conversation_id) if payload.conversation_id else None,
        ip=ip,
    )
    return ChatResponse(
        conversation_id=data["conversation_id"],
        user_message=MessageResponse.model_validate(data["user_message"]),
        assistant_message=MessageResponse.model_validate(data["assistant_message"]),
        tool_calls=data["tool_calls"],
        provider=data["provider"],
        model=data["model"],
        demo_mode=data["demo_mode"],
    )


@router.get("/chat/conversations", response_model=list[ConversationResponse])
def list_conversations(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[ConversationResponse]:
    return [ConversationResponse.model_validate(c) for c in chat_service.list_conversations(db, user=user, limit=limit)]


@router.get("/chat/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conversation_id: str,
    db: DbSession,
    user: CurrentUser,
) -> list[MessageResponse]:
    messages = chat_service.get_messages(db, user=user, conversation_id=conversation_id)
    return [MessageResponse.model_validate(m) for m in messages]


@router.delete("/chat/conversations/{conversation_id}", response_model=dict)
def clear_conversation(
    conversation_id: str,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> dict:
    chat_service.delete_conversation(db, user=user, conversation_id=conversation_id, ip=ip)
    return {"message": "Conversation cleared"}
