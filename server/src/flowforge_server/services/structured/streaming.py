"""Streaming partial object generation.

Provides utilities for streaming partial structured outputs
and parsing incremental JSON.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class PartialObject:
    """Represents a partially parsed object during streaming."""

    data: dict[str, Any] = field(default_factory=dict)
    complete_fields: list[str] = field(default_factory=list)
    raw_json: str = ""
    progress_pct: float = 0.0
    is_complete: bool = False


class PartialJsonParser:
    """
    Parser for incomplete JSON strings.

    Handles streaming JSON by attempting to parse partial content
    and extracting complete fields as they become available.
    """

    def __init__(self, expected_fields: list[str] | None = None) -> None:
        """
        Initialize the parser.

        Args:
            expected_fields: List of expected field names for progress tracking
        """
        self.expected_fields = expected_fields or []
        self._buffer = ""
        self._complete_fields: set[str] = set()

    def feed(self, chunk: str) -> PartialObject:
        """
        Feed a chunk of JSON text and return the current partial object.

        Args:
            chunk: New chunk of JSON text

        Returns:
            PartialObject with current parsing state
        """
        self._buffer += chunk

        # Try to parse as complete JSON first
        try:
            data = json.loads(self._buffer)
            return PartialObject(
                data=data,
                complete_fields=list(data.keys()),
                raw_json=self._buffer,
                progress_pct=1.0,
                is_complete=True,
            )
        except json.JSONDecodeError:
            pass

        # Try to extract partial data
        data = self._extract_partial_data()
        complete_fields = list(self._complete_fields)

        # Calculate progress
        progress = 0.0
        if self.expected_fields:
            progress = len(complete_fields) / len(self.expected_fields)
        elif data:
            # Estimate based on buffer size (rough heuristic)
            progress = min(0.95, len(self._buffer) / 1000)

        return PartialObject(
            data=data,
            complete_fields=complete_fields,
            raw_json=self._buffer,
            progress_pct=progress,
            is_complete=False,
        )

    def _extract_partial_data(self) -> dict[str, Any]:
        """Extract partial data from incomplete JSON."""
        data: dict[str, Any] = {}

        # Find complete key-value pairs
        # This is a simplified parser that handles common cases
        patterns = [
            # String values: "key": "value"
            r'"([^"]+)"\s*:\s*"([^"]*)"',
            # Number values: "key": 123
            r'"([^"]+)"\s*:\s*(-?\d+\.?\d*)',
            # Boolean values: "key": true/false
            r'"([^"]+)"\s*:\s*(true|false)',
            # Null values: "key": null
            r'"([^"]+)"\s*:\s*(null)',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, self._buffer):
                key = match.group(1)
                value_str = match.group(2)

                # Convert value to appropriate type
                if pattern == patterns[0]:  # String
                    value = value_str
                elif pattern == patterns[1]:  # Number
                    value = float(value_str) if '.' in value_str else int(value_str)
                elif pattern == patterns[2]:  # Boolean
                    value = value_str == "true"
                else:  # Null
                    value = None

                data[key] = value
                self._complete_fields.add(key)

        # Try to parse arrays (simplified)
        array_pattern = r'"([^"]+)"\s*:\s*\[((?:[^\[\]]*|\[[^\]]*\])*)\]'
        for match in re.finditer(array_pattern, self._buffer):
            key = match.group(1)
            array_content = match.group(2).strip()
            try:
                # Try to parse the array content
                value = json.loads(f"[{array_content}]")
                data[key] = value
                self._complete_fields.add(key)
            except json.JSONDecodeError:
                pass

        return data

    def reset(self) -> None:
        """Reset the parser state."""
        self._buffer = ""
        self._complete_fields.clear()


async def stream_partial_objects(
    stream: AsyncIterator[dict[str, Any]],
    response_model: type[T],
) -> AsyncIterator[tuple[PartialObject, T | None]]:
    """
    Convert a content stream to partial object updates.

    Args:
        stream: Stream of content chunks (with "type": "content", "chunk": str)
        response_model: Pydantic model for the expected output

    Yields:
        Tuples of (PartialObject, validated_instance or None)
    """
    # Get expected fields from model
    schema = response_model.model_json_schema()
    expected_fields = list(schema.get("properties", {}).keys())

    parser = PartialJsonParser(expected_fields)

    async for chunk in stream:
        if chunk.get("type") == "content":
            partial = parser.feed(chunk.get("chunk", ""))

            # Try to validate partial data
            validated: T | None = None
            if partial.is_complete or len(partial.complete_fields) == len(expected_fields):
                try:
                    validated = response_model.model_validate(partial.data)
                except Exception:
                    pass

            yield partial, validated

        elif chunk.get("type") == "done":
            # Final attempt to parse and validate
            partial = parser.feed("")
            try:
                validated = response_model.model_validate(partial.data)
                partial.is_complete = True
                partial.progress_pct = 1.0
            except Exception:
                validated = None
            yield partial, validated
            break


@dataclass
class StreamingStructuredOutput:
    """
    Wrapper for streaming structured output generation.

    Provides a cleaner interface for streaming partial objects.
    """

    model: str
    response_model: type[BaseModel]
    messages: list[dict[str, str]]
    temperature: float = 0.7

    async def stream(
        self,
        ai_service: Any,  # AIService
    ) -> AsyncIterator[PartialObject]:
        """
        Stream partial objects from AI service.

        Args:
            ai_service: AI service with complete_stream method

        Yields:
            PartialObject instances
        """
        # Build prompt with schema
        schema = self.response_model.model_json_schema()
        schema_prompt = (
            f"\n\nRespond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```"
        )

        messages = list(self.messages)
        if messages and messages[-1]["role"] == "user":
            messages[-1] = {
                "role": "user",
                "content": messages[-1]["content"] + schema_prompt,
            }

        # Stream from AI service
        stream = ai_service.complete_stream(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )

        async for partial, _ in stream_partial_objects(stream, self.response_model):
            yield partial
