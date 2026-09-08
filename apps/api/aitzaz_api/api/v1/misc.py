"""Dashboard stats + global search (small conveniences for the UI)."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from aitzaz_api.core.config import get_settings
from aitzaz_api.core.deps import CurrentUser, DbSession
from aitzaz_api.models.activity import ActivityLog
from aitzaz_api.models.conversation import Conversation
from aitzaz_api.models.memory import Memory
from aitzaz_api.models.task import Task
from aitzaz_api.schemas.activity import ActivityResponse
from aitzaz_api.schemas.misc import DashboardStats, SearchResults, TaskStats
from aitzaz_api.services import (
    agent_service,
    approval_service,
    memory_service,
    task_service,
    tool_service,
)

router = APIRouter(tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: DbSession, user: CurrentUser) -> DashboardStats:
    settings = get_settings()
    agent_row = agent_service.get_personal_assistant(db)
    recent = activity_service_list(db, user_id=user.id, limit=8)
    return DashboardStats(
        tasks=TaskStats(**task_service.task_stats(db, user=user)),
        pending_approvals=approval_service.count_pending(db, user=user),
        memories_count=memory_service.count_memories(db, user=user),
        tools_connected=len([t for t in tool_service.list_tools(db) if t.enabled]),
        conversations_count=conversation_count(db, user_id=user.id),
        agent_status=(agent_row.status if agent_row else "unknown"),
        demo_mode=settings.llm_provider == "mock",
        recent_activity=[ActivityResponse.model_validate(e) for e in recent],
    )


def activity_service_list(db, *, user_id, limit: int) -> list[ActivityLog]:
    return activity_service_recent(db, user_id=user_id, limit=limit)


def activity_service_recent(db, *, user_id, limit: int) -> list[ActivityLog]:
    return list(
        db.scalars(
            select(ActivityLog)
            .where(ActivityLog.user_id == user_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
        ).all()
    )


def conversation_count(db, *, user_id) -> int:
    return int(
        db.scalar(select(func.count(Conversation.id)).where(Conversation.user_id == user_id)) or 0
    )


@router.get("/search", response_model=SearchResults)
def search(
    db: DbSession,
    user: CurrentUser,
    q: str = Query(min_length=1, max_length=120),
) -> SearchResults:
    pattern = f"%{q.strip()}%"

    task_rows = db.scalars(
        select(Task)
        .where(Task.user_id == user.id, or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
        .limit(5)
    ).all()
    memory_rows = db.scalars(
        select(Memory).where(Memory.user_id == user.id, Memory.content.ilike(pattern)).limit(5)
    ).all()
    conversation_rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.title.ilike(pattern))
        .limit(5)
    ).all()

    return SearchResults(
        query=q,
        tasks=[{"id": str(t.id), "title": t.title, "status": t.status} for t in task_rows],
        memories=[
            {"id": str(m.id), "content": m.content[:120], "category": m.category}
            for m in memory_rows
        ],
        conversations=[{"id": str(c.id), "title": c.title} for c in conversation_rows],
    )
