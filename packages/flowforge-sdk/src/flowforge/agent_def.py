"""Agent definition for multi-agent networks."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flowforge.tools import Tool


@dataclass
class AgentDefinition:
    """
    Definition of an agent within a network.

    Agents in a network are defined separately from AgentConfig to allow
    networks to manage agent instances and routing independently.

    Attributes:
        name: Unique identifier for the agent within the network.
        system: System prompt for the agent.
        tools: List of tools available to the agent.
        model: Model to use (overrides network default if specified).

    Example:
        classifier = AgentDefinition(
            name="classifier",
            system="You classify customer inquiries...",
            tools=[classify_tool],
            model="gpt-4o-mini",
        )
    """

    name: str
    system: str
    tools: list["Tool"] = field(default_factory=list)
    model: str | None = None  # Override network default


def agent_def(
    name: str,
    system: str,
    tools: list["Tool"] | None = None,
    model: str | None = None,
) -> AgentDefinition:
    """
    Create an agent definition for use in networks.

    Args:
        name: Unique agent name within the network.
        system: System prompt for agent behavior.
        tools: List of Tool instances the agent can use.
        model: Model override (uses network default if None).

    Returns:
        AgentDefinition ready for network inclusion.

    Example:
        from flowforge import agent_def, tool

        @tool()
        def search_kb(query: str) -> dict:
            return {"results": [...]}

        support = agent_def(
            name="support",
            system="Provide customer support using the knowledge base",
            tools=[search_kb],
            model="claude-sonnet-4-20250514",
        )
    """
    return AgentDefinition(
        name=name,
        system=system,
        tools=tools or [],
        model=model,
    )
