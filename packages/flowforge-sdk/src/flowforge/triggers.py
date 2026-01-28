"""Trigger definitions for FlowForge functions."""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class Trigger:
    """Base trigger configuration for FlowForge functions."""

    type: Literal["event", "cron", "webhook"]
    """Type of trigger."""

    value: str
    """Trigger value (event name, cron expression, or webhook path)."""

    expression: str | None = None
    """Optional filter expression for event triggers."""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": self.type,
            "value": self.value,
        }
        if self.expression:
            result["expression"] = self.expression
        return result


class TriggerBuilder:
    """Builder for creating trigger configurations."""

    def event(self, name: str, expression: str | None = None) -> Trigger:
        """
        Create an event-based trigger.

        Args:
            name: The event name to trigger on (e.g., "order/created").
            expression: Optional filter expression to match specific events.
                       Example: "event.data.amount > 100"

        Returns:
            Trigger configuration for the event.

        Example:
            @flowforge.function(
                trigger=flowforge.trigger.event("order/created")
            )
            async def process_order(ctx: Context):
                ...

            # With filter expression
            @flowforge.function(
                trigger=flowforge.trigger.event(
                    "order/created",
                    expression="event.data.total > 1000"
                )
            )
            async def process_large_order(ctx: Context):
                ...
        """
        return Trigger(type="event", value=name, expression=expression)

    def cron(self, expression: str) -> Trigger:
        """
        Create a cron-based trigger.

        Args:
            expression: Cron expression (e.g., "0 9 * * *" for 9 AM daily).
                       Supports standard 5-field cron syntax:
                       minute hour day-of-month month day-of-week

        Returns:
            Trigger configuration for the cron schedule.

        Example:
            @flowforge.function(
                trigger=flowforge.trigger.cron("0 9 * * *")  # 9 AM daily
            )
            async def daily_report(ctx: Context):
                ...

            @flowforge.function(
                trigger=flowforge.trigger.cron("*/15 * * * *")  # Every 15 minutes
            )
            async def check_status(ctx: Context):
                ...
        """
        return Trigger(type="cron", value=expression)

    def webhook(self, path: str | None = None) -> Trigger:
        """
        Create a webhook-based trigger.

        Args:
            path: Optional custom path for the webhook endpoint.
                  If not provided, uses the function ID.

        Returns:
            Trigger configuration for the webhook.

        Example:
            @flowforge.function(
                trigger=flowforge.trigger.webhook("/stripe/webhook")
            )
            async def handle_stripe_webhook(ctx: Context):
                ...
        """
        return Trigger(type="webhook", value=path or "")


# Global trigger builder instance
trigger = TriggerBuilder()
