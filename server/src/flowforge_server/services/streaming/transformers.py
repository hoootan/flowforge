"""Stream transformers for AI generation.

Provides composable transformers for processing and enriching
streaming AI responses.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, AsyncIterator, Type

from pydantic import BaseModel

from .events import (
    ContentChunkEvent,
    PartialObjectEvent,
    ProgressEvent,
    StreamCompleteEvent,
    StreamEvent,
)

if TYPE_CHECKING:
    pass


class StreamTransformer(ABC):
    """Base class for stream transformers."""

    @abstractmethod
    async def transform(
        self,
        stream: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        """Transform a stream of events."""
        ...


class TokenCounterTransformer(StreamTransformer):
    """
    Adds accurate token counts to stream events.

    Uses tiktoken for accurate OpenAI token counting.
    Falls back to character-based estimation for other providers.
    """

    def __init__(self, model: str = "gpt-4o") -> None:
        """
        Initialize the token counter.

        Args:
            model: Model name for tokenizer selection
        """
        self.model = model
        self._count = 0
        self._encoder = None

    def _get_encoder(self) -> Any:
        """Get or create the token encoder."""
        if self._encoder is None:
            try:
                import tiktoken

                try:
                    self._encoder = tiktoken.encoding_for_model(self.model)
                except KeyError:
                    # Fall back to cl100k_base for unknown models
                    self._encoder = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                # Tiktoken not available, will use estimation
                self._encoder = False
        return self._encoder

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        encoder = self._get_encoder()
        if encoder and encoder is not False:
            return len(encoder.encode(text))
        # Fallback: estimate ~4 characters per token
        return len(text) // 4

    async def transform(
        self,
        stream: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        """Add token counts to content chunk events."""
        async for event in stream:
            if isinstance(event, ContentChunkEvent):
                self._count += self._count_tokens(event.chunk)
                event.tokens_so_far = self._count
            yield event


class ProgressEstimatorTransformer(StreamTransformer):
    """
    Estimates progress based on expected output length.

    Emits ProgressEvent alongside content chunks.
    """

    def __init__(
        self,
        expected_tokens: int = 1000,
        emit_interval_ms: int = 500,
    ) -> None:
        """
        Initialize the progress estimator.

        Args:
            expected_tokens: Expected number of output tokens
            emit_interval_ms: Minimum interval between progress events
        """
        self.expected_tokens = expected_tokens
        self.emit_interval_ms = emit_interval_ms
        self._last_emit = 0.0

    async def transform(
        self,
        stream: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        """Emit progress events alongside content chunks."""
        tokens_seen = 0
        start_time = time.time()

        async for event in stream:
            if isinstance(event, ContentChunkEvent):
                tokens_seen = event.tokens_so_far
                now = time.time()

                # Check if we should emit a progress event
                elapsed_ms = (now - self._last_emit) * 1000
                if elapsed_ms >= self.emit_interval_ms:
                    progress = min(tokens_seen / self.expected_tokens, 0.99)
                    elapsed_seconds = now - start_time

                    # Estimate ETA
                    eta: float | None = None
                    if progress > 0:
                        total_time = elapsed_seconds / progress
                        eta = max(0, total_time - elapsed_seconds)

                    yield ProgressEvent(
                        stage="generating",
                        progress_pct=progress,
                        message=f"Generated {tokens_seen} tokens",
                        eta_seconds=eta,
                    )
                    self._last_emit = now

            yield event

            # Emit final progress on completion
            if isinstance(event, StreamCompleteEvent):
                yield ProgressEvent(
                    stage="complete",
                    progress_pct=1.0,
                    message=f"Completed with {tokens_seen} tokens",
                    eta_seconds=0,
                )


class PartialObjectTransformer(StreamTransformer):
    """
    Parses streaming JSON into partial Pydantic objects.

    Emits PartialObjectEvent as fields become available.
    """

    def __init__(self, response_model: Type[BaseModel]) -> None:
        """
        Initialize the partial object transformer.

        Args:
            response_model: Pydantic model for the expected output
        """
        self.response_model = response_model
        self._buffer = ""

        # Get expected fields from model schema
        schema = response_model.model_json_schema()
        self.expected_fields = list(schema.get("properties", {}).keys())

    async def transform(
        self,
        stream: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        """Convert content chunks to partial object events."""
        import json
        import re

        async for event in stream:
            if isinstance(event, ContentChunkEvent):
                self._buffer += event.chunk

                # Try to extract partial data
                partial_data = self._extract_partial_data()
                if partial_data:
                    complete_fields = list(partial_data.keys())
                    progress = (
                        len(complete_fields) / len(self.expected_fields)
                        if self.expected_fields
                        else 0.5
                    )

                    yield PartialObjectEvent(
                        partial=partial_data,
                        complete_fields=complete_fields,
                        progress_pct=progress,
                    )

            yield event

    def _extract_partial_data(self) -> dict[str, Any]:
        """Extract partial data from the buffer."""
        import json
        import re

        data: dict[str, Any] = {}

        # Try to parse as complete JSON first
        try:
            return json.loads(self._buffer)
        except json.JSONDecodeError:
            pass

        # Extract individual fields using regex
        patterns = [
            # String values
            (r'"([^"]+)"\s*:\s*"([^"]*)"', str),
            # Number values
            (r'"([^"]+)"\s*:\s*(-?\d+\.?\d*)', lambda x: float(x) if "." in x else int(x)),
            # Boolean values
            (r'"([^"]+)"\s*:\s*(true|false)', lambda x: x == "true"),
            # Null values
            (r'"([^"]+)"\s*:\s*(null)', lambda x: None),
        ]

        for pattern, converter in patterns:
            for match in re.finditer(pattern, self._buffer):
                key = match.group(1)
                value_str = match.group(2)
                try:
                    data[key] = converter(value_str)
                except (ValueError, TypeError):
                    pass

        return data


class ThrottleTransformer(StreamTransformer):
    """
    Throttles events to a maximum rate.

    Useful for limiting update frequency to UI clients.
    """

    def __init__(self, events_per_second: float = 30) -> None:
        """
        Initialize the throttle transformer.

        Args:
            events_per_second: Maximum event rate
        """
        self.min_interval = 1.0 / events_per_second
        self._last_yield = 0.0
        self._pending: StreamEvent | None = None

    async def transform(
        self,
        stream: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        """Throttle events to maximum rate."""
        async for event in stream:
            now = time.time()

            # Always yield non-content events immediately
            if not isinstance(event, ContentChunkEvent):
                # Flush any pending event first
                if self._pending:
                    yield self._pending
                    self._pending = None
                yield event
                self._last_yield = now
                continue

            # Check if enough time has passed
            if now - self._last_yield >= self.min_interval:
                # Flush pending if exists
                if self._pending:
                    yield self._pending
                yield event
                self._pending = None
                self._last_yield = now
            else:
                # Store as pending (will be combined with next)
                if self._pending and isinstance(self._pending, ContentChunkEvent):
                    # Combine chunks
                    self._pending.chunk += event.chunk
                    self._pending.accumulated = event.accumulated
                    self._pending.tokens_so_far = event.tokens_so_far
                else:
                    self._pending = event

        # Flush any remaining pending event
        if self._pending:
            yield self._pending


class BufferTransformer(StreamTransformer):
    """
    Buffers content chunks to reduce event frequency.

    Emits buffered content at regular intervals or when buffer is full.
    """

    def __init__(
        self,
        buffer_size: int = 50,
        flush_interval_ms: int = 100,
    ) -> None:
        """
        Initialize the buffer transformer.

        Args:
            buffer_size: Maximum characters to buffer
            flush_interval_ms: Maximum time to hold content
        """
        self.buffer_size = buffer_size
        self.flush_interval_ms = flush_interval_ms
        self._buffer = ""
        self._last_flush = 0.0
        self._accumulated = ""
        self._tokens = 0

    async def transform(
        self,
        stream: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        """Buffer content chunks."""
        async for event in stream:
            if isinstance(event, ContentChunkEvent):
                self._buffer += event.chunk
                self._accumulated = event.accumulated
                self._tokens = event.tokens_so_far

                now = time.time()
                elapsed_ms = (now - self._last_flush) * 1000

                # Flush if buffer full or interval exceeded
                should_flush = (
                    len(self._buffer) >= self.buffer_size
                    or elapsed_ms >= self.flush_interval_ms
                )

                if should_flush and self._buffer:
                    yield ContentChunkEvent(
                        chunk=self._buffer,
                        accumulated=self._accumulated,
                        tokens_so_far=self._tokens,
                    )
                    self._buffer = ""
                    self._last_flush = now
            else:
                # Flush buffer before non-content events
                if self._buffer:
                    yield ContentChunkEvent(
                        chunk=self._buffer,
                        accumulated=self._accumulated,
                        tokens_so_far=self._tokens,
                    )
                    self._buffer = ""
                yield event

        # Flush remaining buffer
        if self._buffer:
            yield ContentChunkEvent(
                chunk=self._buffer,
                accumulated=self._accumulated,
                tokens_so_far=self._tokens,
            )


def compose_transformers(
    *transformers: StreamTransformer,
) -> StreamTransformer:
    """
    Compose multiple transformers into one.

    Args:
        *transformers: Transformers to compose (applied in order)

    Returns:
        A new transformer that applies all transformers in sequence
    """

    class ComposedTransformer(StreamTransformer):
        def __init__(self, transformers: tuple[StreamTransformer, ...]) -> None:
            self.transformers = transformers

        async def transform(
            self,
            stream: AsyncIterator[StreamEvent],
        ) -> AsyncIterator[StreamEvent]:
            for transformer in self.transformers:
                stream = transformer.transform(stream)
            async for event in stream:
                yield event

    return ComposedTransformer(transformers)
