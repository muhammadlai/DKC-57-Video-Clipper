"""Chat service — conversations, the agent runtime and message persistence."""

from __future__ import annotations

import logging
from datetime import UTC
from typing import Any
from uuid import UUID

from aitzaz_agents import (
    PERSONAL_ASSISTANT_DEFINITION,
    AgentDefinition,
    AgentResult,
    BaseAgent,
    PersonalAssistantAgent,
)
from aitzaz_agents.llm.base import LLMMessage
from aitzaz_agents.llm.factory import build_llm_provider
from aitzaz_tools.base import ToolContext
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aitzaz_api.core.config import Settings, get_settings
from aitzaz_api.core.errors import BadRequestError, NotFoundError
from aitzaz_api.models.activity import ActivityType
from aitzaz_api.models.agent import Agent as AgentRow
from aitzaz_api.models.conversation import Conversation, Message
from aitzaz_api.models.user import User
from aitzaz_api.services.activity_service import log_activity
from aitzaz_api.services.agent_service import get_personal_assistant
from aitzaz_api.services.approval_service import create_request_tool_payload
from aitzaz_api.services.memory_service import create_memory_tool_payload
from aitzaz_api.services.task_service import create_task_tool_payload
from aitzaz_api.services.tool_service import execute_tool

logger = logging.getLogger("aitzaz.chat")

MAX_CONTEXT_MESSAGES = 12


def _definition_from_row(row: AgentRow) -> AgentDefinition:
    return AgentDefinition(
        slug=row.slug,
        name=row.name,
        description=row.description,
        system_instructions=row.system_instructions or PERSONAL_ASSISTANT_DEFINITION.system_instructions,
        capabilities=row.capabilities or [],
        tool_slugs=row.tools or [],
        default_config={**(row.default_config or {}), "owner_name": "Aitzaz"},
        status=row.status,
    )


def build_runtime_agent(db: Session, *, user: User, settings: Settings | None = None) -> tuple[BaseAgent, str | None]:
    """Assemble the Personal Assistant for one request.

    Returns ``(agent, provider_warning)`` — the warning is set when a real
    provider was configured but fell back to the Demo AI (e.g. missing key).
    """
    settings = settings or get_settings()
    row = get_personal_assistant(db)
    definition = _definition_from_row(row) if row else PERSONAL_ASSISTANT_DEFINITION
    if row is None:  # database not seeded yet — keep working
        definition.default_config["owner_name"] = "Aitzaz"

    from aitzaz_api.services.tool_service import get_registry

    provider, warning = build_llm_provider(settings)
    agent = PersonalAssistantAgent(
        definition,
        tool_registry=get_registry(),  # provides tool specs to the LLM
        llm_provider=provider,
        max_tool_rounds=int(definition.default_config.get("max_tool_rounds", 3)),
    )
    return agent, warning


def _tool_executor(db: Session, user: User, ip: str | None):
    def executor(slug: str, arguments: dict[str, Any]) -> Any:
        result = execute_tool(
            db,
            user=user,
            slug=slug,
            input_data=arguments,
            actor="agent",
            ip=ip,
            config={
                "task_creator": lambda **kw: create_task_tool_payload(db, user=user, **kw),
                "memory_creator": lambda **kw: create_memory_tool_payload(db, user=user, ip=ip, **kw),
                "approval_requester": lambda **kw: create_request_tool_payload(db, user=user, **kw),
            },
            commit=False,
        )
        if not result.ok:
            from aitzaz_tools.base import ToolError

            raise ToolError(result.error or "tool failed")
        return result.result

    return executor


# -- conversations -------------------------------------------------------------


def list_conversations(db: Session, *, user: User, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc())
        .limit(limit)
    ).all()
    result = []
    for row in rows:
        count = db.scalar(select(func.count(Message.id)).where(Message.conversation_id == row.id)) or 0
        result.append(
            {
                "id": row.id,
                "title": row.title,
                "agent_id": row.agent_id,
                "created_at": row.created_at,
                "last_message_at": row.last_message_at,
                "message_count": int(count),
            }
        )
    return result


def get_conversation(db: Session, *, user: User, conversation_id: str) -> Conversation:
    try:
        cid = UUID(conversation_id)
    except ValueError:
        raise NotFoundError("Conversation not found") from None
    row = db.scalar(
        select(Conversation).where(Conversation.id == cid, Conversation.user_id == user.id)
    )
    if row is None:
        raise NotFoundError("Conversation not found")
    return row


