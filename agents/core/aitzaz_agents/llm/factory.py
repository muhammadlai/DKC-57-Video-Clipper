"""LLM provider factory — selects the provider from configuration.

Resolution order:
1. ``provider="mock"`` → Demo AI (default; no API key required).
2. ``provider="openai"`` / ``"anthropic"`` → real provider; if its API key is
   missing the factory falls back to the Demo AI so the app never breaks.
"""

from __future__ import annotations

from typing import Any, Protocol

from aitzaz_agents.llm.base import LLMProvider
from aitzaz_agents.llm.mock import MockLLMProvider


class _SettingsLike(Protocol):
    llm_provider: str
    openai_api_key: str | None
    openai_model: str
    anthropic_api_key: str | None
    anthropic_model: str
    mock_llm_delay_ms: int


def build_llm_provider(settings: _SettingsLike) -> tuple[LLMProvider, str | None]:
    """Return ``(provider, warning)``.

    ``warning`` is a human-readable note when a real provider was requested
    but not usable (missing key), in which case the Demo AI is returned.
    """
    choice = (settings.llm_provider or "mock").strip().lower()

    if choice == "openai":
        if settings.openai_api_key:
            from aitzaz_agents.llm.openai_provider import OpenAIProvider

            return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model), None
        return (
            _demo(settings),
            "LLM_PROVIDER=openai but OPENAI_API_KEY is not set — using Demo AI instead.",
        )

    if choice == "anthropic":
        if settings.anthropic_api_key:
            from aitzaz_agents.llm.anthropic_provider import AnthropicProvider

            return (
                AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model),
                None,
            )
        return (
            _demo(settings),
            "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set — using Demo AI instead.",
        )

    if choice not in ("mock", "demo", ""):
        return (
            _demo(settings),
            f"Unknown LLM_PROVIDER '{choice}' — using Demo AI instead.",
        )

    return _demo(settings), None


def _demo(settings: _SettingsLike) -> MockLLMProvider:
    delay = getattr(settings, "mock_llm_delay_ms", 0) or 0
    return MockLLMProvider(delay_ms=delay)


def provider_summary(provider: LLMProvider) -> dict[str, Any]:
    return {
        "provider": provider.name,
        "model": provider.model,
        "demo_mode": provider.is_demo,
    }
