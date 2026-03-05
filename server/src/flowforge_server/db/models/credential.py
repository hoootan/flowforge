"""Credential model for secure storage of service credentials."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class Credential(Base, TimestampMixin):
    """
    Encrypted credential storage for tenant service integrations.

    Stores API keys, tokens, and other secrets that can be referenced
    in tool configurations via {{credential:name}} placeholders.

    Attributes:
        id: Unique identifier
        tenant_id: Associated tenant
        name: Unique name per tenant (e.g., "supabase_key")
        credential_type: Type of credential (api_key, bearer_token, basic_auth, custom)
        encrypted_value: Fernet-encrypted secret value
        value_prefix: First 8 chars for masked display
        description: Optional description
        is_active: Whether this credential is active
    """

    __tablename__ = "credentials"

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_credential_tenant_name"),
        Index("ix_credential_tenant_active", "tenant_id", "is_active"),
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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    credential_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="api_key",
    )  # api_key, bearer_token, basic_auth, custom

    encrypted_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    value_prefix: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # First 8 chars + "..." for display

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="credentials",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Credential {self.name} ({self.credential_type})>"

    @property
    def masked_value(self) -> str:
        """Get the masked value for display."""
        return self.value_prefix

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (never includes decrypted value)."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "credential_type": self.credential_type,
            "value_prefix": self.value_prefix,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
