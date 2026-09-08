"""Personal Assistant — the built-in Phase 1 agent.

Implements the agent loop:

    user message → LLM provider → (tool calls ⇄ results) → final answer

The loop is provider-agnostic: the Demo AI (mock) and real providers both
express tool calls through the same LLMProvider contract.
"""

from __future__ import annotations

import json

from aitzaz_agents.base import (
    AgentDefinition,
    AgentResult,
    BaseAgent,
    ExecutedToolCall,
)
from aitzaz_agents.llm.base import LLMCompletion, LLMError, LLMMessage, LLMToolCall
from aitzaz_tools.base import ToolContext, ToolError

MAX_HISTORY_MESSAGES = 12

PERSONAL_ASSISTANT_DEFINITION = AgentDefinition(
    slug="personal-assistant",
    name="Personal Assistant",
    description=(
        "Aitzaz's central AI agent. Understands requests, uses safe tools, "
        "creates tasks and memories, and prepares approval requests for "
        "sensitive actions."
    ),
    system_instructions=(
        "You are Aitzaz AI, {owner}'s personal AI agent.\n"
        "Behaviour:\n"
        "1. Understand the user's request and help politely and concisely.\n"
        "2. Use the available tools whenever they can answer better than plain text.\n"
        "3. For sensitive external actions (emails, purchases, deletions), never "
        "claim to have done them — request an approval first.\n"
        "4. You are honest about what you are: if running as the Demo AI, say so.\n"
        "5. Keep answers short and friendly."
    ),
    capabilities=["chat", "calculator", "time", "tasks", "memory", "approvals"],
    tool_slugs=[
        "calculator",
        "current_time",
        "echo",
        "task_create",
        "memory_create",
        "approval_request",
    ],
    default_config={"max_tool_rounds": 3},
    status="active",
)


class PersonalAssistantAgent(BaseAgent):
    """The general-purpose personal agent."""

    def run(
        self,
        user_input: str,
        *,
        history: list[LLMMessage] | None = None,
        context: ToolContext,
    ) -> AgentResult:
        tools = self.tool_specs()
        messages: list[LLMMessage] = [self._system_message()]
        trimmed = (history or [])[-MAX_HISTORY_MESSAGES:]
        messages.extend(trimmed)
        messages.append(LLMMessage(role="user", content=user_input))

        executed: list = []
        rounds = 0
        completion: LLMCompletion | None = None
        seen_calls: set[tuple[str, str]] = set()

        for _ in range(self.max_tool_rounds + 1):
            rounds += 1
            completion = self.llm_provider.complete(messages, tools=tools or None)

            if not completion.tool_calls:
                break

            new_calls = [
                c for c in completion.tool_calls
                if (c.name, json.dumps(c.arguments or {}, sort_keys=True, default=str)) not in seen_calls
            ]
            if not new_calls:
                # Deterministic provider repeating itself — stop the loop.
                completion = type(completion)(
                    content=completion.content or self._repeat_fallback(),
                    tool_calls=[],
                    provider=completion.provider,
                    model=completion.model,
                    finish_reason="stop",
                    is_demo=completion.is_demo,
                )
                break

            for tool_call in new_calls:
                seen_calls.add(
                    (tool_call.name, json.dumps(tool_call.arguments or {}, sort_keys=True, default=str))
                )
                result = self.safe_execute(
                    tool_call.name, tool_call.arguments or {}, context
                )
                executed.append(result)
                messages.append(
                    LLMMessage(
                        role="assistant",
                        content="",
                        name=tool_call.name,
                    )
                )
                messages.append(
                    LLMMessage(
                        role="tool",
                        name=tool_call.name,
                        content=self._serialize_tool_result(tool_call, result),
                    )
                )
            # Loop once more so the provider can summarize the tool results.

        content = (completion.content if completion else "") or self._repeat_fallback()
        return AgentResult(
            content=content,
            tool_calls=executed,
            provider=completion.provider if completion else "",
            model=completion.model if completion else "",
            is_demo=completion.is_demo if completion else self.llm_provider.is_demo,
            rounds=rounds,
        )

    # -- internals ----------------------------------------------------------

    def safe_execute(self, slug: str, arguments: dict, ctx: ToolContext) -> ExecutedToolCall:
        """Prefer the injected (DB-backed) executor; fall back to the registry.

        The executor path runs the same permission checks and audit logging as
        the Tools API, so agent-driven tool use is fully audited.
        """
        executor = ctx.config.get("tool_executor") if ctx.config else None
        if executor is not None:
            try:
                output = executor(slug, arguments)
            except ToolError as exc:
                return ExecutedToolCall(slug=slug, arguments=arguments, ok=False, error=exc.message)
            except Exception as exc:  # noqa: BLE001
                return ExecutedToolCall(slug=slug, arguments=arguments, ok=False, error=str(exc))
            return ExecutedToolCall(slug=slug, arguments=arguments, ok=True, result=output)
        return super().safe_execute(slug, arguments, ctx)

    @staticmethod
    def _repeat_fallback() -> str:
        return (
            "I couldn't produce an answer for that. Please try rephrasing, "
            "or try one of the suggested prompts."
        )

    def _system_message(self) -> LLMMessage:
        owner = self.definition.default_config.get("owner_name", "my user")
        instructions = self.definition.system_instructions.format(owner=owner)
        demo_note = (
            "\nCurrent mode: Demo AI (rule-based mock provider). Mention this "
            "when the user might expect real AI reasoning."
            if self.llm_provider.is_demo
            else ""
        )
        tool_line = (
            f"Available tools: {', '.join(self.definition.tool_slugs)}."
            if self.definition.tool_slugs
            else ""
        )
        return LLMMessage(role="system", content=f"{instructions}{demo_note}\n{tool_line}")

    @staticmethod
    def _serialize_tool_result(call: LLMToolCall, result) -> str:
        import json

        payload = {
            "tool": call.name,
            "ok": result.ok,
            "result": result.result if result.ok else None,
            "error": result.error,
        }
        return json.dumps(payload, default=str)
