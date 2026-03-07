"""SSE streaming types for FlowForge run events."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class RunEventType(str, Enum):
    """Event types emitted by the SSE run stream."""

    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    THINKING = "thinking"
    THINKING_CHUNK = "thinking_chunk"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    RUN_STARTED = "run_started"
    RUN_PAUSED = "run_paused"
    RUN_RESUMED = "run_resumed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


_TERMINAL_EVENTS = {RunEventType.RUN_COMPLETED, RunEventType.RUN_FAILED}


@dataclass
class RunEvent:
    """A single event from an SSE run stream."""

    event_type: RunEventType
    data: dict[str, Any]
    run_id: str
    timestamp: datetime

    @classmethod
    def from_raw(cls, event_type_str: str, json_data: str, run_id: str) -> RunEvent:
        """Parse a raw SSE event into a RunEvent."""
        parsed = json.loads(json_data) if isinstance(json_data, str) else json_data
        ts = parsed.get("timestamp") or parsed.get("ts")
        if isinstance(ts, str):
            try:
                timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        return cls(
            event_type=RunEventType(event_type_str),
            data=parsed,
            run_id=run_id,
            timestamp=timestamp,
        )

    @property
    def is_terminal(self) -> bool:
        """True if this event signals the run has ended."""
        return self.event_type in _TERMINAL_EVENTS
