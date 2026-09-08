"""User settings (per-user JSON document with defaults merged at read time)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aitzaz_api.db.base import Base, TimestampMixin


class UserSetting(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user = relationship("User", back_populates="settings_row")
