"""Agent abstractions module.

Provides reusable agent definitions, conversation management,
and agent execution with automatic tool calling.
"""

from .base import (
    AgentDefinition,
    AgentExecutionResult,
    AgentState,
    PrepareStepCallback,
    StepAction,
    StepCallback,
    StepContext,
    ToolDefinition,
    ToolExecutionCallback,
)
from .conversation import ConversationManager, Message
from .executor import AgentExecutor, DefaultToolExecutor, ToolExecutorProtocol

__all__ = [
    # Base types
    "AgentDefinition",
    "AgentState",
    "AgentExecutionResult",
    "ToolDefinition",
    "StepContext",
    "StepAction",
    # Callbacks
    "StepCallback",
    "PrepareStepCallback",
    "ToolExecutionCallback",
    # Conversation
    "ConversationManager",
    "Message",
    # Executor
    "AgentExecutor",
    "ToolExecutorProtocol",
    "DefaultToolExecutor",
]
