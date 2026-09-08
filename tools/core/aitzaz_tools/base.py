"""Core tool abstraction for Aitzaz AI.

Every capability the agent can use is a *Tool*: a self-contained, validated,
permission-aware unit of work. Tools never touch the database directly;
request-scoped dependencies (user id, runtime config, service callables) are
passed in via :class:`ToolContext`. This keeps tools portable, testable and
safe to expose to LLMs in later phases.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from aitzaz_tools.validation import validate_against_schema


class ToolError(Exception):
    """Base error for tool execution failures."""

    code = "tool_error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ToolNotFoundError(ToolError):
    code = "tool_not_found"


class ToolDisabledError(ToolError):
    code = "tool_disabled"


class ToolInputError(ToolError):
    code = "tool_invalid_input"


class ToolPermissionError(ToolError):
    code = "tool_permission_denied"


@dataclass
class ToolContext:
    """Request-scoped information handed to a tool at execution time."""

    user_id: str | None = None
    actor: str = "user"  # "user" (invoked from UI/API) or "agent"
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Structured outcome of a tool execution."""

    ok: bool
    result: Any = None
    error: str | None = None
    error_code: str | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "result": self.result,
            "error": self.error,
            "error_code": self.error_code,
            "duration_ms": self.duration_ms,
        }


class Tool(ABC):
    """Base class for all Aitzaz AI tools.

    Subclasses define identity, JSON-schema contracts and an ``execute``
    method. Input is validated against ``input_schema`` before execution.
    """

    slug: str = ""
    name: str = ""
    description: str = ""
    category: str = "general"
    #: JSON Schema (subset) describing the tool input.
    input_schema: dict[str, Any] = {"type": "object", "properties": {}}
    #: JSON Schema (subset) describing the tool output.
    output_schema: dict[str, Any] = {"type": "object"}
    #: Permission code required to run this tool (None = any authenticated user).
    required_permission: str | None = None
    enabled: bool = True

    def validate_input(self, input_data: dict[str, Any] | None) -> dict[str, Any]:
        """Validate (and normalize) input against ``input_schema``."""
        cleaned, errors = validate_against_schema(
            self.input_schema, input_data if input_data is not None else {}
        )
        if errors:
            raise ToolInputError(
                "Invalid input for tool '%s'" % self.slug,
                details=errors,
            )
        return cleaned

    @abstractmethod
    def execute(self, input_data: dict[str, Any], ctx: ToolContext) -> Any:
        """Run the tool and return its JSON-serializable output.

        Raise :class:`ToolError` for controlled failures; unexpected
        exceptions are caught by the registry and converted to a failed
        :class:`ToolResult`.
        """

    def spec(self) -> dict[str, Any]:
        """Serializable descriptor (used by the API and the LLM tool spec)."""
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "required_permission": self.required_permission,
            "enabled": self.enabled,
        }


#: Optional callable that raises :class:`ToolPermissionError` when the caller
#: lacks the given permission code. Injected by the application layer.
PermissionChecker = Callable[[str], None]


class ToolRegistry:
    """In-process registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool, *, replace: bool = False) -> None:
        if not tool.slug:
            raise ValueError("Tool must define a non-empty slug")
        if tool.slug in self._tools and not replace:
            raise ValueError(f"Tool '{tool.slug}' is already registered")
        self._tools[tool.slug] = tool

    def get(self, slug: str) -> Tool:
        try:
            return self._tools[slug]
        except KeyError:
            raise ToolNotFoundError(f"Unknown tool: '{slug}'") from None

    def has(self, slug: str) -> bool:
        return slug in self._tools

    def list_tools(self) -> list[Tool]:
        return sorted(self._tools.values(), key=lambda t: t.slug)

    def execute(
        self,
        slug: str,
        input_data: dict[str, Any] | None,
        ctx: ToolContext,
        *,
        permission_checker: PermissionChecker | None = None,
    ) -> ToolResult:
        """Validate permissions + input, execute, and time the run."""
        tool = self.get(slug)  # raises ToolNotFoundError

        if not tool.enabled:
            raise ToolDisabledError(f"Tool '{slug}' is disabled")

        if tool.required_permission and permission_checker is not None:
            permission_checker(tool.required_permission)

        clean_input = tool.validate_input(input_data)

        started = time.perf_counter()
        try:
            output = tool.execute(clean_input, ctx)
        except ToolError as exc:
            return ToolResult(
                ok=False,
                error=exc.message,
                error_code=exc.code,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:  # noqa: BLE001 — tools must never crash the agent
            return ToolResult(
                ok=False,
                error=f"Tool '{slug}' failed unexpectedly: {exc}",
                error_code="tool_crash",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        return ToolResult(
            ok=True,
            result=output,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
