"""Agent endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from aitzaz_api.core.deps import CurrentUser, DbSession
from aitzaz_api.schemas.agent import AgentResponse
from aitzaz_api.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
def list_agents(db: DbSession, user: CurrentUser) -> list[AgentResponse]:
    agents = agent_service.list_agents(db, user=user)
    return [AgentResponse.model_validate(a) for a in agents]


@router.get("/future")
def future_agents(user: CurrentUser) -> dict:
    """Specialist agents planned for later phases (display-only)."""
    return {"agents": agent_service.FUTURE_AGENTS}


@router.get("/{slug_or_id}", response_model=AgentResponse)
def get_agent(slug_or_id: str, db: DbSession, user: CurrentUser) -> AgentResponse:
    return AgentResponse.model_validate(agent_service.get_agent(db, slug_or_id=slug_or_id))
