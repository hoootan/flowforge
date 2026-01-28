"""Context and Event classes for FlowForge function execution."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from flowforge.steps import StepManager


@dataclass
class Event:
    """
    Represents an event that triggered a function.

    Events are the primary way to trigger FlowForge functions.
    They carry data from your application to the workflow engine.
    """

    id: str
    """Unique identifier for this event."""

    name: str
    """Event type name (e.g., "order/created", "user/signup")."""

    data: dict[str, Any]
    """Event payload data."""

    timestamp: datetime
    """When the event was created."""

    user_id: str | None = None
    """Optional user ID associated with this event."""

    def __post_init__(self) -> None:
        # Ensure timestamp is a datetime object
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create an Event from a dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            data=data.get("data", {}),
            timestamp=data["timestamp"],
            user_id=data.get("user_id"),
        )


@dataclass
class Context:
    """
    Execution context passed to FlowForge functions.

    Contains the triggering event, run metadata, and provides
    methods for logging and accessing step functionality.
    """

    event: Event
    """The event that triggered this function execution."""

    run_id: str
    """Unique identifier for this function run."""

    function_id: str
    """Identifier of the function being executed."""

    attempt: int = 1
    """Current attempt number (1-based)."""

    _step_manager: "StepManager | None" = field(default=None, repr=False)
    """Internal step manager for executing steps."""

    _logger: logging.Logger | None = field(default=None, repr=False)
    """Logger instance for this context."""

    def __post_init__(self) -> None:
        if self._logger is None:
            self._logger = logging.getLogger(f"flowforge.run.{self.run_id[:8]}")

    @property
    def step(self) -> "StepManager":
        """Access the step manager for executing workflow steps."""
        if self._step_manager is None:
            raise RuntimeError("Step manager not initialized. Context is not properly configured.")
        return self._step_manager

    def log(
        self,
        message: str,
        level: str = "info",
        **kwargs: Any,
    ) -> None:
        """
        Log a message associated with this run.

        Args:
            message: The log message.
            level: Log level ("debug", "info", "warning", "error").
            **kwargs: Additional context to include in the log.

        Example:
            ctx.log("Processing order", order_id=order["id"])
            ctx.log("Payment failed", level="error", reason=error.message)
        """
        if self._logger is None:
            return

        log_data = {
            "run_id": self.run_id,
            "function_id": self.function_id,
            "attempt": self.attempt,
            **kwargs,
        }

        log_level = getattr(logging, level.upper(), logging.INFO)
        self._logger.log(log_level, message, extra=log_data)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "event": self.event.to_dict(),
            "run_id": self.run_id,
            "function_id": self.function_id,
            "attempt": self.attempt,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        step_manager: "StepManager | None" = None,
    ) -> "Context":
        """Create a Context from a dictionary."""
        return cls(
            event=Event.from_dict(data["event"]),
            run_id=data["run_id"],
            function_id=data["function_id"],
            attempt=data.get("attempt", 1),
            _step_manager=step_manager,
        )
