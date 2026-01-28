"""Structured output generation module.

Provides type-safe JSON output generation using Pydantic models
with the instructor library.
"""

from .outputs import (
    StructuredOutputError,
    StructuredOutputService,
    pydantic_to_tool_schema,
    validate_against_model,
)

__all__ = [
    "StructuredOutputService",
    "StructuredOutputError",
    "pydantic_to_tool_schema",
    "validate_against_model",
]
