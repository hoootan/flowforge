"""Router implementations for multi-agent networks."""

from abc import ABC, abstractmethod
from typing import Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from flowforge.network import RouterContext
    from flowforge.agent_def import AgentDefinition


class Router(ABC):
    """Base class for network routers."""

    @abstractmethod
    async def route(self, ctx: "RouterContext") -> "AgentDefinition | None":
        """
        Determine the next agent to execute, or None to complete.

        Args:
            ctx: Router context with execution state.

        Returns:
            AgentDefinition to execute next, or None to complete network.
        """
        pass


class CodeRouter(Router):
    """Router that uses a Python function for deterministic routing."""

    def __init__(self, fn: Callable[["RouterContext"], "AgentDefinition | str | None"]):
        """
        Initialize a code-based router.

        Args:
            fn: Function that takes RouterContext and returns:
                - AgentDefinition instance to route to
                - String agent name to look up and route to
                - None to complete network execution
        """
        self.fn = fn

    async def route(self, ctx: "RouterContext") -> "AgentDefinition | None":
        """Execute the routing function and resolve agent references."""
        result = self.fn(ctx)

        # Handle async functions
        if hasattr(result, "__await__"):
            result = await result

        # If string returned, look up agent by name
        if isinstance(result, str):
            agent = ctx.agents.get(result)
            if agent is None:
                raise ValueError(f"Router returned unknown agent: {result}")
            return agent

        return result


class LLMRouter(Router):
    """Router that uses an LLM to select the next agent."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        prompt: str | None = None,
        temperature: float = 0.3,
    ):
        """
        Initialize an LLM-based router.

        Args:
            model: Model to use for routing decisions.
            prompt: Custom prompt template for the routing LLM.
            temperature: Sampling temperature for routing decisions.
        """
        self.model = model
        self.prompt = prompt or self._default_prompt()
        self.temperature = temperature

    def _default_prompt(self) -> str:
        """Default prompt template for LLM routing."""
        return """You are a routing agent. Based on the conversation history and current state,
select the most appropriate agent to handle the next step, or indicate that the task is complete.

Available agents: {agents}

Current state: {state}

Last agent result: {last_result}

Respond with ONLY the agent name to route to, or "DONE" if the task is complete."""

    async def route(self, ctx: "RouterContext") -> "AgentDefinition | None":
        """
        Execute LLM-based routing.

        Note: This will be implemented within step.network() execution.
        The LLM router logic is executed by the network orchestrator.
        """
        raise NotImplementedError("LLM routing is executed within step.network()")


# Factory functions
def code(fn: Callable[["RouterContext"], "AgentDefinition | str | None"]) -> CodeRouter:
    """
    Create a code-based router from a function.

    Args:
        fn: Routing function that receives RouterContext and returns:
            - AgentDefinition to execute next
            - String agent name to look up
            - None to complete execution

    Returns:
        CodeRouter instance.

    Example:
        def my_router(ctx):
            if ctx.iteration == 0:
                return "classifier"
            if ctx.state.get("resolved"):
                return None
            return "support"

        router = code(my_router)
    """
    return CodeRouter(fn)


def llm(
    model: str = "gpt-4o-mini",
    prompt: str | None = None,
    temperature: float = 0.3,
) -> LLMRouter:
    """
    Create an LLM-based router.

    Args:
        model: Model to use for routing (default: gpt-4o-mini).
        prompt: Custom routing prompt template.
        temperature: Sampling temperature (default: 0.3).

    Returns:
        LLMRouter instance.

    Example:
        router = llm(
            model="gpt-4o",
            prompt="Select the best agent for: {last_result}",
            temperature=0.5,
        )
    """
    return LLMRouter(model=model, prompt=prompt, temperature=temperature)
