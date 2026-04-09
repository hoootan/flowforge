"""Notification model for inbox system."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.user import User


class Notification(Base, TimestampMixin):
    """
    Notification for the user inbox.

    Tracks approvals, task assignments, agent completions, mentions, etc.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Recipient
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification type
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    # Types: "approval_required", "task_assigned", "task_completed",
    #        "mention", "agent_blocked", "run_failed", "comment"

    # Title and body
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Link to related entity
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Extra data
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Read/archived state
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} for {self.user_id}>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response dict."""
        return {
            "id": str(self.id),
            "notification_type": self.notification_type,
            "title": self.title,
            "body": self.body,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "data": self.data,
            "is_read": self.is_read,
            "is_archived": self.is_archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
