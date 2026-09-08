"""Activity schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from aitzaz_api.schemas.common import ORMModel


class ActivityResponse(ORMModel):
    id: uuid.UUID
    activity_type: str
    message: str
    meta: dict[str, Any] | None
    ip: str | None
    created_at: datetime
