"""Aggregated API v1 router."""

from __future__ import annotations

from fastapi import APIRouter

from aitzaz_api.api.v1 import (
    activity,
    agents,
    approvals,
    auth,
    chat,
    health,
    memories,
    misc,
    settings,
    tasks,
    tools,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(agents.router)
api_router.include_router(tools.router)
api_router.include_router(memories.router)
api_router.include_router(tasks.router)
api_router.include_router(approvals.router)
api_router.include_router(activity.router)
api_router.include_router(settings.router)
api_router.include_router(misc.router)
