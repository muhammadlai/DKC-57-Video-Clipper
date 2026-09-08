"""Anthropic Messages API provider (optional; requires an API key).

Phase 1 ships a minimal, correct implementation of the LLMProvider contract
including tool use. Production hardening lands in Phase 2.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from aitzaz_agents.llm.base import (
    LLMCompletion,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMToolCall,
    LLMToolSpec,
)

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    is_demo = False

    def __init__(
        self, *, api_key: str, model: str = "claude-3-5-haiku-latest", timeout: float = 60.0
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[LLMToolSpec] | None = None,
    ) -> LLMCompletion:
        # Anthropic requires the system prompt separately.
        system_parts = [m.content for m in messages if m.role == "system"]
        chat = [m for m in messages if m.role in ("user", "assistant")]

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
            "system": "\n\n".join(system_parts) or None,
            "messages": [{"role": m.role, "content": m.content} for m in chat],
        }
        if tools:
            payload["tools"] = [
                {
                    "name": t.slug,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            response = httpx.post(
                _API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": _API_VERSION,
                },
                json=payload,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        if response.status_code != 200:
            raise LLMError(
                f"Anthropic returned HTTP {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        content_text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        tool_calls = [
            LLMToolCall(
                id=block.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                name=block["name"],
                arguments=block.get("input") or {},
            )
            for block in data.get("content", [])
            if block.get("type") == "tool_use"
        ]
        stop = data.get("stop_reason", "end_turn")
        return LLMCompletion(
            content=content_text or None,
            tool_calls=tool_calls,
            provider=self.name,
            model=data.get("model", self.model),
            finish_reason="tool_calls" if tool_calls else stop,
        )
