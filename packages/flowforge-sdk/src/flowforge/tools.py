"""Tool definition API for FlowForge agents."""

from __future__ import annotations

import inspect
import types as _builtintypes
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Union, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from flowforge.agent_def import AgentDefinition


@dataclass
class Tool:
    """
    Represents a tool/function that can be called by AI agents.

    Tools are Python functions that agents can invoke to interact with
    external systems, retrieve data, or perform actions.

    Attributes:
        name: Unique identifier for the tool.
        description: Human-readable description of what the tool does.
        fn: The callable function to execute when the tool is invoked.
        parameters: JSON Schema describing the function parameters.
        requires_approval: Whether this tool requires human approval before execution.
        approval_timeout: How long to wait for approval before timing out.
    """

    name: str
    description: str
    fn: Callable[..., Any | Awaitable[Any]]
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    approval_timeout: str | None = None

    def to_openai_schema(self) -> dict[str, Any]:
        """
        Convert tool to OpenAI function calling schema.

        Returns:
            Dictionary in OpenAI function calling format.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_schema(self) -> dict[str, Any]:
        """
        Convert tool to Anthropic tool calling schema.

        Returns:
            Dictionary in Anthropic tool format.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


def _type_to_schema(type_hint: Any) -> dict[str, Any]:
    """
    Convert a Python type hint to JSON Schema.

    Args:
        type_hint: Python type annotation.

    Returns:
        JSON Schema dictionary representing the type.
    """
    # Handle None type
    if type_hint is type(None):
        return {"type": "null"}

    # Get the origin type for generics
    origin = get_origin(type_hint)

    # Handle Union types (typing.Union / Optional and Python 3.10+ X | Y syntax)
    _is_union = origin is Union or (
        hasattr(_builtintypes, "UnionType") and type(type_hint) is _builtintypes.UnionType
    )
    if _is_union:
        args = get_args(type_hint)
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return _type_to_schema(non_none_args[0])
        return {"anyOf": [_type_to_schema(a) for a in non_none_args]}

    # Handle Literal types
    if hasattr(type_hint, "__origin__") and type_hint.__origin__ is Literal:
        values = get_args(type_hint)
        # Infer type from first value
        if values:
            first_value = values[0]
            if isinstance(first_value, str):
                return {"type": "string", "enum": list(values)}
            elif isinstance(first_value, int):
                return {"type": "integer", "enum": list(values)}
            elif isinstance(first_value, float):
                return {"type": "number", "enum": list(values)}
            elif isinstance(first_value, bool):
                return {"type": "boolean", "enum": list(values)}
        return {"type": "string"}

    # Handle list/List
    if origin is list:
        args = get_args(type_hint)
        if args:
            return {"type": "array", "items": _type_to_schema(args[0])}
        return {"type": "array"}

    # Handle dict/Dict
    if origin is dict:
        args = get_args(type_hint)
        if len(args) >= 2:
            return {
                "type": "object",
                "additionalProperties": _type_to_schema(args[1]),
            }
        return {"type": "object"}

    # Handle basic types
    type_mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }

    # Check if it's a basic type
    for py_type, schema in type_mapping.items():
        if type_hint is py_type:
            return schema

    # Default to object for unknown types
    return {"type": "object"}


def _infer_parameters(fn: Callable[..., Any]) -> dict[str, Any]:
    """
    Infer JSON Schema parameters from function signature.

    Extracts type hints, default values, and docstring to build
    a complete JSON Schema for the function parameters.

    Args:
        fn: The function to analyze.

    Returns:
        JSON Schema dictionary for the function parameters.
    """
    sig = inspect.signature(fn)
    type_hints = get_type_hints(fn)

    # Parse docstring for parameter descriptions
    docstring = inspect.getdoc(fn) or ""
    param_descriptions = {}

    # Simple docstring parsing - look for "Args:" section
    if "Args:" in docstring:
        args_section = docstring.split("Args:")[1]
        if "Returns:" in args_section:
            args_section = args_section.split("Returns:")[0]

        for line in args_section.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith(("Returns", "Raises", "Example")):
                parts = line.split(":", 1)
                param_name = parts[0].strip()
                param_desc = parts[1].strip() if len(parts) > 1 else ""
                param_descriptions[param_name] = param_desc

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        # Skip self, cls, *args, **kwargs
        if param_name in ("self", "cls") or param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        # Get type hint
        type_hint = type_hints.get(param_name, str)

        # Convert to JSON Schema
        schema = _type_to_schema(type_hint)

        # Add description if available
        if param_name in param_descriptions:
            schema["description"] = param_descriptions[param_name]

        properties[param_name] = schema

        # Check if required (no default value)
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    result = {
        "type": "object",
        "properties": properties,
    }

    if required:
        result["required"] = required

    return result


