"""Memory endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from aitzaz_api.core.deps import CurrentUser, DbSession, get_client_ip
from aitzaz_api.core.errors import NotFoundError
from aitzaz_api.schemas.common import Paginated
from aitzaz_api.schemas.memory import MemoryCreate, MemoryResponse, MemoryUpdate
from aitzaz_api.services import memory_service

router = APIRouter(prefix="/memories", tags=["memories"])


def _record_to_response(record) -> MemoryResponse:
    return MemoryResponse(
        id=record.id,
        category=record.category,
        content=record.content,
        importance=record.importance,
        metadata=record.metadata,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("", response_model=MemoryResponse, status_code=201)
def create_memory(
    payload: MemoryCreate,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> MemoryResponse:
    record = memory_service.create_memory(
        db,
        user=user,
        content=payload.content,
        category=payload.category,
        importance=payload.importance,
        metadata=payload.metadata,
        ip=ip,
    )
    return _record_to_response(record)


@router.get("", response_model=Paginated[MemoryResponse])
def list_memories(
    db: DbSession,
    user: CurrentUser,
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Paginated[MemoryResponse]:
    records, total = memory_service.list_memories(
        db, user=user, category=category, search=search, limit=limit, offset=offset
    )
    return Paginated(
        items=[_record_to_response(r) for r in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{memory_id}", response_model=MemoryResponse)
def get_memory(memory_id: str, db: DbSession, user: CurrentUser) -> MemoryResponse:
    store = memory_service.SQLAlchemyMemoryStore(db)
    record = store.get(user_id=str(user.id), memory_id=memory_id)
    if record is None:
        raise NotFoundError("Memory not found")
    return _record_to_response(record)


@router.patch("/{memory_id}", response_model=MemoryResponse)
def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> MemoryResponse:
    record = memory_service.update_memory(
        db,
        user=user,
        memory_id=memory_id,
        content=payload.content,
        category=payload.category,
        importance=payload.importance,
        ip=ip,
    )
    if record is None:
        raise NotFoundError("Memory not found")
    return _record_to_response(record)


@router.delete("/{memory_id}")
def delete_memory(
    memory_id: str,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> dict:
    deleted = memory_service.delete_memory(db, user=user, memory_id=memory_id, ip=ip)
    if not deleted:
        raise NotFoundError("Memory not found")
    return {"message": "Memory deleted"}
