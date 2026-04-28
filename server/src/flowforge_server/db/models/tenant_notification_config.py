"""Per-tenant notification configuration.

One row per tenant. Drives services/notifier.py — when a Run transitions to
FAILED/TIMEOUT (per the boolean toggles below) the notifier reads this row,
posts to Slack / PagerDuty if configured, and enqueues an email digest line
when enabled.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class TenantNotificationConfig(Base, TimestampMixin):
    """Notification preferences for a workspace."""

    __tablename__ = "tenant_notification_config"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Slack
    slack_channel: Mapped[str | None] = mapped_column(Text, nullable=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # PagerDuty (Events API v2)
    pagerduty_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pagerduty_integration_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Email digest (daily summary at 09:00 in tenant timezone)
    email_digest_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Triggers — per-event-type toggles
    notify_on_run_failed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_on_run_timeout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationship
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TenantNotificationConfig tenant={self.tenant_id}>"
