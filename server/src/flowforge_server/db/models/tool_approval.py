"""ToolApproval model for Human-in-the-Loop tool approval."""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.run import Run
    from flowforge_server.db.models.step import Step


class ApprovalStatus(str, Enum):
    """Status of a tool approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ToolApproval(Base, TimestampMixin):
    """
    Human-in-the-Loop approval request for tool execution.

    When an agent attempts to call a tool that requires approval,
    a ToolApproval record is created and the execution pauses until
    a human approves, rejects, or the request times out.
    """

    __tablename__ = "tool_approvals"

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

    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tool details
    tool_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    tool_call_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    tool_arguments: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Approval status
    status: Mapped[ApprovalStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True,
    )

    # Timing
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    timeout_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Resolution details
    resolved_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Modified arguments (e.g., user input for ask_user tool)
    modified_arguments: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", foreign_keys=[run_id])
    step: Mapped["Step"] = relationship("Step", foreign_keys=[step_id])

    def __repr__(self) -> str:
        return f"<ToolApproval {self.tool_name}:{self.tool_call_id} ({self.status})>"

    @property
    def is_terminal(self) -> bool:
        """Check if the approval is in a terminal state."""
        return self.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.TIMEOUT,
        )

    @property
    def is_pending(self) -> bool:
        """Check if the approval is still pending."""
        return self.status == ApprovalStatus.PENDING

    @property
    def is_expired(self) -> bool:
        """Check if the approval has timed out."""
        if self.is_terminal:
            return False
        now = datetime.now(UTC)
        timeout = self.timeout_at
        # Handle both naive and aware datetimes
        if timeout.tzinfo is None:
            timeout = timeout.replace(tzinfo=UTC)
        return now > timeout

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "run_id": str(self.run_id),
            "step_id": str(self.step_id),
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "tool_arguments": self.tool_arguments,
            "status": self.status.value,
            "requested_at": self.requested_at.isoformat(),
            "timeout_at": self.timeout_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "rejection_reason": self.rejection_reason,
            "modified_arguments": self.modified_arguments,
            "created_at": self.created_at.isoformat(),
        }
