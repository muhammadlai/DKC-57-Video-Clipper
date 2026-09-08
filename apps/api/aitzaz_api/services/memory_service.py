"""Memory service — SQLAlchemy-backed implementation of the MemoryStore
protocol (aitzaz_memory) plus API-facing conveniences."""

from __future__ import annotations

import uuid
from typing import Any

from aitzaz_memory import MemoryRecord, MemoryStore, normalize_category, validate_importance
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aitzaz_api.models.activity import ActivityType
from aitzaz_api.models.memory import Memory
from aitzaz_api.models.user import User
from aitzaz_api.services.activity_service import log_activity


class SQLAlchemyMemoryStore(MemoryStore):
    """Concrete MemoryStore. Swappable for a vector store in Phase 3."""

    def __init__(self, db: Session, *, ip: str | None = None) -> None:
        self.db = db
        self.ip = ip

    # -- protocol implementation -------------------------------------------

    def add(
        self,
        *,
        user_id: str,
        category: str,
        content: str,
        importance: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        memory = Memory(
            user_id=uuid.UUID(user_id),
            category=normalize_category(category),
            content=content.strip(),
            importance=validate_importance(importance),
            metadata_json=metadata or {},
        )
        self.db.add(memory)
        self.db.flush()
        return self._to_record(memory)

    def get(self, *, user_id: str, memory_id: str) -> MemoryRecord | None:
        memory = self._get_orm(user_id, memory_id)
        return self._to_record(memory) if memory else None

    def list(
        self,
        *,
        user_id: str,
        category: str | None = None,
        search: str | None = None,
        min_importance: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MemoryRecord], int]:
        query = select(Memory).where(Memory.user_id == uuid.UUID(user_id))
        count_query = select(func.count(Memory.id)).where(Memory.user_id == uuid.UUID(user_id))
        if category:
            query = query.where(Memory.category == normalize_category(category))
            count_query = count_query.where(Memory.category == normalize_category(category))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(Memory.content.ilike(pattern))
            count_query = count_query.where(Memory.content.ilike(pattern))
        if min_importance is not None:
            query = query.where(Memory.importance >= min_importance)
            count_query = count_query.where(Memory.importance >= min_importance)
        total = db_count(self.db, count_query)
        rows = self.db.scalars(
            query.order_by(Memory.importance.desc(), Memory.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return [self._to_record(m) for m in rows], total

    def update(
        self,
        *,
        user_id: str,
        memory_id: str,
        content: str | None = None,
        category: str | None = None,
        importance: int | None = None,
    ) -> MemoryRecord | None:
        memory = self._get_orm(user_id, memory_id)
        if memory is None:
            return None
        if content is not None:
            memory.content = content.strip()
        if category is not None:
            memory.category = normalize_category(category)
        if importance is not None:
            memory.importance = validate_importance(importance)
        self.db.flush()
        return self._to_record(memory)

    def delete(self, *, user_id: str, memory_id: str) -> bool:
        memory = self._get_orm(user_id, memory_id)
        if memory is None:
            return False
        self.db.delete(memory)
        self.db.flush()
        return True

    # -- helpers -------------------------------------------------------------

    def _get_orm(self, user_id: str, memory_id: str) -> Memory | None:
        try:
            mid = uuid.UUID(memory_id)
        except ValueError:
            return None
        return self.db.scalar(
            select(Memory).where(Memory.id == mid, Memory.user_id == uuid.UUID(user_id))
        )

    @staticmethod
    def _to_record(memory: Memory) -> MemoryRecord:
        return MemoryRecord(
            id=str(memory.id),
            user_id=str(memory.user_id),
            category=memory.category,
            content=memory.content,
            importance=memory.importance,
            metadata=memory.metadata_json or {},
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )


def db_count(db: Session, count_query) -> int:
    return int(db.scalar(count_query) or 0)


def list_memories(
    db: Session,
    *,
    user: User,
    category: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[MemoryRecord], int]:
    store = SQLAlchemyMemoryStore(db)
    return store.list(user_id=str(user.id), category=category, search=search, limit=limit, offset=offset)


def create_memory(
    db: Session,
    *,
    user: User,
    content: str,
    category: str = "fact",
    importance: int = 3,
    metadata: dict[str, Any] | None = None,
    source: str = "user",
    ip: str | None = None,
) -> MemoryRecord:
    store = SQLAlchemyMemoryStore(db, ip=ip)
    record = store.add(
        user_id=str(user.id),
        category=category,
        content=content,
        importance=importance,
        metadata={**(metadata or {}), "source": source},
    )
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.MEMORY_CREATED,
        message=f"Memory saved ({record.category}): {record.content[:80]}",
        meta={"memory_id": record.id, "source": source},
        ip=ip,
    )
    db.commit()
    return record


def update_memory(
    db: Session,
    *,
    user: User,
    memory_id: str,
    content: str | None = None,
    category: str | None = None,
    importance: int | None = None,
    ip: str | None = None,
) -> MemoryRecord | None:
    store = SQLAlchemyMemoryStore(db, ip=ip)
    record = store.update(
        user_id=str(user.id), memory_id=memory_id, content=content, category=category, importance=importance
    )
    if record is None:
        return None
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.MEMORY_UPDATED,
        message=f"Memory updated: {record.content[:80]}",
        meta={"memory_id": record.id},
        ip=ip,
    )
    db.commit()
    return record


def delete_memory(db: Session, *, user: User, memory_id: str, ip: str | None = None) -> bool:
    store = SQLAlchemyMemoryStore(db, ip=ip)
    record = store.get(user_id=str(user.id), memory_id=memory_id)
    if record is None:
        return False
    store.delete(user_id=str(user.id), memory_id=memory_id)
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.MEMORY_DELETED,
        message=f"Memory deleted: {record.content[:80]}",
        meta={"memory_id": memory_id},
        ip=ip,
    )
    db.commit()
    return True


def count_memories(db: Session, *, user: User) -> int:
    return int(
        db.scalar(select(func.count(Memory.id)).where(Memory.user_id == user.id)) or 0
    )


def create_memory_tool_payload(
    db: Session,
    *,
    user: User,
    content: str,
    category: str = "fact",
    importance: int = 3,
    ip: str | None = None,
) -> dict[str, Any]:
    """Shaped for the agent's memory_create tool (chat flow owns commit)."""
    record = create_memory(
        db,
        user=user,
        content=content,
        category=category,
        importance=importance,
        source="agent",
        ip=ip,
    )
    return {
        "id": record.id,
        "content": record.content,
        "category": record.category,
        "importance": record.importance,
    }
