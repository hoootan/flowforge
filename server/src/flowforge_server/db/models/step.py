"""Step model for individual steps within a run."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.run import Run


class StepType(str, Enum):
    """Type of step being executed."""

    RUN = "run"
    SLEEP = "sleep"
    AI = "ai"
    WAIT_FOR_EVENT = "wait_for_event"
    INVOKE = "invoke"
    SEND_EVENT = "send_event"


class StepStatus(str, Enum):
    """Status of a step execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SLEEPING = "sleeping"  # For sleep/wait steps
    WAITING = "waiting"  # For wait_for_event steps


class Step(Base, TimestampMixin):
    """
    Individual step within a function run.

    Steps represent units of work that can be independently
    retried, memoized, and monitored.
    """

    __tablename__ = "steps"

    __table_args__ = (
        UniqueConstraint("run_id", "step_hash", name="uq_step_run_step_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User-defined step ID
    step_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Unique identifier for step within a run (e.g., "agent:run-uuid:iteration")
    step_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Type of step
    step_type: Mapped[StepType] = mapped_column(
        String(50),
        nullable=False,
        default=StepType.RUN,
    )

    # Current status
    status: Mapped[StepStatus] = mapped_column(
        String(50),
        nullable=False,
        default=StepStatus.PENDING,
    )

    # Input data for the step
    input: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Output/result of the step
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Error details if failed
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Attempt tracking
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)

    # For sleep/scheduled steps
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # For wait_for_event steps
    wait_event_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wait_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    wait_timeout_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Tool-specific columns for agent steps
    tool_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    tool_call_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    tool_input: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Agent state snapshot for checkpointing
    agent_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship
    run: Mapped["Run"] = relationship("Run", back_populates="steps")

    def __repr__(self) -> str:
        return f"<Step {self.step_id} ({self.status})>"

    @property
    def is_terminal(self) -> bool:
        """Check if the step is in a terminal state."""
        return self.status in (StepStatus.COMPLETED, StepStatus.FAILED)

    @property
    def can_retry(self) -> bool:
        """Check if the step can be retried."""
        return self.attempt < self.max_attempts

    @property
    def is_waiting(self) -> bool:
        """Check if the step is waiting (sleep or event)."""
        return self.status in (StepStatus.SLEEPING, StepStatus.WAITING)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "run_id": str(self.run_id),
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "status": self.status.value,
            "input": self.input,
            "output": self.output,
            "error": self.error,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "agent_state": self.agent_state,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat(),
        }
