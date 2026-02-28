"""User model for dashboard authentication."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class UserRole(str, Enum):
    """User role for access control."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class User(Base, TimestampMixin):
    """
    User for dashboard authentication.

    Users are separate from API keys - they authenticate via email/password
    to access the dashboard and manage the platform.
    """

    __tablename__ = "users"

    # Constraints and indexes
    __table_args__ = (
        # Email must be unique within a tenant
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        # For listing users by tenant, filtered by active status
        Index("ix_users_tenant_active", "tenant_id", "is_active"),
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

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.MEMBER.value,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Two-Factor Authentication fields
    totp_secret: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted TOTP secret for 2FA",
    )

    totp_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether 2FA is enabled for this user",
    )

    backup_codes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(64)),
        nullable=True,
        comment="Encrypted backup codes for 2FA recovery",
    )

    # Relationship to tenant
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"

    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN.value

    @property
    def is_member(self) -> bool:
        """Check if user is a member."""
        return self.role == UserRole.MEMBER.value

    @property
    def is_viewer(self) -> bool:
        """Check if user is a viewer."""
        return self.role == UserRole.VIEWER.value

    @property
    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.is_admin

    @property
    def can_create_resources(self) -> bool:
        """Check if user can create functions, tools, etc."""
        return self.role in (UserRole.ADMIN.value, UserRole.MEMBER.value)

    @property
    def initials(self) -> str:
        """Get user initials for avatar."""
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper() if self.name else "??"
