"""Multi-agent network primitives for FlowForge."""

from dataclasses import dataclass, field
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from flowforge.router import Router
    from flowforge.agent_def import AgentDefinition


@dataclass
class NetworkState:
    """Shared state accessible to all agents in a network."""
    _data: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in state."""
        self._data[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Export state as dictionary."""
        return dict(self._data)

    @classmethod
    def from_dict(cls, data: dict) -> "NetworkState":
        """Create state from dictionary."""
        state = cls()
        state._data = dict(data)
        return state


@dataclass
class RouterContext:
    """Context provided to routing functions."""
    last_result: Any  # AgentResult from last agent
    state: NetworkState  # Shared network state
    iteration: int  # Current iteration count
    history: list[dict]  # Execution history
    agents: dict[str, "AgentDefinition"]  # Available agents


@dataclass
class NetworkResult:
    """Result of network execution."""
    output: Any  # Final output from last agent
    status: Literal["completed", "max_iterations", "failed", "handoff_failed"]
    iterations: int
    agent_calls: list[dict]  # List of agent execution records
    state: dict[str, Any]  # Final state
    total_tokens: int
    total_cost_usd: float

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "output": self.output,
            "status": self.status,
            "iterations": self.iterations,
            "agent_calls": self.agent_calls,
            "state": self.state,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
        }


class Network:
    """
    A network of collaborating agents with shared state and routing.

    Example:
        network = Network(
            name="support-network",
            agents=[classifier, support, escalation],
            router=code_router(my_router_fn),
            default_model="claude-sonnet-4-20250514",
        )
    """

    def __init__(
        self,
        name: str,
        agents: list["AgentDefinition"],
        router: "Router",
        default_model: str = "claude-sonnet-4-20250514",
        default_system: str = "",
    ):
        """
        Initialize a multi-agent network.

        Args:
            name: Unique name for the network.
            agents: List of agent definitions in the network.
            router: Router instance to determine agent execution order.
            default_model: Default model for agents without explicit models.
            default_system: Default system prompt for agents.
        """
        self.name = name
        self.agents = {agent.name: agent for agent in agents}
        self.router = router
        self.default_model = default_model
        self.default_system = default_system
        self.state = NetworkState()


def network(
    name: str,
    agents: list["AgentDefinition"],
    router: "Router",
    default_model: str = "claude-sonnet-4-20250514",
) -> Network:
    """
    Create a multi-agent network.

    Args:
        name: Unique name for the network.
        agents: List of agent definitions.
        router: Router to control agent execution flow.
        default_model: Default model for agents.

    Returns:
        Network instance ready for execution.

    Example:
        from flowforge import network, agent_def
        from flowforge.router import code

        def my_router(ctx):
            if ctx.iteration == 0:
                return ctx.agents["classifier"]
            return None

        net = network(
            name="support",
            agents=[classifier, support],
            router=code(my_router),
        )
    """
    return Network(name=name, agents=agents, router=router, default_model=default_model)
