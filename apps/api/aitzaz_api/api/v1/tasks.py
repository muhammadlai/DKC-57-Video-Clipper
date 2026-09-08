"""Task endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from aitzaz_api.core.deps import CurrentUser, DbSession, get_client_ip
from aitzaz_api.schemas.common import Paginated
from aitzaz_api.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from aitzaz_api.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    payload: TaskCreate,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> TaskResponse:
    task = task_service.create_task(
        db,
        user=user,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_at=payload.due_at,
        ip=ip,
    )
    return TaskResponse.model_validate(task)


@router.get("", response_model=Paginated[TaskResponse])
def list_tasks(
    db: DbSession,
    user: CurrentUser,
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Paginated[TaskResponse]:
    tasks, total = task_service.list_tasks(
        db, user=user, status=status, priority=priority, search=search, limit=limit, offset=offset
    )
    return Paginated(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats")
def stats(db: DbSession, user: CurrentUser) -> dict:
    return task_service.task_stats(db, user=user)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: DbSession, user: CurrentUser) -> TaskResponse:
    return TaskResponse.model_validate(task_service.get_task(db, user=user, task_id=task_id))


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> TaskResponse:
    task = task_service.update_task(
        db,
        user=user,
        task_id=task_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_at=payload.due_at,
        ip=ip,
    )
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> dict:
    task_service.delete_task(db, user=user, task_id=task_id, ip=ip)
    return {"message": "Task deleted"}
