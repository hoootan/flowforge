"""Tool definition API for FlowForge agents."""

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, get_type_hints, get_origin, get_args, Literal


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

    # Handle Optional (Union with None)
    if origin is type(None) or origin is type(None).__class__:
        args = get_args(type_hint)
        if args:
            # Take first non-None type
            for arg in args:
                if arg is not type(None):
                    return _type_to_schema(arg)
        return {"type": "null"}

    # Handle Union types
    if origin is type(None).__class__ or (hasattr(origin, "__name__") and origin.__name__ == "Union"):
        args = get_args(type_hint)
        if len(args) == 2 and type(None) in args:
            # This is Optional[T]
            non_none = args[0] if args[1] is type(None) else args[1]
            schema = _type_to_schema(non_none)
            # Don't add nullable flag, just return the schema
            return schema
        else:
            # Multiple types - use anyOf
            return {"anyOf": [_type_to_schema(arg) for arg in args]}

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
            model="gpt-4o",
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
