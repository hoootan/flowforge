"""Configuration classes for FlowForge functions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Concurrency:
    """
    Concurrency configuration for a function.

    Limits how many instances of a function can run simultaneously.
    """

    limit: int
    """Maximum number of concurrent executions."""

    key: str | None = None
    """
    Optional key expression for per-key concurrency limiting.
    Example: "event.data.user_id" limits concurrency per user.
    """

    def to_dict(self) -> dict[str, Any]:
        return {"limit": self.limit, "key": self.key}


@dataclass
class RateLimit:
    """
    Rate limiting configuration for a function.

    Limits the rate of function invocations over a time period.
    """

    limit: int
    """Maximum number of invocations."""

    period: str
    """Time period (e.g., "1m", "1h", "1d")."""

    key: str | None = None
    """Optional key expression for per-key rate limiting."""

    def to_dict(self) -> dict[str, Any]:
        return {"limit": self.limit, "period": self.period, "key": self.key}


@dataclass
class Throttle:
    """
    Throttle configuration for a function.

    Ensures a minimum time gap between invocations.
    """

    limit: int
    """Maximum invocations in the period."""

    period: str
    """Time period (e.g., "1s", "1m")."""

    key: str | None = None
    """Optional key expression for per-key throttling."""

    burst: int | None = None
    """Optional burst allowance."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "limit": self.limit,
            "period": self.period,
            "key": self.key,
            "burst": self.burst,
        }


@dataclass
class Debounce:
    """
    Debounce configuration for a function.

    Delays execution until no new events arrive for a period.
    """

    period: str
    """Time to wait for more events before executing."""

    key: str | None = None
    """Optional key expression for per-key debouncing."""

    def to_dict(self) -> dict[str, Any]:
        return {"period": self.period, "key": self.key}


@dataclass
class Priority:
    """
    Priority configuration for a function.

    Controls execution order when jobs are queued.
    """

    run: str | None = None
    """Expression to determine run priority (e.g., "event.data.priority")."""

    def to_dict(self) -> dict[str, Any]:
        return {"run": self.run}


@dataclass
class FunctionConfig:
    """Complete configuration for a FlowForge function."""

    id: str
    """Unique identifier for the function."""

    name: str | None = None
    """Human-readable name (defaults to function name)."""

    retries: int = 3
    """Number of retry attempts on failure."""

    timeout: str = "5m"
    """Maximum execution time (e.g., "5m", "1h")."""

    concurrency: Concurrency | None = None
    """Concurrency limiting configuration."""

    rate_limit: RateLimit | None = None
    """Rate limiting configuration."""

    throttle: Throttle | None = None
    """Throttle configuration."""

    debounce: Debounce | None = None
    """Debounce configuration."""

    priority: Priority | None = None
    """Priority configuration."""

    cancel_on: list[str] = field(default_factory=list)
    """Events that cancel running instances."""

    idempotency_key: str | None = None
    """Expression for idempotency (e.g., "event.data.order_id")."""

    def to_dict(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "retries": self.retries,
            "timeout": self.timeout,
        }

        if self.concurrency:
            config["concurrency"] = self.concurrency.to_dict()
        if self.rate_limit:
            config["rate_limit"] = self.rate_limit.to_dict()
        if self.throttle:
            config["throttle"] = self.throttle.to_dict()
        if self.debounce:
            config["debounce"] = self.debounce.to_dict()
        if self.priority:
            config["priority"] = self.priority.to_dict()
        if self.cancel_on:
            config["cancel_on"] = self.cancel_on
        if self.idempotency_key:
            config["idempotency_key"] = self.idempotency_key

        return config


# Convenience functions for creating configurations
def concurrency(limit: int, key: str | None = None) -> Concurrency:
    """Create a concurrency configuration."""
    return Concurrency(limit=limit, key=key)


def rate_limit(limit: int, period: str, key: str | None = None) -> RateLimit:
    """Create a rate limit configuration."""
    return RateLimit(limit=limit, period=period, key=key)


def throttle(
    limit: int, period: str, key: str | None = None, burst: int | None = None
) -> Throttle:
    """Create a throttle configuration."""
    return Throttle(limit=limit, period=period, key=key, burst=burst)


def debounce(period: str, key: str | None = None) -> Debounce:
    """Create a debounce configuration."""
    return Debounce(period=period, key=key)


def priority(run: str | None = None) -> Priority:
    """Create a priority configuration."""
    return Priority(run=run)
