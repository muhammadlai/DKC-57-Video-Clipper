"""Demo AI provider — deterministic, rule-based "LLM" for Phase 1.

This provider is NOT a real AI model. It pattern-matches common requests and
either answers directly or emits tool calls exactly like a real provider
would, so the full agent pipeline (tools → memory → approvals) is exercised
without an API key. Every response is labelled as demo via ``is_demo=True``
and the UI shows a "Demo AI" badge whenever this provider is active.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Callable, Optional

from aitzaz_agents.llm.base import (
    LLMCompletion,
    LLMMessage,
    LLMProvider,
    LLMToolCall,
    LLMToolSpec,
)

_MATH_RE = re.compile(
    r"(\d+(?:\.\d+)?(?:\s*[-+*/×÷x%^]\s*\(?\s*\d+(?:\.\d+)?\s*\)?)+)"
)
_REMEMBER_RE = re.compile(
    r"\bremember(?:\s+(?:that|this))?\s*[:,-]?\s*(.+)",
    re.IGNORECASE,
)
_TASK_RE = re.compile(
    r"(?:remind me to|remind me|create(?:\s+a)?\s+task(?:\s+to)?|add\s+task|new\s+task)\s*[:,]?\s*(.+)",
    re.IGNORECASE,
)
_ECHO_RE = re.compile(r"^\s*echo\s*[:\-]?\s*(.+)$", re.IGNORECASE)
_TIME_RE = re.compile(r"\b(what(?:'s| is)? the )?(time|date|day)\b.*", re.IGNORECASE)
_HELP_RE = re.compile(
    r"\b(help|what can you do|who are you|capabilities|features)\b", re.IGNORECASE
)
# Sensitive external actions → approval workflow (Phase 1: request only).
_APPROVAL_RE = re.compile(
    r"\b(send|draft|compose)\b.*\b(e-?mail|message)\b"
    r"|\b(e-?mail|message)\b.*\b(to|send)\b"
    r"|\b(purchase|buy|pay|transfer|delete all|post publicly)\b",
    re.IGNORECASE,
)
_GREETING_RE = re.compile(
    r"\b(hi|hello|hey|good (morning|afternoon|evening)|salaam|salam|assalam)\b",
    re.IGNORECASE,
)
_THANKS_RE = re.compile(r"\b(thanks|thank you|shukriya)\b", re.IGNORECASE)

Intents = Callable[[str, list[LLMMessage]], Optional[dict]]


class MockLLMProvider(LLMProvider):
    """Deterministic Demo AI. Never pretends to be a real model."""

    name = "mock-demo"
    model = "demo-rules-v1"
    is_demo = True

    def __init__(self, *, delay_ms: int = 0) -> None:
        self.delay_ms = max(0, int(delay_ms))

    # -- contract ----------------------------------------------------------

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[LLMToolSpec] | None = None,
    ) -> LLMCompletion:
        if self.delay_ms:
            time.sleep(self.delay_ms / 1000)

        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        available = {spec.slug for spec in (tools or [])}

        def call(slug: str, arguments: dict) -> LLMCompletion:
            return LLMCompletion(
                content=None,
                tool_calls=[
                    LLMToolCall(id=f"call_{uuid.uuid4().hex[:12]}", name=slug, arguments=arguments)
                ],
                provider=self.name,
                model=self.model,
                finish_reason="tool_calls",
                is_demo=True,
            )

        text = last_user.strip()

        # A real provider sees tool results and then produces the final
        # answer. The mock mirrors that: when the last message(s) are tool
        # results, summarize them instead of calling tools again.
        trailing_tool_msgs = self._trailing_tool_messages(messages)
        if trailing_tool_msgs:
            return LLMCompletion(
                content=self._summarize_tool_results(trailing_tool_msgs),
                tool_calls=[],
                provider=self.name,
                model=self.model,
                finish_reason="stop",
                is_demo=True,
            )

        # 1. Math → calculator tool
        if "calculator" in available:
            math_match = _MATH_RE.search(text.replace(",", ""))
            if math_match and not _TASK_RE.search(text):
                return call("calculator", {"expression": math_match.group(1)})

        # 2. Date/time → current_time tool
        if "current_time" in available and _TIME_RE.search(text) and len(text) < 120:
            arguments = {}
            tz = self._extract_timezone(text)
            if tz:
                arguments["timezone"] = tz
            return call("current_time", arguments)

        # 3. Remember X → memory_create tool
        if "memory_create" in available:
            m = _REMEMBER_RE.search(text)
            if m and not _TASK_RE.search(text):
                content = m.group(1).strip().rstrip(".")
                category = "preference" if re.search(r"\bi (prefer|like|always|usually)\b", content, re.I) else "fact"
                return call("memory_create", {"content": content, "category": category})

        # 4. Task / reminder → task_create tool
        if "task_create" in available:
            m = _TASK_RE.search(text)
            if m:
                title = m.group(1).strip().rstrip(".!?")
                arguments: dict = {"title": title[:200]}
                due = self._extract_due(text)
                if due:
                    arguments["due_at"] = due
                return call("task_create", arguments)

        # 5. Sensitive external actions → approval_request tool
        if "approval_request" in available and _APPROVAL_RE.search(text):
            action_type = self._classify_action(text)
            return call(
                "approval_request",
                {
                    "action_type": action_type,
                    "description": f"Demo AI wants to: {text[:300]}",
                },
            )

        # 6. Echo test tool
        if "echo" in available:
            m = _ECHO_RE.match(text)
            if m:
                return call("echo", {"message": m.group(1).strip()})

        # 7. Direct answers (no tools needed)
        return LLMCompletion(
            content=self._direct_reply(text),
            tool_calls=[],
            provider=self.name,
            model=self.model,
            finish_reason="stop",
            is_demo=True,
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _trailing_tool_messages(messages: list["LLMMessage"]) -> list["LLMMessage"]:
        trailing: list[LLMMessage] = []
        for message in reversed(messages):
            if message.role == "tool":
                trailing.append(message)
            elif message.role == "assistant" and not message.content:
                continue
            else:
                break
        return list(reversed(trailing))

    def _summarize_tool_results(self, tool_messages: list["LLMMessage"]) -> str:
        lines: list[str] = []
        for message in tool_messages:
            slug = message.name or "tool"
            try:
                payload = json.loads(message.content or "{}")
            except json.JSONDecodeError:
                payload = {}
            ok = payload.get("ok", False)
            result = payload.get("result") or {}
            if not ok:
                lines.append(
                    f"⚠️ The {slug} tool failed: {payload.get('error') or 'unknown error'}."
                )
                continue
            if slug == "calculator":
                lines.append(
                    f"{result.get('expression')} = **{result.get('formatted', result.get('result'))}**"
                )
            elif slug == "current_time":
                lines.append(f"🕒 {result.get('friendly')} — ISO: `{result.get('iso')}`")
            elif slug == "task_create":
                due = f"\nDue: {result.get('due_at')}" if result.get("due_at") else ""
                lines.append(
                    f"✅ Task created: **{result.get('title')}**{due}\nSee it on the Tasks page."
                )
            elif slug == "memory_create":
                lines.append(
                    f"🧠 Noted — I'll remember that ({result.get('category')}): "
                    "\u201c{0}\u201d. It's on the Memory page.".format(result.get("content"))
                )
            elif slug == "approval_request":
                lines.append(
                    "🔒 That's a sensitive action, so I did **not** execute it. "
                    f"I created approval request #{result.get('id', '')} "
                    f"({result.get('action_type')}). Open the Approvals page and "
                    "approve or reject it — I only act after your approval."
                )
            elif slug == "echo":
                lines.append(
                    f"🔁 Echo test OK: \u201c{result.get('message')}\u201d "
                    "(received back from the tool pipeline)."
                )
            else:
                lines.append(f"Used `{slug}` → {json.dumps(result, default=str)[:400]}")
        return "\n".join(lines) or "Done."

    def _direct_reply(self, text: str) -> str:
        lowered = text.lower()
        if _GREETING_RE.search(lowered) and len(text) < 80:
            return (
                "Hello! I'm Aitzaz AI — your personal agent. I'm currently "
                "running as the **Demo AI** (a rule-based mock, not a real "
                "LLM yet — a real provider arrives in Phase 2).\n\n"
                "Try me with:\n"
                "• `Calculate 125 × 48`\n"
                "• `What time is it?`\n"
                "• `Remind me to stretch tomorrow`\n"
                "• `Remember that I prefer dark mode`\n"
                "• `Send an email to John` (creates an approval request)"
            )
        if _HELP_RE.search(lowered):
            return (
                "I'm Aitzaz AI, running in **Demo AI** mode. In Phase 1 I can:\n\n"
                "1. Do math via the Calculator tool — try `What is 500 × 25?`\n"
                "2. Tell you the current time via the Current Time tool\n"
                "3. Create tasks — try `Remind me to call the bank tomorrow`\n"
                "4. Remember things — try `Remember that my sister's birthday is March 3`\n"
                "5. Prepare sensitive actions as approval requests — try "
                "`Send an email to John`\n\n"
                "Real LLM understanding, web research, browser automation and "
                "more arrive in later phases."
            )
        if _THANKS_RE.search(lowered):
            return "You're welcome! Anything else you'd like me to do?"
        return (
            "I'm the **Demo AI** for Phase 1, so my understanding is limited "
            "to a few patterns (math, time, tasks, memory, approvals). "
            "A real LLM provider will be connected in Phase 2.\n\n"
            "Try: `Calculate 300 × 12`, `What time is it?`, `Remind me to "
            "review the report tomorrow`, or `Remember that I prefer short "
            "emails`."
        )

    @staticmethod
    def _extract_timezone(text: str) -> str | None:
        m = re.search(r"\b([A-Za-z]+/[A-Za-z_]+)\b", text)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_due(text: str) -> str | None:
        """Very small natural-language due-date extraction for the demo."""
        now = time.time()
        if re.search(r"\btomorrow\b", text, re.I):
            return time.strftime("%Y-%m-%dT09:00:00Z", time.gmtime(now + 86400))
        if re.search(r"\btonight\b", text, re.I):
            return time.strftime("%Y-%m-%dT20:00:00Z", time.gmtime(now))
        m = re.search(r"\bin (\d+) (minutes?|hours?)\b", text, re.I)
        if m:
            amount = int(m.group(1))
            seconds = amount * (3600 if m.group(2).lower().startswith("hour") else 60)
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + seconds))
        return None

    @staticmethod
    def _classify_action(text: str) -> str:
        lowered = text.lower()
        if re.search(r"\be-?mail\b", lowered):
            return "send_email"
        if re.search(r"\b(message|dm|whatsapp|sms)\b", lowered):
            return "send_message"
        if re.search(r"\b(purchase|buy|pay)\b", lowered):
            return "purchase"
        if re.search(r"\btransfer\b", lowered):
            return "transfer_money"
        if re.search(r"\bdelete\b", lowered):
            return "delete_files"
        if re.search(r"\bpost\b", lowered):
            return "post_publicly"
        return "external_action"

    def describe_intents(self) -> list[dict]:
        """Introspection for the Tools/Agents pages and tests."""
        return [
            {"pattern": "math expression", "tool": "calculator"},
            {"pattern": "time/date question", "tool": "current_time"},
            {"pattern": "remember …", "tool": "memory_create"},
            {"pattern": "remind me to … / create task …", "tool": "task_create"},
            {"pattern": "send email/message, purchase …", "tool": "approval_request"},
            {"pattern": "echo …", "tool": "echo"},
        ]

    def to_json(self) -> str:
        return json.dumps(self.describe_intents())