def get_messages(db: Session, *, user: User, conversation_id: str, limit: int = 200) -> list[Message]:
    conversation = get_conversation(db, user=user, conversation_id=conversation_id)
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
            .limit(limit)
        ).all()
    )


def delete_conversation(db: Session, *, user: User, conversation_id: str, ip: str | None = None) -> None:
    conversation = get_conversation(db, user=user, conversation_id=conversation_id)
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.CONVERSATION_DELETED,
        message=f"Conversation cleared: {conversation.title}",
        meta={"conversation_id": str(conversation.id)},
        ip=ip,
    )
    db.delete(conversation)
    db.commit()


# -- the main chat flow ------------------------------------------------------------


def send_message(
    db: Session,
    *,
    user: User,
    message: str,
    conversation_id: str | None,
    ip: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    message = (message or "").strip()
    if not message:
        raise BadRequestError("Message cannot be empty")

    settings = settings or get_settings()

    # 1. Resolve or create the conversation.
    if conversation_id:
        conversation = get_conversation(db, user=user, conversation_id=conversation_id)
    else:
        agent_row = get_personal_assistant(db)
        conversation = Conversation(
            user_id=user.id,
            agent_id=agent_row.id if agent_row else None,
            title=message[:60] + ("…" if len(message) > 60 else ""),
        )
        db.add(conversation)
        db.flush()
        log_activity(
            db,
            user_id=user.id,
            activity_type=ActivityType.CONVERSATION_CREATED,
            message=f"Conversation started: {conversation.title}",
            meta={"conversation_id": str(conversation.id)},
            ip=ip,
        )

    # 2. Persist the user message.
    user_message = Message(conversation_id=conversation.id, role="user", content=message)
    db.add(user_message)
    db.flush()

    # 3. Build history for the agent.
    history_rows = (
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(MAX_CONTEXT_MESSAGES + 1)
        ).all()
    )
    history = [
        LLMMessage(role=row.role, content=row.content)
        for row in reversed(history_rows)
        if row.id != user_message.id and row.role in ("user", "assistant")
    ]

    # 4. Run the agent.
    agent, provider_warning = build_runtime_agent(db, user=user, settings=settings)
    ctx = ToolContext(
        user_id=str(user.id),
        actor="agent",
        config={
            "tool_executor": _tool_executor(db, user, ip),
            "default_timezone": settings.default_timezone,
            "task_creator": lambda **kw: create_task_tool_payload(db, user=user, **kw),
            "memory_creator": lambda **kw: create_memory_tool_payload(db, user=user, ip=ip, **kw),
            "approval_requester": lambda **kw: create_request_tool_payload(db, user=user, **kw),
        },
    )
    try:
        result: AgentResult = agent.run(message, history=history, context=ctx)
    except Exception as exc:  # noqa: BLE001 — never 500 the chat UI
        logger.exception("Agent run failed")
        from aitzaz_api.services.activity_service import log_error

        log_error(db, user=user, where="chat.agent_run", error=str(exc), ip=ip)
        raise BadRequestError(
            "The agent could not process this message. Please try again."
        ) from exc

    # 5. Persist the assistant message.
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result.content,
        meta={
            "provider": result.provider,
            "model": result.model,
            "demo_mode": result.is_demo,
            "rounds": result.rounds,
            "tool_calls": [call.to_dict() for call in result.tool_calls],
            "provider_warning": provider_warning,
        },
    )
    db.add(assistant_message)
    from datetime import datetime

    conversation.last_message_at = datetime.now(UTC)
    db.flush()

    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.AI_MESSAGE,
        message=f"Chat: {message[:80]} → {result.content[:80]}",
        meta={
            "conversation_id": str(conversation.id),
            "tools_used": [call.slug for call in result.tool_calls],
            "provider": result.provider,
            "demo": result.is_demo,
        },
        ip=ip,
    )
    db.commit()
    db.refresh(assistant_message)
    db.refresh(user_message)

    return {
        "conversation_id": conversation.id,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "tool_calls": [call.to_dict() for call in result.tool_calls],
        "provider": result.provider,
        "model": result.model,
        "demo_mode": result.is_demo,
    }
