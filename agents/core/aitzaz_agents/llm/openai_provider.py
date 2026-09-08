"""OpenAI chat-completions provider (optional; requires an API key).

Phase 1 ships a minimal, correct implementation of the LLMProvider contract
including function calling. Production hardening (retries, token accounting,
streaming) lands in Phase 2.
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

_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(LLMProvider):
    name = "openai"
    is_demo = False

    def __init__(self, *, api_key: str, model: str = "gpt-4o-mini", timeout: float = 60.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[LLMToolSpec] | None = None,
    ) -> LLMCompletion:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.slug,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        try:
            response = httpx.post(
                _API_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc

        if response.status_code != 200:
            raise LLMError(
                f"OpenAI returned HTTP {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]

        tool_calls = [
            LLMToolCall(
                id=tc.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                name=tc["function"]["name"],
                arguments=self._parse_arguments(tc["function"].get("arguments", "{}")),
            )
            for tc in message.get("tool_calls") or []
        ]
        return LLMCompletion(
            content=message.get("content"),
            tool_calls=tool_calls,
            provider=self.name,
            model=data.get("model", self.model),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    @staticmethod
    def _parse_arguments(raw: str | dict) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
