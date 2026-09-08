"""Activity (audit log) endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from aitzaz_api.core.deps import CurrentUser, DbSession
from aitzaz_api.schemas.activity import ActivityResponse
from aitzaz_api.schemas.common import Paginated
from aitzaz_api.services import activity_service

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=Paginated[ActivityResponse])
def list_activity(
    db: DbSession,
    user: CurrentUser,
    type: str | None = Query(default=None, alias="type"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Paginated[ActivityResponse]:
    entries, total = activity_service.list_activity(
        db, user_id=user.id, activity_type=type, limit=limit, offset=offset
    )
    return Paginated(
        items=[ActivityResponse.model_validate(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )
