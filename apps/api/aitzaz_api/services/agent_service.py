"""Agent service — persists built-in agents and exposes them to the API."""

from __future__ import annotations

import uuid

from aitzaz_agents import PERSONAL_ASSISTANT_DEFINITION, AgentDefinition
from sqlalchemy import select
from sqlalchemy.orm import Session

from aitzaz_api.core.errors import NotFoundError
from aitzaz_api.models.agent import Agent, AgentConfig
from aitzaz_api.models.user import User


def _definition_to_row(definition: AgentDefinition) -> dict:
    return {
        "slug": definition.slug,
        "name": definition.name,
        "description": definition.description,
        "system_instructions": definition.system_instructions,
        "capabilities": list(definition.capabilities),
        "tools": list(definition.tool_slugs),
        "default_config": dict(definition.default_config),
        "status": definition.status.value if hasattr(definition.status, "value") else str(definition.status),
        "is_builtin": True,
    }


def ensure_builtin_agents(db: Session) -> None:
    """Idempotently sync built-in agent definitions into the database."""
    for definition in [PERSONAL_ASSISTANT_DEFINITION]:
        row = db.scalar(select(Agent).where(Agent.slug == definition.slug))
        if row is None:
            db.add(Agent(**_definition_to_row(definition)))
        else:
            for key, value in _definition_to_row(definition).items():
                setattr(row, key, value)
    db.commit()


def list_agents(db: Session, *, user: User | None = None) -> list[Agent]:
    query = select(Agent).where(
        Agent.is_builtin.is_(True) | (Agent.user_id == (user.id if user else None))
    )
    return list(db.scalars(query.order_by(Agent.created_at)).all())


def get_agent(db: Session, *, slug_or_id: str) -> Agent:
    row = db.scalar(select(Agent).where(Agent.slug == slug_or_id))
    if row is None:
        try:
            row = db.get(Agent, uuid.UUID(slug_or_id))
        except ValueError:
            row = None
    if row is None:
        raise NotFoundError("Agent not found")
    return row


def get_personal_assistant(db: Session) -> Agent | None:
    return db.scalar(select(Agent).where(Agent.slug == PERSONAL_ASSISTANT_DEFINITION.slug))


def set_agent_status(db: Session, *, agent_id: str, status: str) -> Agent:
    if status not in ("active", "paused", "disabled"):
        raise NotFoundError("status must be active, paused or disabled")
    agent = get_agent(db, slug_or_id=agent_id)
    agent.status = status
    db.commit()
    db.refresh(agent)
    return agent


def add_agent_config(db: Session, *, agent_id: str, key: str, value: dict) -> AgentConfig:
    agent = get_agent(db, slug_or_id=agent_id)
    row = db.scalar(
        select(AgentConfig).where(AgentConfig.agent_id == agent.id, AgentConfig.key == key)
    )
    if row is None:
        row = AgentConfig(agent_id=agent.id, key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()
    db.refresh(row)
    return row


#: Future specialist agents (display-only; implemented in later phases).
FUTURE_AGENTS: list[dict[str, str]] = [
    {"slug": "research-agent", "name": "Research Agent", "phase": "Phase 4", "description": "Web research, topic reports, source collection."},
    {"slug": "browser-agent", "name": "Browser Agent", "phase": "Phase 5", "description": "Operates websites through browser automation."},
    {"slug": "coding-agent", "name": "Coding Agent", "phase": "Phase 10", "description": "Helps with programming tasks in safe workspaces."},
    {"slug": "file-agent", "name": "File Agent", "phase": "Phase 6", "description": "Reads, organizes and summarizes documents."},
    {"slug": "email-agent", "name": "Email Agent", "phase": "Phase 8", "description": "Drafts and sends email when explicitly connected."},
    {"slug": "calendar-agent", "name": "Calendar Agent", "phase": "Phase 8", "description": "Manages events and reminders."},
    {"slug": "finance-agent", "name": "Finance Agent", "phase": "Phase 10", "description": "Tracks and analyzes finances (read-only first)."},
    {"slug": "communication-agent", "name": "Communication Agent", "phase": "Phase 10", "description": "Coordination across messaging platforms."},
]
