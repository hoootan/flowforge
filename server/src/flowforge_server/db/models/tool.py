"""Tool model for reusable AI tools."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class Tool(Base, TimestampMixin):
    """
    Reusable tool that can be used by agent-based functions.

    Tools can be:
    - Built-in: Shipped with FlowForge (tenant_id is None)
    - Custom: Created by users for their tenant
    """

    __tablename__ = "tools"

    __table_args__ = (
        # Tool name must be unique per tenant (or globally for built-in)
        UniqueConstraint("tenant_id", "name", name="uq_tool_tenant_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Tenant ID (None for built-in tools)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Tool name (e.g., "web_search", "generate_image")
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Human-readable description (shown to LLM)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # JSON Schema for parameters
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Tool type: "custom" (code-based), "webhook" (HTTP config), "builtin"
    tool_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="custom", server_default="custom"
    )

    # Python code for custom tools (None for built-in tools)
    # Format: async def execute(**kwargs) -> dict: ...
    code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Webhook configuration (for tool_type="webhook")
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_method: Mapped[str] = mapped_column(
        String(10), nullable=False, default="POST", server_default="POST"
    )
    webhook_headers: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    # Whether this is a built-in tool
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Whether this tool requires human approval before execution
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timeout for approval (e.g., "1h", "30m")
    approval_timeout: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Whether the tool is active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Soft-delete marker. NULL = visible; timestamp = hidden from user-facing
    # endpoints. Runs already executing keep loading the tool via its is_active
    # filter; deleting also sets is_active=False so new runs stop loading it.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationships
    tenant: Mapped["Tenant | None"] = relationship("Tenant", back_populates="tools")

    def __repr__(self) -> str:
        return f"<Tool {self.name}>"

    def to_schema(self) -> dict[str, Any]:
        """Convert to OpenAI/Anthropic tool schema format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
