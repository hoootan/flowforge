"""Agent loop primitives for FlowForge."""

from dataclasses import dataclass, field
from typing import Any, Literal

from flowforge.tools import Tool


@dataclass
class AgentConfig:
    """
    Configuration for agent execution.

    Attributes:
        model: Model to use (e.g., "claude-sonnet-4-20250514", "gpt-4o").
        system: System prompt for the agent.
        tools: List of tools the agent can use.
        max_iterations: Maximum number of agent loop iterations.
        checkpoint_strategy: When to checkpoint agent state.
        max_tool_calls: Maximum number of tool calls across all iterations.
        temperature: Sampling temperature for LLM.
    """

    model: str
    system: str = ""
    tools: list[Tool] = field(default_factory=list)
    max_iterations: int = 20
    checkpoint_strategy: Literal["per_tool", "per_iteration", "final_only"] = "per_tool"
    max_tool_calls: int = 50
    temperature: float = 0.7


@dataclass
class AgentState:
    """
    State of an agent during execution.

    Attributes:
        messages: Conversation history including user, assistant, and tool messages.
        iteration: Current iteration number.
        tool_calls_count: Total number of tool calls made.
        tokens_used: Total tokens used across all iterations.
        status: Current status of the agent.
    """

    messages: list[dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    tool_calls_count: int = 0
    tokens_used: int = 0
    status: Literal["running", "completed", "max_iterations", "max_tool_calls", "failed"] = "running"


@dataclass
class AgentResult:
    """
    Result of agent execution.

    Attributes:
        output: Final output text from the agent.
        status: Final status of the agent execution.
        iterations: Number of iterations completed.
        tool_calls_count: Total number of tool calls made.
        tokens_used: Total tokens used.
        messages: Full conversation history.
        tool_calls: Detailed list of all tool calls made.
    """

    output: str
    status: Literal["completed", "max_iterations", "max_tool_calls", "failed"]
    iterations: int
    tool_calls_count: int
    tokens_used: int
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "output": self.output,
            "status": self.status,
            "iterations": self.iterations,
            "tool_calls_count": self.tool_calls_count,
            "tokens_used": self.tokens_used,
            "messages": self.messages,
            "tool_calls": self.tool_calls,
        }
