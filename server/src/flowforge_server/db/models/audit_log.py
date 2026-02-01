"""Audit log model for tracking security-sensitive operations."""

from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID, INET
from sqlalchemy.orm import Mapped, mapped_column

from flowforge_server.db.models.base import Base


class AuditAction(str, Enum):
    """Types of auditable actions."""

    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    TWO_FA_ENABLED = "2fa_enabled"
    TWO_FA_DISABLED = "2fa_disabled"

    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_DEACTIVATED = "user_deactivated"
    USER_ROLE_CHANGED = "user_role_changed"

    # API key management
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"

    # Function management
    FUNCTION_CREATED = "function_created"
    FUNCTION_UPDATED = "function_updated"
    FUNCTION_DELETED = "function_deleted"

    # Tool management
    TOOL_CREATED = "tool_created"
    TOOL_UPDATED = "tool_updated"
    TOOL_DELETED = "tool_deleted"

    # AI Provider management
    PROVIDER_CREATED = "provider_created"
    PROVIDER_UPDATED = "provider_updated"
    PROVIDER_DELETED = "provider_deleted"

    # Security events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ACCOUNT_LOCKED = "account_locked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditLog(Base):
    """
    Audit log entry for security and compliance tracking.

    Records who did what, when, and from where.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # When the action occurred
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # Tenant context
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Who performed the action (user ID or API key ID)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Actor type: "user", "api_key", "system"
    actor_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
    )

    # Actor identifier for display (email, key prefix, etc.)
    actor_display: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # What action was performed
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Target resource type (user, function, api_key, etc.)
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Target resource ID
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Resource identifier for display
    resource_display: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Additional context/details
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Request metadata
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Correlation ID for request tracing
    correlation_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    # Success/failure
    success: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    # Error message if failed
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.actor_display} at {self.timestamp}>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": str(self.tenant_id),
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "actor_type": self.actor_type,
            "actor_display": self.actor_display,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "resource_display": self.resource_display,
            "details": self.details,
            "ip_address": self.ip_address,
            "correlation_id": self.correlation_id,
            "success": self.success,
            "error_message": self.error_message,
        }
