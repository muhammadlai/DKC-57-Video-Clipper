"""Agent-only tools backed by application services.

These conform to the same Tool interface as the demo tools but their
``execute`` calls callables injected via ``ToolContext.config`` — that keeps
this package free of database imports while still letting the agent create
tasks/memories/approvals through the exact same validated tool pipeline.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from aitzaz_tools.base import Tool, ToolContext, ToolInputError

VALID_CATEGORIES = ["preference", "fact", "conversation", "task", "system"]
VALID_ACTION_TYPES = [
    "send_email",
    "send_message",
    "purchase",
    "transfer_money",
    "delete_files",
    "change_settings",
    "submit_form",
    "make_call",
    "post_publicly",
    "external_action",
]
VALID_PRIORITIES = ["low", "medium", "high", "urgent"]


class TaskCreateTool(Tool):
    slug = "task_create"
    name = "Create Task"
    description = (
        "Creates a task on the user's task list. Use when the user asks to "
        "remember to do something, set a reminder, or track work."
    )
    category = "tasks"
    required_permission = "tasks.create"
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 200},
            "description": {"type": "string", "maxLength": 4000, "default": ""},
            "priority": {"type": "string", "enum": VALID_PRIORITIES, "default": "medium"},
            "due_at": {
                "type": "string",
                "maxLength": 40,
                "description": "Optional ISO-8601 due date/time",
            },
        },
        "required": ["title"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "status": {"type": "string"},
        },
    }

    def execute(self, input_data: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        creator: Callable[..., dict[str, Any]] | None = ctx.config.get("task_creator")
        if creator is None:
            raise ToolInputError("Task creation is not available in this context")
        due_at = input_data.get("due_at")
        parsed_due = None
        if due_at:
            try:
                raw = due_at.replace("Z", "+00:00")
                parsed_due = datetime.fromisoformat(raw)
                if parsed_due.tzinfo is None:
                    parsed_due = parsed_due.replace(tzinfo=UTC)
            except ValueError as exc:
                raise ToolInputError(
                    f"Could not parse due_at '{due_at}'. Use ISO-8601 like 2026-01-31T09:00:00Z."
                ) from exc
        return creator(
            title=input_data["title"],
            description=input_data.get("description") or "",
            priority=input_data.get("priority") or "medium",
            due_at=parsed_due,
        )


class MemoryCreateTool(Tool):
    slug = "memory_create"
    name = "Create Memory"
    description = (
        "Stores a durable fact or preference about the user. Use when the "
        "user says 'remember that …' or shares something worth remembering."
    )
    category = "memory"
    required_permission = "memory.write"
    input_schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "minLength": 1, "maxLength": 1000},
            "category": {"type": "string", "enum": VALID_CATEGORIES, "default": "fact"},
            "importance": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
        },
        "required": ["content"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "content": {"type": "string"},
            "category": {"type": "string"},
        },
    }

    def execute(self, input_data: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        creator: Callable[..., dict[str, Any]] | None = ctx.config.get("memory_creator")
        if creator is None:
            raise ToolInputError("Memory creation is not available in this context")
        return creator(
            content=input_data["content"],
            category=input_data.get("category") or "fact",
            importance=input_data.get("importance") or 3,
        )


class ApprovalRequestTool(Tool):
    slug = "approval_request"
    name = "Request Approval"
    description = (
        "Prepares a sensitive external action (send email/message, purchase, "
        "delete files, …) as an approval request. NEVER performs the action — "
        "the user must approve it first."
    )
    category = "approvals"
    required_permission = "approvals.request"
    input_schema = {
        "type": "object",
        "properties": {
            "action_type": {"type": "string", "enum": VALID_ACTION_TYPES},
            "description": {
                "type": "string",
                "minLength": 1,
                "maxLength": 1000,
                "description": "Exactly what will be done once approved",
            },
            "payload": {
                "type": "object",
                "description": "Structured details for the action (recipient, content, …)",
            },
        },
        "required": ["action_type", "description"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "action_type": {"type": "string"},
            "status": {"type": "string"},
        },
    }

    def execute(self, input_data: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        requester: Callable[..., dict[str, Any]] | None = ctx.config.get("approval_requester")
        if requester is None:
            raise ToolInputError("Approval requests are not available in this context")
        return requester(
            action_type=input_data["action_type"],
            description=input_data["description"],
            payload=input_data.get("payload") or {},
        )


def build_agent_tools() -> list[Tool]:
    return [TaskCreateTool(), MemoryCreateTool(), ApprovalRequestTool()]
