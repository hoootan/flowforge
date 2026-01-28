"""Stream event types for AI generation.

Defines typed events for streaming AI responses including
content chunks, tool calls, progress updates, and completion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class StreamEvent:
    """Base class for stream events."""

    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ContentChunkEvent(StreamEvent):
    """A chunk of generated content."""

    event_type: str = "content_chunk"
    chunk: str = ""
    accumulated: str = ""
    tokens_so_far: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "chunk": self.chunk,
            "accumulated": self.accumulated,
            "tokens_so_far": self.tokens_so_far,
        }


@dataclass
class PartialObjectEvent(StreamEvent):
    """Partial structured object during streaming."""

    event_type: str = "partial_object"
    partial: dict[str, Any] = field(default_factory=dict)
    complete_fields: list[str] = field(default_factory=list)
    progress_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "partial": self.partial,
            "complete_fields": self.complete_fields,
            "progress_pct": self.progress_pct,
        }


@dataclass
class ToolCallStartEvent(StreamEvent):
    """Tool call is starting."""

    event_type: str = "tool_call_start"
    tool_name: str = ""
    tool_call_id: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "arguments": self.arguments,
        }


@dataclass
class ToolCallEndEvent(StreamEvent):
    """Tool call completed."""

    event_type: str = "tool_call_end"
    tool_name: str = ""
    tool_call_id: str = ""
    result: Any = None
    error: str | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ProgressEvent(StreamEvent):
    """Progress update for long-running operations."""

    event_type: str = "progress"
    stage: str = ""
    progress_pct: float = 0.0
    message: str = ""
    eta_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "stage": self.stage,
            "progress_pct": self.progress_pct,
            "message": self.message,
            "eta_seconds": self.eta_seconds,
        }


@dataclass
class ThinkingEvent(StreamEvent):
    """Agent thinking/reasoning event."""

    event_type: str = "thinking"
    status: Literal["start", "chunk", "end"] = "chunk"
    content: str = ""
    iteration: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "status": self.status,
            "content": self.content,
            "iteration": self.iteration,
        }


@dataclass
class ApprovalRequiredEvent(StreamEvent):
    """Human approval required for tool execution."""

    event_type: str = "approval_required"
    approval_id: str = ""
    tool_name: str = ""
    tool_call_id: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    timeout_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "approval_id": self.approval_id,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "arguments": self.arguments,
            "timeout_at": self.timeout_at.isoformat() if self.timeout_at else None,
        }


@dataclass
class ApprovalResolvedEvent(StreamEvent):
    """Human approval resolved."""

    event_type: str = "approval_resolved"
    approval_id: str = ""
    status: Literal["approved", "rejected", "timeout"] = "approved"
    resolved_by: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "approval_id": self.approval_id,
            "status": self.status,
            "resolved_by": self.resolved_by,
            "reason": self.reason,
        }


@dataclass
class IterationCompleteEvent(StreamEvent):
    """Agent iteration completed."""

    event_type: str = "iteration_complete"
    iteration: int = 0
    tool_calls_made: int = 0
    tokens_used: int = 0
    has_more: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "iteration": self.iteration,
            "tool_calls_made": self.tool_calls_made,
            "tokens_used": self.tokens_used,
            "has_more": self.has_more,
        }


@dataclass
class StreamCompleteEvent(StreamEvent):
    """Stream has completed."""

    event_type: str = "complete"
    content: str = ""
    structured_output: dict[str, Any] | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    finish_reason: str = "stop"
    total_iterations: int = 0
    total_tool_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "content": self.content,
            "structured_output": self.structured_output,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "total_iterations": self.total_iterations,
            "total_tool_calls": self.total_tool_calls,
        }


@dataclass
class ErrorEvent(StreamEvent):
    """Error during streaming."""

    event_type: str = "error"
    error_type: str = ""
    message: str = ""
    recoverable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "error_type": self.error_type,
            "message": self.message,
            "recoverable": self.recoverable,
        }


# Type alias for all event types
AnyStreamEvent = (
    ContentChunkEvent
    | PartialObjectEvent
    | ToolCallStartEvent
    | ToolCallEndEvent
    | ProgressEvent
    | ThinkingEvent
    | ApprovalRequiredEvent
    | ApprovalResolvedEvent
    | IterationCompleteEvent
    | StreamCompleteEvent
    | ErrorEvent
)
