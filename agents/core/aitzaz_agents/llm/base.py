"""LLM provider abstraction (provider-agnostic chat completion contract)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMError(Exception):
    """Base error for LLM provider failures."""


class ProviderNotConfiguredError(LLMError):
    """Raised when a provider is selected but its API key is missing."""


@dataclass
class LLMMessage:
    """One message in a conversation (OpenAI-style roles)."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None  # tool slug for role == "tool"


@dataclass
class LLMToolSpec:
    """Tool description handed to the provider (function-calling style)."""

    slug: str
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMToolCall:
    """A tool invocation requested by the provider."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMCompletion:
    """Response from a provider: either content, tool calls, or both."""

    content: str | None
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    finish_reason: str = "stop"
    #: True when the active provider is the built-in Demo AI (mock).
    is_demo: bool = False


class LLMProvider(ABC):
    """Contract every LLM provider implements.

    Implementations shipped in Phase 1:

    * :class:`MockLLMProvider` — deterministic Demo AI (no API key, clearly
      labelled as a demo everywhere it appears).
    * ``OpenAIProvider`` / ``AnthropicProvider`` — real providers, enabled via
      environment configuration (hardened in Phase 2).
    """

    name: str = "base"
    model: str = "unknown"
    is_demo: bool = False

    @abstractmethod
    def complete(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[LLMToolSpec] | None = None,
    ) -> LLMCompletion:
        """Produce the next assistant turn for the given messages."""

    def healthcheck(self) -> dict[str, Any]:
        return {"provider": self.name, "model": self.model, "demo": self.is_demo}


__all__ = [
    "LLMProvider",
    "LLMMessage",
    "LLMToolSpec",
    "LLMToolCall",
    "LLMCompletion",
    "LLMError",
    "ProviderNotConfiguredError",
]
