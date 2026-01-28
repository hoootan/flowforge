"""Function model for registered workflow functions."""

from datetime import datetime
from typing import Any, TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant
    from flowforge_server.db.models.run import Run


class Function(Base, TimestampMixin):
    """
    Registered workflow function.

    Functions are registered by the SDK and define how workflows
    are triggered and configured.
    """

    __tablename__ = "functions"

    __table_args__ = (
        UniqueConstraint("tenant_id", "function_id", name="uq_function_tenant_function_id"),
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

    # User-defined function ID (e.g., "process-order")
    function_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Human-readable name
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # URL-friendly slug
    slug: Mapped[str] = mapped_column(String(255), nullable=False)

    # Trigger type: 'event', 'cron', 'webhook'
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Trigger value: event name, cron expression, or webhook path
    trigger_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional filter expression for event triggers
    trigger_expression: Mapped[str | None] = mapped_column(Text, nullable=True)

    # URL where the function is deployed (optional for inline functions)
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # =========================================================================
    # Serverless/Inline Execution Fields
    # =========================================================================

    # Whether this function executes inline (serverless) vs external worker
    is_inline: Mapped[bool] = mapped_column(default=False)

    # System prompt for agent-based functions
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # List of tool names to use (references Tool.name)
    tools_config: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Agent configuration (model, max_iterations, max_tool_calls, etc.)
    agent_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # =========================================================================

    # Function configuration (retries, timeout, concurrency, etc.)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Whether the function is active
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="functions")

    runs: Mapped[list["Run"]] = relationship(
        "Run",
        back_populates="function",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Function {self.function_id}>"

    @property
    def retries(self) -> int:
        """Get configured retry count."""
        return self.config.get("retries", 3)

    @property
    def timeout(self) -> str:
        """Get configured timeout."""
        return self.config.get("timeout", "5m")

    @property
    def concurrency_limit(self) -> int | None:
        """Get configured concurrency limit."""
        concurrency = self.config.get("concurrency")
        if concurrency:
            return concurrency.get("limit")
        return None
