"""Memory type system and storage contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class MemoryType(str, Enum):
    """Kinds of memory Aitzaz AI remembers about its user and itself."""

    PREFERENCE = "preference"  # how the user likes things done
    FACT = "fact"  # durable facts ("I live in Lahore")
    CONVERSATION = "conversation"  # noteworthy chat content
    TASK = "task"  # context tied to tasks
    SYSTEM = "system"  # operational/agent memory


MEMORY_CATEGORIES = [t.value for t in MemoryType]

#: 1 = minor detail ... 5 = critical, always surface
MIN_IMPORTANCE = 1
MAX_IMPORTANCE = 5
DEFAULT_IMPORTANCE = 3


def normalize_category(value: str | None) -> str:
    """Map free-form category strings onto the known memory types."""
    if not value:
        return MemoryType.FACT.value
    candidate = value.strip().lower().replace("-", "_")
    try:
        return MemoryType(candidate).value
    except ValueError:
        return MemoryType.FACT.value


def validate_importance(value: int | None) -> int:
    if value is None:
        return DEFAULT_IMPORTANCE
    return max(MIN_IMPORTANCE, min(MAX_IMPORTANCE, int(value)))


@dataclass
class MemoryRecord:
    """Provider-agnostic memory record (what agents see)."""

    id: str
    user_id: str
    category: str
    content: str
    importance: int = DEFAULT_IMPORTANCE
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@runtime_checkable
class MemoryStore(Protocol):
    """Storage contract for memories.

    The FastAPI app provides a SQLAlchemy-backed implementation today; a
    vector/RAG store can implement the same protocol in Phase 3.
    """

    def add(
        self,
        *,
        user_id: str,
        category: str,
        content: str,
        importance: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord: ...

    def get(self, *, user_id: str, memory_id: str) -> MemoryRecord | None: ...

    def list(
        self,
        *,
        user_id: str,
        category: str | None = None,
        search: str | None = None,
        min_importance: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MemoryRecord], int]: ...

    def update(
        self,
        *,
        user_id: str,
        memory_id: str,
        content: str | None = None,
        category: str | None = None,
        importance: int | None = None,
    ) -> MemoryRecord | None: ...

    def delete(self, *, user_id: str, memory_id: str) -> bool: ...


def summarize_for_prompt(records: list[MemoryRecord], max_chars: int = 1200) -> str:
    """Compact, prompt-ready summary of memories (used by agents)."""
    if not records:
        return ""
    lines = []
    for record in sorted(records, key=lambda r: r.importance, reverse=True):
        tag = record.category.upper()
        lines.append(f"- [{tag}] {record.content.strip()}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars].rsplit("\n", 1)[0] + "\n- …"
    return text
