"""Memory model — what Aitzaz AI remembers about its user."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aitzaz_api.db.base import Base, TimestampMixin


class Memory(Base, TimestampMixin):
    __tablename__ = "memories"
    __table_args__ = (
        CheckConstraint("importance BETWEEN 1 AND 5", name="importance_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: one of aitzaz_memory.MemoryType values (preference|fact|conversation|task|system)
    category: Mapped[str] = mapped_column(String(40), default="fact", nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    user = relationship("User", back_populates="memories")
