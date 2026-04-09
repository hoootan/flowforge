"""Agent model for first-class agent identity."""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class AgentStatus(str, enum.Enum):
    """Agent availability status."""

    ONLINE = "online"
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class Agent(Base, TimestampMixin):
    """
    First-class agent identity.

    Agents are AI team members that can be assigned tasks,
    appear alongside humans, and track their own run history.
    """

    __tablename__ = "agents"

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_agent_tenant_slug"),
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

    # Display name (e.g., "Code Reviewer", "Deploy Bot")
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # URL-friendly identifier
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Avatar URL (or emoji/initials)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Agent description / bio
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Current status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AgentStatus.OFFLINE.value,
        server_default=AgentStatus.OFFLINE.value,
    )

    # AI model this agent uses by default
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # System prompt / personality
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Capabilities / skills this agent has
    capabilities: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Enabled skill IDs — skills inject instructions at runtime for this agent
    enabled_skills: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Agent configuration (max_iterations, tools, etc.)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Performance stats (cached, updated periodically)
    stats: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Whether the agent is active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="agents")

    def __repr__(self) -> str:
        return f"<Agent {self.name} ({self.status})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response dict."""
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "avatar_url": self.avatar_url,
            "description": self.description,
            "status": self.status,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "capabilities": self.capabilities,
            "config": self.config,
            "stats": self.stats,
            "enabled_skills": self.enabled_skills or [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