def tool(
    name: str | None = None,
    description: str | None = None,
    requires_approval: bool = False,
    approval_timeout: str | None = None,
) -> Callable[[Callable[..., Any]], Tool]:
    """
    Decorator to create a Tool from a Python function.

    Automatically extracts parameter schema from type hints and docstring.
    Supports both sync and async functions.

    Args:
        name: Tool name (defaults to function name).
        description: Tool description (defaults to docstring summary).
        requires_approval: Whether the tool requires human approval.
        approval_timeout: How long to wait for approval (e.g., "30m", "1h").

    Returns:
        Decorator that converts a function to a Tool.

    Example:
        @tool(
            name="search_database",
            description="Search customer database",
            requires_approval=False,
        )
        async def search_database(query: str, field: str = "email") -> dict:
            return {"results": [...]}

        # Use in step.ai()
        result = await step.ai(
            "search-step",
            model="gpt-5",
            prompt="Find customer john@example.com",
            tools=[search_database],
        )
    """

    def decorator(fn: Callable[..., Any]) -> Tool:
        # Get function name and docstring
        fn_name = name or fn.__name__
        fn_doc = description or (inspect.getdoc(fn) or "").split("\n")[0]

        # Infer parameters from function signature
        parameters = _infer_parameters(fn)

        return Tool(
            name=fn_name,
            description=fn_doc,
            fn=fn,
            parameters=parameters,
            requires_approval=requires_approval,
            approval_timeout=approval_timeout,
        )

    return decorator


@dataclass
class SubAgentConfig:
    """Configuration for a sub-agent tool.

    This is attached to a Tool via ``_sub_agent_config`` so that
    ``step.agent()`` can detect the tool as a sub-agent delegation
    and run a nested agent loop instead of calling ``tool.fn``.

    Attributes:
        agent: The agent definition to run as a sub-agent.
        max_iterations: Max iterations for the sub-agent loop.
        max_tool_calls: Max tool calls for the sub-agent loop.
        temperature: Sampling temperature for the sub-agent LLM.
        context_mode: How much parent context to share with the sub-agent.
    """

    agent: AgentDefinition
    max_iterations: int = 20
    max_tool_calls: int = 50
    temperature: float = 0.7
    context_mode: Literal["task_only", "summary", "full_history"] = "task_only"


def sub_agent(
    agent: AgentDefinition,
    *,
    description: str | None = None,
    max_iterations: int = 20,
    max_tool_calls: int = 50,
    temperature: float = 0.7,
    context_mode: Literal["task_only", "summary", "full_history"] = "task_only",
) -> Tool:
    """Create a Tool that delegates work to a sub-agent.

    When the parent agent's LLM calls this tool, ``step.agent()``
    intercepts the call and runs a nested agent loop with the
    given agent definition, returning the sub-agent's output as
    the tool result.

    Args:
        agent: Agent definition describing the sub-agent.
        description: Tool description shown to the LLM. If omitted,
            auto-generated from the agent name and system prompt.
        max_iterations: Maximum reasoning iterations for the sub-agent.
        max_tool_calls: Maximum tool calls for the sub-agent.
        temperature: Sampling temperature for the sub-agent.
        context_mode: How much parent context to pass:
            - "task_only" (default): Only the delegated task string.
            - "summary": Task + last 3 parent exchanges as context.
            - "full_history": Task + full parent conversation.

    Returns:
        A Tool with a single ``task: str`` parameter and a
        ``_sub_agent_config`` attribute for detection.

    Example:
        researcher = agent_def(
            name="researcher",
            system="You research topics thoroughly.",
            tools=[web_search],
        )

        research_tool = sub_agent(researcher, description="Delegate research tasks.")

        result = await step.agent(
            "manager",
            task="Plan a project",
            model="claude-opus-4-6",
            tools=[research_tool],
        )
    """
    desc = description or f"Delegate a task to the '{agent.name}' sub-agent. {agent.system[:100]}"

    async def _placeholder(task: str) -> str:  # noqa: ARG001
        raise RuntimeError(
            "Sub-agent tool should not be called directly. "
            "It is intercepted by step.agent()."
        )

    t = Tool(
        name=agent.name,
        description=desc,
        fn=_placeholder,
        parameters={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task to delegate to the sub-agent.",
                },
            },
            "required": ["task"],
        },
    )

    # Attach sub-agent config as a marker for step.agent() detection
    t._sub_agent_config = SubAgentConfig(  # type: ignore[attr-defined]
        agent=agent,
        max_iterations=max_iterations,
        max_tool_calls=max_tool_calls,
        temperature=temperature,
        context_mode=context_mode,
    )

    return t
