"""Aitzaz AI — agent core.

Defines the reusable Agent abstraction, the LLM provider interface with a
clearly-labelled Demo (mock) provider, and the built-in Personal Assistant
agent.
"""

from aitzaz_agents.base import (
    AgentDefinition,
    AgentResult,
    AgentStatus,
    BaseAgent,
    ExecutedToolCall,
)
from aitzaz_agents.llm import build_llm_provider
from aitzaz_agents.llm.base import (
    LLMCompletion,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMToolCall,
    LLMToolSpec,
    ProviderNotConfiguredError,
)
from aitzaz_agents.personal_assistant import PERSONAL_ASSISTANT_DEFINITION, PersonalAssistantAgent

__all__ = [
    "AgentDefinition",
    "AgentResult",
    "AgentStatus",
    "BaseAgent",
    "ExecutedToolCall",
    "LLMCompletion",
    "LLMError",
    "LLMMessage",
    "LLMProvider",
    "LLMToolCall",
    "LLMToolSpec",
    "ProviderNotConfiguredError",
    "PERSONAL_ASSISTANT_DEFINITION",
    "PersonalAssistantAgent",
    "build_llm_provider",
]
