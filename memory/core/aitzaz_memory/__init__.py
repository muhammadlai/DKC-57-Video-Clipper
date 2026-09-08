"""Aitzaz AI — memory abstraction.

Phase 1 keeps memory simple: typed, categorized records persisted in
PostgreSQL and retrieved by filters. The :class:`MemoryStore` protocol is the
seam where semantic/vector retrieval (Phase 3) will plug in without changing
callers.
"""

from aitzaz_memory.base import (
    MEMORY_CATEGORIES,
    MemoryRecord,
    MemoryStore,
    MemoryType,
    normalize_category,
    summarize_for_prompt,
    validate_importance,
)

__all__ = [
    "MemoryType",
    "MEMORY_CATEGORIES",
    "MemoryRecord",
    "MemoryStore",
    "normalize_category",
    "validate_importance",
    "summarize_for_prompt",
]
