"""Stream middleware for AI generation.

Provides middleware hooks for logging, metrics, persistence,
and other cross-cutting concerns during streaming.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

from .events import (
    ContentChunkEvent,
    ErrorEvent,
    StreamCompleteEvent,
    StreamEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)


# Type aliases for handlers
EventHandler = Callable[[StreamEvent], Awaitable[None] | None]
CompleteHandler = Callable[[StreamCompleteEvent], Awaitable[None] | None]
ErrorHandler = Callable[[Exception], Awaitable[None] | None]


class StreamMiddleware:
    """
    Middleware for processing streams.

    Allows hooking into stream events for logging,
    metrics, persistence, etc.
    """

    def __init__(self) -> None:
        self._on_event: list[EventHandler] = []
        self._on_complete: list[CompleteHandler] = []
        self._on_error: list[ErrorHandler] = []
        self._on_start: list[Callable[[], Awaitable[None] | None]] = []

    def on_start(
        self,
        handler: Callable[[], Awaitable[None] | None],
    ) -> "StreamMiddleware":
        """Register a start handler."""
        self._on_start.append(handler)
        return self

    def on_event(
        self,
        handler: EventHandler,
    ) -> "StreamMiddleware":
        """Register an event handler."""
        self._on_event.append(handler)
        return self

    def on_complete(
        self,
        handler: CompleteHandler,
    ) -> "StreamMiddleware":
        """Register a completion handler."""
        self._on_complete.append(handler)
        return self

    def on_error(
        self,
        handler: ErrorHandler,
    ) -> "StreamMiddleware":
        """Register an error handler."""
        self._on_error.append(handler)
        return self

    async def wrap(
        self,
        stream: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        """Wrap a stream with middleware handlers."""
        # Call start handlers
        for handler in self._on_start:
            result = handler()
            if result is not None:
                await result

        try:
            async for event in stream:
                # Call event handlers
                for handler in self._on_event:
                    result = handler(event)
                    if result is not None:
                        await result

                yield event

                # Call complete handlers on completion
                if isinstance(event, StreamCompleteEvent):
                    for handler in self._on_complete:
                        result = handler(event)
                        if result is not None:
                            await result

        except Exception as e:
            # Call error handlers
            for handler in self._on_error:
                result = handler(e)
                if result is not None:
                    await result
            raise


@dataclass
class StreamMetrics:
    """Metrics collected during streaming."""

    start_time: float = 0.0
    end_time: float = 0.0
    total_tokens: int = 0
    total_chunks: int = 0
    tool_calls: int = 0
    tool_call_duration_ms: int = 0
    errors: int = 0
    content_length: int = 0

    @property
    def duration_ms(self) -> float:
        """Total duration in milliseconds."""
        if self.end_time == 0:
            return 0
        return (self.end_time - self.start_time) * 1000

    @property
    def tokens_per_second(self) -> float:
        """Token generation rate."""
        duration_s = self.duration_ms / 1000
        if duration_s == 0:
            return 0
        return self.total_tokens / duration_s


def create_metrics_middleware() -> tuple[StreamMiddleware, StreamMetrics]:
    """
    Create middleware that collects stream metrics.

    Returns:
        Tuple of (middleware, metrics) - metrics are populated during streaming
    """
    metrics = StreamMetrics()

    middleware = StreamMiddleware()

    def on_start() -> None:
        metrics.start_time = time.time()

    def on_event(event: StreamEvent) -> None:
        if isinstance(event, ContentChunkEvent):
            metrics.total_chunks += 1
            metrics.total_tokens = event.tokens_so_far
            metrics.content_length = len(event.accumulated)
        elif isinstance(event, ToolCallStartEvent):
            metrics.tool_calls += 1
        elif isinstance(event, ToolCallEndEvent):
            metrics.tool_call_duration_ms += event.duration_ms
        elif isinstance(event, ErrorEvent):
            metrics.errors += 1

    def on_complete(event: StreamCompleteEvent) -> None:
        metrics.end_time = time.time()
        if event.usage:
            metrics.total_tokens = event.usage.get("total_tokens", metrics.total_tokens)

    def on_error(error: Exception) -> None:
        metrics.errors += 1
        metrics.end_time = time.time()

    middleware.on_start(on_start)
    middleware.on_event(on_event)
    middleware.on_complete(on_complete)
    middleware.on_error(on_error)

    return middleware, metrics


def create_logging_middleware(
    logger: Any,
    log_chunks: bool = False,
) -> StreamMiddleware:
    """
    Create middleware that logs stream events.

    Args:
        logger: Logger instance
        log_chunks: Whether to log individual content chunks

    Returns:
        Configured middleware
    """
    middleware = StreamMiddleware()

    def on_start() -> None:
        logger.info("Stream started")

    def on_event(event: StreamEvent) -> None:
        if isinstance(event, ContentChunkEvent):
            if log_chunks:
                logger.debug(f"Chunk: {event.chunk[:50]}...")
        elif isinstance(event, ToolCallStartEvent):
            logger.info(f"Tool call: {event.tool_name}")
        elif isinstance(event, ToolCallEndEvent):
            if event.error:
                logger.error(f"Tool error: {event.tool_name}: {event.error}")
            else:
                logger.info(f"Tool complete: {event.tool_name} ({event.duration_ms}ms)")
        elif isinstance(event, ErrorEvent):
            logger.error(f"Stream error: {event.error_type}: {event.message}")

    def on_complete(event: StreamCompleteEvent) -> None:
        logger.info(
            f"Stream complete: {event.finish_reason}, "
            f"tokens={event.usage.get('total_tokens', 0)}"
        )

    def on_error(error: Exception) -> None:
        logger.exception(f"Stream failed: {error}")

    middleware.on_start(on_start)
    middleware.on_event(on_event)
    middleware.on_complete(on_complete)
    middleware.on_error(on_error)

    return middleware


@dataclass
class ProgressInfo:
    """Information about current progress."""

    stage: str = ""
    progress_pct: float = 0.0
    tokens_generated: int = 0
    tokens_expected: int | None = None
    elapsed_seconds: float = 0.0
    eta_seconds: float | None = None
    current_content: str = ""
    partial_object: dict[str, Any] | None = None


ProgressCallback = Callable[[ProgressInfo], Awaitable[None] | None]


class ProgressTracker:
    """
    Tracks progress of LLM generation.

    Provides accurate progress estimation and callbacks.
    """

    def __init__(
        self,
        callback: ProgressCallback | None = None,
        expected_tokens: int | None = None,
        update_interval_ms: int = 100,
    ) -> None:
        """
        Initialize the progress tracker.

        Args:
            callback: Progress callback function
            expected_tokens: Expected number of tokens (for progress estimation)
            update_interval_ms: Minimum interval between updates
        """
        self.callback = callback
        self.expected_tokens = expected_tokens
        self.update_interval_ms = update_interval_ms

        self._start_time: float = 0.0
        self._tokens = 0
        self._content = ""
        self._last_update = 0.0

    async def on_start(self) -> None:
        """Called when generation starts."""
        self._start_time = time.time()
        self._last_update = self._start_time

    async def on_token(self, token: str) -> None:
        """Called for each generated token."""
        self._tokens += 1
        self._content += token

        if self.callback and self._should_update():
            await self._emit_progress()

    async def on_chunk(self, chunk: str, tokens: int) -> None:
        """Called for content chunks (alternative to on_token)."""
        self._tokens = tokens
        self._content += chunk

        if self.callback and self._should_update():
            await self._emit_progress()

    async def on_complete(self) -> None:
        """Called when generation is complete."""
        if self.callback:
            info = self._build_progress_info()
            info.progress_pct = 1.0
            info.stage = "complete"
            result = self.callback(info)
            if result is not None:
                await result

    def _should_update(self) -> bool:
        """Check if we should emit a progress update."""
        now = time.time() * 1000
        if now - (self._last_update * 1000) >= self.update_interval_ms:
            self._last_update = now / 1000
            return True
        return False

    async def _emit_progress(self) -> None:
        """Emit a progress update."""
        if self.callback:
            info = self._build_progress_info()
            result = self.callback(info)
            if result is not None:
                await result

    def _build_progress_info(self) -> ProgressInfo:
        """Build progress info from current state."""
        elapsed = time.time() - self._start_time

        progress = 0.0
        eta: float | None = None

        if self.expected_tokens and self.expected_tokens > 0:
            progress = min(self._tokens / self.expected_tokens, 0.99)
            if progress > 0:
                total_time = elapsed / progress
                eta = max(0, total_time - elapsed)

        return ProgressInfo(
            stage="generating",
            progress_pct=progress,
            tokens_generated=self._tokens,
            tokens_expected=self.expected_tokens,
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            current_content=self._content,
        )

    def to_middleware(self) -> StreamMiddleware:
        """Convert tracker to middleware."""
        middleware = StreamMiddleware()
        middleware.on_start(self.on_start)

        async def handle_event(event: StreamEvent) -> None:
            if isinstance(event, ContentChunkEvent):
                await self.on_chunk(event.chunk, event.tokens_so_far)

        async def handle_complete(event: StreamCompleteEvent) -> None:
            await self.on_complete()

        middleware.on_event(handle_event)
        middleware.on_complete(handle_complete)

        return middleware
