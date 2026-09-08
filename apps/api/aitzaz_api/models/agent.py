"""Agent models — persisted agent definitions and per-agent configuration."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aitzaz_api.db.base import Base, TimestampMixin


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    system_instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    capabilities: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    #: Slugs of tools this agent may use (kept simple for Phase 1).
    tools: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    default_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: Owner for user-created agents; NULL for built-ins.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    configs = relationship(
        "AgentConfig",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AgentConfig(Base, TimestampMixin):
    __tablename__ = "agent_configs"
    __table_args__ = (UniqueConstraint("agent_id", "key", name="uq_agent_configs_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    agent = relationship("Agent", back_populates="configs")
