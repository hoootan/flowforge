"""Run model for function executions."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.function import Function
    from flowforge_server.db.models.step import Step


class RunStatus(str, Enum):
    """Status of a function run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"  # Waiting for event or sleeping


class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current: RunStatus, target: RunStatus):
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid state transition: {current.value} -> {target.value}"
        )


# Valid state transitions for runs
# Key: current state, Value: set of valid target states
VALID_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.PENDING: {
        RunStatus.RUNNING,  # Started execution
        RunStatus.CANCELLED,  # Cancelled before start
    },
    RunStatus.RUNNING: {
        RunStatus.COMPLETED,  # Finished successfully
        RunStatus.FAILED,  # Execution failed
        RunStatus.CANCELLED,  # Cancelled during execution
        RunStatus.PAUSED,  # Waiting for event/sleep
        RunStatus.PENDING,  # Re-queued for retry
    },
    RunStatus.PAUSED: {
        RunStatus.RUNNING,  # Resumed after event/sleep
        RunStatus.CANCELLED,  # Cancelled while paused
        RunStatus.FAILED,  # Timeout or error while paused
    },
    RunStatus.COMPLETED: set(),  # Terminal state - no transitions allowed
    RunStatus.FAILED: {
        RunStatus.PENDING,  # Manual retry (re-queue)
    },
    RunStatus.CANCELLED: set(),  # Terminal state - no transitions allowed
}


class Run(Base, TimestampMixin):
    """
    A single execution of a function.

    Runs track the lifecycle of a function execution, including
    all steps, retries, and final output.
    """

    __tablename__ = "runs"

    # Composite indexes for common query patterns
    __table_args__ = (
        # For listing runs by tenant, filtered by status, ordered by date
        Index("ix_runs_tenant_status_created", "tenant_id", "status", "created_at"),
        # For finding runs to resume (paused runs past their resume time)
        Index("ix_runs_status_resume", "status", "resume_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    function_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("functions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Reference to the triggering event (if applicable)
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Parent run ID for sub-agent / invoke tracking
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Idempotency key for deduplication
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Current status
    status: Mapped[RunStatus] = mapped_column(
        String(50),
        nullable=False,
        default=RunStatus.PENDING,
        index=True,
    )

    # How this run was triggered
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # The triggering data (event, cron info, etc.)
    trigger_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Current attempt number
    attempt: Mapped[int] = mapped_column(Integer, default=1)

    # Maximum attempts allowed
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)

    # Function output (when completed)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Error details (when failed)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # For paused runs: when to resume
    resume_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    function: Mapped["Function"] = relationship("Function", back_populates="runs")

    steps: Mapped[list["Step"]] = relationship(
        "Step",
        back_populates="run",
        lazy="select",
        order_by="Step.created_at",
    )

    # Self-referential parent/child run relationship
    parent_run: Mapped["Run | None"] = relationship(
        "Run",
        remote_side="Run.id",
        foreign_keys=[parent_run_id],
        back_populates="child_runs",
    )

    child_runs: Mapped[list["Run"]] = relationship(
        "Run",
        foreign_keys="Run.parent_run_id",
        back_populates="parent_run",
    )

    def __repr__(self) -> str:
        return f"<Run {self.id} ({self.status})>"

    @property
    def is_terminal(self) -> bool:
        """Check if the run is in a terminal state."""
        return self.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED)

    @property
    def can_retry(self) -> bool:
        """Check if the run can be retried."""
        return self.attempt < self.max_attempts

    @property
    def completed_steps(self) -> dict[str, Any]:
        """Get dictionary of completed step results for memoization."""
        return {
            step.step_hash: step.output
            for step in self.steps
            if step.status == "completed" and step.output is not None
        }

    def can_transition_to(self, target: RunStatus) -> bool:
        """
        Check if a transition to the target state is valid.

        Args:
            target: The desired target state

        Returns:
            True if the transition is valid, False otherwise
        """
        valid_targets = VALID_TRANSITIONS.get(self.status, set())
        return target in valid_targets

    def transition_to(self, target: RunStatus) -> None:
        """
        Transition to a new state with validation.

        Args:
            target: The desired target state

        Raises:
            InvalidStateTransition: If the transition is not valid
        """
        if not self.can_transition_to(target):
            raise InvalidStateTransition(self.status, target)

        self.status = target

        # Update timestamps based on transition
        if target == RunStatus.RUNNING and self.started_at is None:
            self.started_at = datetime.utcnow()
        elif target in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            self.ended_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "function_id": str(self.function_id),
            "parent_run_id": str(self.parent_run_id) if self.parent_run_id else None,
            "status": self.status.value,
            "trigger_type": self.trigger_type,
            "trigger_data": self.trigger_data,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat(),
        }
