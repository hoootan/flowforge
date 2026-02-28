"""Function version model for tracking function changes."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.function import Function
    from flowforge_server.db.models.user import User


class FunctionVersion(Base, TimestampMixin):
    """
    Version history for a function.

    Stores a snapshot of the function configuration at a point in time,
    allowing for rollback and audit of changes.
    """

    __tablename__ = "function_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    function_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("functions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Version number (auto-incremented per function)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # User who created this version
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Reason for the change (optional)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # =========================================================================
    # Snapshot of function configuration
    # =========================================================================

    # Human-readable name
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Trigger configuration
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_value: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_expression: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Endpoint URL
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Inline execution configuration
    is_inline: Mapped[bool] = mapped_column(default=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_config: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    agent_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Function configuration
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # =========================================================================
    # Relationships
    # =========================================================================

    function: Mapped["Function"] = relationship(
        "Function",
        back_populates="versions",
    )

    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )

    def __repr__(self) -> str:
        return f"<FunctionVersion {self.function_id}@v{self.version}>"

    def to_dict(self) -> dict[str, Any]:
        """Convert version to dictionary for API responses."""
        return {
            "id": str(self.id),
            "function_id": str(self.function_id),
            "version": self.version,
            "created_by_id": str(self.created_by_id) if self.created_by_id else None,
            "change_reason": self.change_reason,
            "name": self.name,
            "trigger_type": self.trigger_type,
            "trigger_value": self.trigger_value,
            "trigger_expression": self.trigger_expression,
            "endpoint_url": self.endpoint_url,
            "is_inline": self.is_inline,
            "system_prompt": self.system_prompt,
            "tools_config": self.tools_config,
            "agent_config": self.agent_config,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
