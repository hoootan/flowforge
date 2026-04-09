"""Skill template model for reusable function+tool configurations."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class SkillTemplate(Base, TimestampMixin):
    """
    Reusable skill template.

    Captures a function + tools configuration as a shareable,
    versionable template that grows the workspace skill library.
    """

    __tablename__ = "skill_templates"

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_skill_tenant_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Display name
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # URL-friendly slug
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Description of what this skill does
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Category (e.g., "deployment", "code-review", "data-analysis")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Icon/emoji for visual identification
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Version
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Function configuration snapshot
    function_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # Contains: system_prompt, model, agent_config, trigger_type, etc.

    # Tools configuration snapshot
    tools_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    # Contains: list of tool schemas with code, parameters, etc.

    # Usage count
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Whether this is a built-in/global template
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Tags for discovery
    tags: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Source: "local", "skills_sh", "github"
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="local", server_default="local", index=True,
    )

    # Raw SKILL.md markdown body — knowledge payload for imported skills
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance tracking for imported skills
    # {"repo": "owner/repo", "path": "SKILL.md", "commit_sha": "...", "fetched_at": "...", "external_id": "...", "install_count": 1234}
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Created by
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant | None"] = relationship("Tenant", back_populates="skill_templates")

    def __repr__(self) -> str:
        return f"<SkillTemplate {self.name} v{self.version}>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response dict."""
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "version": self.version,
            "function_config": self.function_config,
            "tools_config": self.tools_config,
            "usage_count": self.usage_count,
            "is_builtin": self.is_builtin,
            "is_active": self.is_active,
            "tags": self.tags,
            "source": self.source,
            "instructions": self.instructions,
            "source_metadata": self.source_metadata,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
