"""Pydantic schemas for tenant notification settings."""

from pydantic import BaseModel, Field


class NotificationSettings(BaseModel):
    """Workspace-level notification preferences."""

    slack_channel: str | None = Field(default=None, max_length=200)
    slack_webhook_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Slack incoming-webhook URL. Required for Slack notifications.",
    )

    pagerduty_enabled: bool = False
    pagerduty_integration_key: str | None = Field(default=None, max_length=200)

    email_digest_enabled: bool = False

    notify_on_run_failed: bool = True
    notify_on_run_timeout: bool = True


class NotificationSettingsUpdate(BaseModel):
    """Partial update for notification settings."""

    slack_channel: str | None = Field(default=None, max_length=200)
    slack_webhook_url: str | None = Field(default=None, max_length=2048)

    pagerduty_enabled: bool | None = None
    pagerduty_integration_key: str | None = Field(default=None, max_length=200)

    email_digest_enabled: bool | None = None

    notify_on_run_failed: bool | None = None
    notify_on_run_timeout: bool | None = None


class NotificationTestRequest(BaseModel):
    """Body for POST /tenant/notifications/test."""

    channel: str = Field(
        description="Which channel to test: 'slack' or 'pagerduty'.",
        pattern="^(slack|pagerduty)$",
    )


class NotificationTestResponse(BaseModel):
    """Result of a test send."""

    ok: bool
    channel: str
    message: str
