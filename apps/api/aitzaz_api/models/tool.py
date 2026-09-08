"""Tool registry persistence — mirrors the code-level ToolRegistry."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from aitzaz_api.db.base import Base, TimestampMixin


class Tool(Base, TimestampMixin):
    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    required_permission: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: execution method — "local" in Phase 1 (future: "http", "browser", …)
    execution: Mapped[str] = mapped_column(String(40), default="local", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
