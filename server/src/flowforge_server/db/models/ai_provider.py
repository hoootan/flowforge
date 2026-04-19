"""AI Provider model for secure multi-tenant API key management."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class AIProvider(Base, TimestampMixin):
    """
    AI Provider configuration for multi-tenant credential storage.

    Stores encrypted API keys and configuration for AI providers
    on a per-tenant basis. Keys are encrypted at rest using Fernet.

    Attributes:
        id: Unique identifier
        tenant_id: Associated tenant (for multi-tenancy)
        provider_name: Provider identifier (openai, anthropic, google, etc.)
        display_name: User-friendly name for this configuration
        api_key_encrypted: Fernet-encrypted API key
        api_key_prefix: First 8 chars for display (e.g., "sk-proj-...")
        base_url: Optional custom API endpoint (for self-hosted/proxied)
        is_active: Whether this provider is currently enabled
        is_default: Whether this is the default provider for the tenant
        config: Additional configuration (model preferences, rate limits, etc.)
    """

    __tablename__ = "ai_providers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Tenant association
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider identification
    provider_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # openai, anthropic, google, mistral, cohere, custom

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )  # User-friendly name like "Production OpenAI"

    # Encrypted credentials
    api_key_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )  # Fernet-encrypted API key

    api_key_prefix: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # First 8 chars + "..." for display

    # Authentication type
    auth_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="api_key",
    )  # "api_key" or "oauth_token"

    # Optional custom endpoint
    base_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # For custom/self-hosted providers or proxies

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )  # Default provider within this provider_name for the tenant (only disambiguates between multiple keys of the same provider type; does not route across providers).

    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )  # Most recent successful use by the AI service

    # Additional configuration
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )  # Model preferences, rate limits, fallback settings, etc.

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="ai_providers",
        lazy="selectin",
    )

    # Constraints and indexes
    __table_args__ = (
        # Index for finding default provider
        Index("ix_ai_provider_tenant_default", "tenant_id", "is_default"),
        # Index for finding active providers
        Index("ix_ai_provider_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<AIProvider {self.provider_name} ({self.display_name})>"

    @property
    def masked_key(self) -> str:
        """Get the masked API key for display."""
        return self.api_key_prefix

    def to_dict(self, include_encrypted: bool = False) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Args:
            include_encrypted: If True, include the encrypted key (NOT the decrypted key)
        """
        result = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "provider_name": self.provider_name,
            "display_name": self.display_name,
            "api_key_prefix": self.api_key_prefix,
            "auth_type": self.auth_type,
            "base_url": self.base_url,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "config": self.config,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_encrypted:
            result["api_key_encrypted"] = self.api_key_encrypted

        return result
