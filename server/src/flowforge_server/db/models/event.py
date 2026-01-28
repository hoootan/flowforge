"""Event model for received events."""

from datetime import datetime
from typing import Any, TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class Event(Base, TimestampMixin):
    """
    Received event that triggers function runs.

    Events are the primary mechanism for triggering FlowForge functions.
    They are persisted for audit, replay, and debugging purposes.
    """

    __tablename__ = "events"

    __table_args__ = (
        UniqueConstraint("tenant_id", "event_id", name="uq_event_tenant_event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Client-provided event ID (for idempotency)
    event_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Event type name (e.g., "order/created")
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Event payload
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # When the event occurred (client timestamp)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # When the event was received by the server
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Optional user ID from the client
    user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Processing status
    processed: Mapped[bool] = mapped_column(default=False)

    # Relationship
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="events")

    def __repr__(self) -> str:
        return f"<Event {self.name} ({self.event_id})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for SDK consumption."""
        return {
            "id": self.event_id,
            "name": self.name,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
        }
