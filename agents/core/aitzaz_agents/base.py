"""Agent abstraction.

An agent = identity + instructions + capabilities + tools + an LLM provider.
The FastAPI application persists agent definitions; this module defines the
runtime contract so future specialist agents (research, browser, coding…)
plug in without changing the chat pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aitzaz_agents.llm.base import (
    LLMMessage,
    LLMProvider,
    LLMToolSpec,
)
from aitzaz_tools.base import ToolContext, ToolRegistry, ToolError


class AgentStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass
class AgentDefinition:
    """Static definition of an agent (mirrored in the database)."""

    slug: str
    name: str
    description: str
    system_instructions: str
    capabilities: list[str] = field(default_factory=list)
    tool_slugs: list[str] = field(default_factory=list)
    default_config: dict[str, Any] = field(default_factory=dict)
    status: AgentStatus = AgentStatus.ACTIVE


@dataclass
class ExecutedToolCall:
    """A tool the agent invoked during a turn (recorded for UI + audit)."""

    slug: str
    arguments: dict[str, Any]
    ok: bool
    result: Any = None
    error: str | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "arguments": self.arguments,
            "ok": self.ok,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AgentResult:
    """Outcome of one agent turn."""

    content: str
    tool_calls: list[ExecutedToolCall] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    is_demo: bool = False
    rounds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "tool_calls": [c.to_dict() for c in self.tool_calls],
            "provider": self.provider,
            "model": self.model,
            "is_demo": self.is_demo,
        }


class BaseAgent(ABC):
    """Runtime base class for agents.

    Subclasses implement :meth:`run`, orchestrating the LLM provider and the
    tool registry. The base class provides shared helpers (tool spec
    extraction, guarded tool execution).
    """

    def __init__(
        self,
        definition: AgentDefinition,
        *,
        tool_registry: ToolRegistry | None,
        llm_provider: LLMProvider,
        max_tool_rounds: int = 3,
    ) -> None:
        self.definition = definition
        self.tool_registry = tool_registry
        self.llm_provider = llm_provider
        self.max_tool_rounds = max(1, max_tool_rounds)

    # -- helpers -----------------------------------------------------------

    def tool_specs(self) -> list[LLMToolSpec]:
        if self.tool_registry is None:
            return []
        specs: list[LLMToolSpec] = []
        for slug in self.definition.tool_slugs:
            if self.tool_registry.has(slug):
                tool = self.tool_registry.get(slug)
                specs.append(
                    LLMToolSpec(
                        slug=tool.slug,
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.input_schema,
                    )
                )
        return specs

    def safe_execute(
        self, slug: str, arguments: dict[str, Any], ctx: ToolContext
    ) -> ExecutedToolCall:
        """Execute a tool, converting errors into a failed ExecutedToolCall."""
        try:
            result = self.tool_registry.execute(slug, arguments, ctx)
        except ToolError as exc:
            return ExecutedToolCall(
                slug=slug, arguments=arguments, ok=False, error=exc.message
            )
        return ExecutedToolCall(
            slug=slug,
            arguments=arguments,
            ok=result.ok,
            result=result.result,
            error=result.error,
            duration_ms=result.duration_ms,
        )

    # -- contract ----------------------------------------------------------

    @abstractmethod
    def run(
        self,
        user_input: str,
        *,
        history: list[LLMMessage] | None = None,
        context: ToolContext,
    ) -> AgentResult:
        """Process one user message and produce an :class:`AgentResult`."""
