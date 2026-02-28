"""Agent base types and definitions.

Defines the core types for agent configuration, including
AgentDefinition, StepContext, and ToolDefinition.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from flowforge_server.services.ai import ToolCall


@dataclass
class ToolDefinition:
    """Definition of a tool that can be called by an agent."""

    name: str
    description: str
    parameters: dict[str, Any]
    is_builtin: bool = False
    requires_approval: bool = False
    approval_timeout: str = "30m"
    code: str | None = None

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Convert to Anthropic tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


@dataclass
class StepContext:
    """Context passed to step callbacks."""

    iteration: int
    messages: list[dict[str, Any]]
    pending_tool_calls: list[ToolCall]
    state: dict[str, Any]
    tokens_used: int
    cost_usd: float = 0.0
    elapsed_seconds: float = 0.0


@dataclass
class StepAction:
    """Action to take for the current step."""

    action: Literal["continue", "approve", "reject", "modify", "stop"]
    modified_tool_calls: list[ToolCall] | None = None
    reason: str | None = None


# Callback types
StepCallback = Callable[[StepContext], Awaitable[None]]
PrepareStepCallback = Callable[[StepContext], Awaitable[StepAction]]
ToolExecutionCallback = Callable[[str, dict[str, Any], Any], Awaitable[None]]


@dataclass
class AgentDefinition:
    """
    Reusable agent definition with tool sets.

    Similar to Vercel AI SDK's agent interface but adapted for
    FlowForge's durable execution model.
    """

    name: str
    system_prompt: str
    model: str = "claude-sonnet-4-6"
    tools: list[ToolDefinition] = field(default_factory=list)

    # Execution limits
    max_steps: int = 20
    max_tool_calls: int = 50
    max_tokens_per_step: int = 4096

    # Model parameters
    temperature: float = 0.7

    # Output schema for structured outputs
    output_schema: type[BaseModel] | None = None

    # Approval configuration
    requires_approval_for: list[str] = field(default_factory=list)  # Tool names
    approval_timeout: str = "30m"

    # Callbacks
    on_step_complete: StepCallback | None = None
    prepare_step: PrepareStepCallback | None = None
    on_tool_execution: ToolExecutionCallback | None = None

    # State management
    initial_state: dict[str, Any] = field(default_factory=dict)

    def tool_requires_approval(self, tool_name: str) -> bool:
        """Check if a tool requires approval."""
        if tool_name in self.requires_approval_for:
            return True

        # Check tool definition
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.requires_approval

        return False

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def get_tool_schemas(self, provider: str = "openai") -> list[dict[str, Any]]:
        """Get tool schemas for the specified provider."""
        schemas = []
        for tool in self.tools:
            if provider == "anthropic":
                schemas.append(tool.to_anthropic_schema())
            else:
                schemas.append(tool.to_openai_schema())
        return schemas


@dataclass
class AgentState:
    """Runtime state of an agent execution."""

    iteration: int = 0
    tool_calls_count: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    status: Literal["running", "completed", "stopped", "failed", "waiting_approval"] = "running"
    custom: dict[str, Any] = field(default_factory=dict)

    def can_continue(self, agent: AgentDefinition) -> bool:
        """Check if execution can continue."""
        if self.status not in ("running", "waiting_approval"):
            return False
        if self.iteration >= agent.max_steps:
            return False
        if self.tool_calls_count >= agent.max_tool_calls:
            return False
        return True


@dataclass
class AgentExecutionResult:
    """Result of agent execution."""

    output: str | BaseModel
    status: Literal["completed", "max_steps", "max_tool_calls", "stopped", "failed"]
    iterations: int
    tool_calls_made: int
    tokens_used: int
    cost_usd: float
    messages: list[dict[str, Any]]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "output": (
                self.output.model_dump()
                if isinstance(self.output, BaseModel)
                else self.output
            ),
            "status": self.status,
            "iterations": self.iterations,
            "tool_calls_made": self.tool_calls_made,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "error": self.error,
        }
