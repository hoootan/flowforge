"""API Key model for enhanced authentication."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class ApiKeyType(str, Enum):
    """API key type/environment."""

    LIVE = "live"
    TEST = "test"
    READ_ONLY = "ro"


class ApiKey(Base, TimestampMixin):
    """
    API Key for tenant authentication.

    Supports multiple keys per tenant with different scopes and environments.
    Key format: ff_{type}_{random} (e.g., ff_live_a1b2c3d4e5f6...)
    """

    __tablename__ = "api_keys"

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

    # Human-readable name for the key
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # SHA-256 hash of the full API key
    key_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)

    # First 12 chars of the key for identification (e.g., "ff_live_a1b2")
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)

    # Key type: live, test, or ro (read-only)
    key_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ApiKeyType.TEST.value,
    )

    # Scopes/permissions for this key
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    # Optional expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Soft delete / revocation
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Revocation info
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship to tenant
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="api_keys",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ApiKey {self.key_prefix}... ({self.name})>"

    @property
    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(self.expires_at.tzinfo) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the key is currently valid (active and not expired)."""
        return self.is_active and not self.is_expired


# Default scopes by key type
DEFAULT_SCOPES = {
    ApiKeyType.LIVE: [
        "events:send",
        "events:read",
        "runs:read",
        "runs:manage",
        "functions:read",
        "functions:manage",
        "tools:read",
        "tools:manage",
        "approvals:read",
        "approvals:manage",
    ],
    ApiKeyType.TEST: [
        "events:send",
        "events:read",
        "runs:read",
        "runs:manage",
        "functions:read",
        "functions:manage",
        "tools:read",
        "tools:manage",
        "approvals:read",
        "approvals:manage",
    ],
    ApiKeyType.READ_ONLY: [
        "events:read",
        "runs:read",
        "functions:read",
        "tools:read",
        "approvals:read",
    ],
}

# All available scopes
ALL_SCOPES = [
    "events:send",
    "events:read",
    "runs:read",
    "runs:manage",
    "functions:read",
    "functions:manage",
    "tools:read",
    "tools:manage",
    "approvals:read",
    "approvals:manage",
    "admin",  # Full access - implies all other scopes
]
