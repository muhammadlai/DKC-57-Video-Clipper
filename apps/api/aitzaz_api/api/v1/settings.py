"""Settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from aitzaz_api.core.deps import CurrentUser, DbSession, get_client_ip
from aitzaz_api.schemas.misc import SettingsResponse, SettingsSectionUpdate
from aitzaz_api.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def get_settings_values(db: DbSession, user: CurrentUser) -> SettingsResponse:
    return SettingsResponse(data=settings_service.get_user_settings(db, user=user))


@router.patch("", response_model=SettingsResponse)
def update_settings(
    payload: SettingsSectionUpdate,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> SettingsResponse:
    data = settings_service.update_section(
        db, user=user, section=payload.section, values=payload.values, ip=ip
    )
    return SettingsResponse(data=data)
