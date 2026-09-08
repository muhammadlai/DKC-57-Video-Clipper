"""Unit tests for security primitives, tools core and the mock LLM."""

from __future__ import annotations

import pytest

from aitzaz_api.core.security import (
    TokenError,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("super-secret-123", rounds=4)
    assert hashed != "super-secret-123"
    assert verify_password("super-secret-123", hashed)
    assert not verify_password("wrong", hashed)


def test_password_hash_is_salted():
    assert hash_password("same-password", rounds=4) != hash_password("same-password", rounds=4)


def test_token_roundtrip():
    token, jti, expires_at = create_access_token(subject="user-1", secret_key="k" * 32, expires_minutes=5)
    payload = decode_token(token, secret_key="k" * 32)
    assert payload["sub"] == "user-1"
    assert payload["jti"] == jti


def test_token_bad_secret():
    token, _jti, _exp = create_access_token(subject="user-1", secret_key="k" * 32)
    with pytest.raises(TokenError):
        decode_token(token, secret_key="other" + "x" * 28)


def test_token_expired():
    token, _jti, _exp = create_access_token(subject="u", secret_key="k" * 32, expires_minutes=-1)
    with pytest.raises(TokenError):
        decode_token(token, secret_key="k" * 32)


# --- tools core ---------------------------------------------------------------


def test_calculator_basic_math():
    from aitzaz_tools.base import ToolContext
    from aitzaz_tools.calculator import CalculatorTool

    tool = CalculatorTool()
    assert tool.execute({"expression": "125 * 48"}, ToolContext())["result"] == 6000
    assert tool.execute({"expression": "2 ** 10"}, ToolContext())["result"] == 1024
    assert tool.execute({"expression": "(5 + 5) / 4"}, ToolContext())["result"] == 2.5


def test_calculator_rejects_dangerous_input():
    from aitzaz_tools.base import ToolContext, ToolInputError
    from aitzaz_tools.calculator import CalculatorTool

    tool = CalculatorTool()
    with pytest.raises(ToolInputError):
        tool.execute({"expression": "__import__('os')"}, ToolContext())
    with pytest.raises(ToolInputError):
        tool.execute({"expression": "1 / 0"}, ToolContext())


def test_registry_permission_check():
    from aitzaz_tools.base import Tool, ToolContext, ToolPermissionError, ToolRegistry

    class GuardedTool(Tool):
        slug = "guarded"
        name = "Guarded"
        description = "test"
        required_permission = "admin.only"

        def execute(self, input_data, ctx):  # pragma: no cover
            return {}

    registry = ToolRegistry()
    registry.register(GuardedTool())

    def deny(_permission):
        raise ToolPermissionError("denied by test")

    with pytest.raises(ToolPermissionError):
        registry.execute("guarded", {}, ToolContext(), permission_checker=deny)


def test_registry_validation_error():
    from aitzaz_tools.base import ToolContext, ToolInputError, ToolRegistry
    from aitzaz_tools.echo import EchoTool

    registry = ToolRegistry()
    registry.register(EchoTool())
    with pytest.raises(ToolInputError):
        registry.execute("echo", {"nope": True}, ToolContext())


# --- mock LLM -----------------------------------------------------------------


def test_mock_llm_labels_demo():
    from aitzaz_agents.llm.mock import MockLLMProvider

    provider = MockLLMProvider()
    completion = provider.complete(
        [type("M", (), {"role": "user", "content": "hello", "name": None})()],
        tools=None,
    )
    assert completion.is_demo is True
    assert "Demo AI" in completion.content


def test_mock_llm_math_intent():
    from aitzaz_agents.llm.base import LLMToolSpec
    from aitzaz_agents.llm.mock import MockLLMProvider

    specs = [LLMToolSpec(slug="calculator", name="Calculator", description="math")]
    completion = MockLLMProvider().complete(
        [type("M", (), {"role": "user", "content": "What is 500 × 25?", "name": None})()],
        tools=specs,
    )
    assert completion.tool_calls[0].name == "calculator"


def test_openai_provider_requires_key():
    from aitzaz_agents.llm.factory import build_llm_provider

    class S:
        llm_provider = "openai"
        openai_api_key = None
        openai_model = "gpt-4o-mini"
        anthropic_api_key = None
        anthropic_model = "claude"
        mock_llm_delay_ms = 0

    provider, warning = build_llm_provider(S())
    assert provider.is_demo is True
    assert warning and "OPENAI_API_KEY" in warning
