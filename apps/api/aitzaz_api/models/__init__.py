"""All models imported for Alembic autogenerate and metadata creation."""

from aitzaz_api.models.activity import ActivityLog, ActivityType
from aitzaz_api.models.agent import Agent, AgentConfig
from aitzaz_api.models.approval import (
    APPROVAL_ACTION_TYPES,
    APPROVAL_STATUSES,
    Approval,
    ApprovalStatus,
)
from aitzaz_api.models.conversation import Conversation, Message
from aitzaz_api.models.memory import Memory
from aitzaz_api.models.permission import (
    ALL_PERMISSIONS,
    Permission,
    permissions_for_role,
)
from aitzaz_api.models.session import AuthSession
from aitzaz_api.models.settings import UserSetting
from aitzaz_api.models.task import (
    TASK_PRIORITIES,
    TASK_STATUSES,
    TASK_TRANSITIONS,
    Task,
    TaskStatus,
)
from aitzaz_api.models.tool import Tool
from aitzaz_api.models.user import User

__all__ = [
    "ActivityLog",
    "ActivityType",
    "Agent",
    "AgentConfig",
    "APPROVAL_ACTION_TYPES",
    "APPROVAL_STATUSES",
    "Approval",
    "ApprovalStatus",
    "Conversation",
    "Message",
    "Memory",
    "ALL_PERMISSIONS",
    "Permission",
    "permissions_for_role",
    "AuthSession",
    "UserSetting",
    "TASK_PRIORITIES",
    "TASK_STATUSES",
    "TASK_TRANSITIONS",
    "Task",
    "TaskStatus",
    "Tool",
    "User",
]
