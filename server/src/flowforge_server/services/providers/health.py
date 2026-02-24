"""Provider health checking.

Monitors the health status of AI providers and tracks rate limits.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from . import ProviderRegistry


@dataclass
class HealthStatus:
    """Health status of a provider."""

    provider: str
    status: Literal["healthy", "degraded", "unhealthy", "unknown"] = "unknown"
    last_check: datetime | None = None
    latency_ms: float | None = None
    error: str | None = None
    rate_limited: bool = False
    rate_limit_reset: datetime | None = None
    consecutive_failures: int = 0
    last_success: datetime | None = None

    def is_healthy(self) -> bool:
        """Check if provider is considered healthy."""
        if self.rate_limited:
            if self.rate_limit_reset and datetime.utcnow() < self.rate_limit_reset:
                return False
        return self.status in ("healthy", "degraded", "unknown")


@dataclass
class HealthMetrics:
    """Aggregated health metrics for a provider."""

    provider: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    uptime_pct: float = 100.0
    latencies: list[float] = field(default_factory=list)

    def record_request(
        self,
        success: bool,
        latency_ms: float,
        rate_limited: bool = False,
    ) -> None:
        """Record a request result."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        if rate_limited:
            self.rate_limited_requests += 1

        # Track latency (keep last 100 for percentile calc)
        self.latencies.append(latency_ms)
        if len(self.latencies) > 100:
            self.latencies.pop(0)

        # Update averages
        self.avg_latency_ms = sum(self.latencies) / len(self.latencies)
        sorted_latencies = sorted(self.latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        self.p95_latency_ms = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]

        # Update uptime
        if self.total_requests > 0:
            self.uptime_pct = (self.successful_requests / self.total_requests) * 100


class HealthChecker:
    """
    Background health checker for providers.

    Periodically pings providers and tracks their status.
    Integrates with the ProviderRegistry for health-aware routing.
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        check_interval_seconds: float = 60.0,
        failure_threshold: int = 3,
        recovery_threshold: int = 2,
    ) -> None:
        """
        Initialize the health checker.

        Args:
            registry: Provider registry to check
            check_interval_seconds: Interval between health checks
            failure_threshold: Consecutive failures to mark unhealthy
            recovery_threshold: Consecutive successes to mark healthy
        """
        self.registry = registry
        self.check_interval = check_interval_seconds
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold

        self._status: dict[str, HealthStatus] = {}
        self._metrics: dict[str, HealthMetrics] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._consecutive_successes: dict[str, int] = {}

    async def start(self) -> None:
        """Start background health checking."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._check_loop())

    async def stop(self) -> None:
        """Stop background health checking."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _check_loop(self) -> None:
        """Background loop for periodic health checks."""
        while self._running:
            try:
                await self.check_all()
            except Exception:
                pass  # Don't crash the loop
            await asyncio.sleep(self.check_interval)

    async def check_all(self) -> dict[str, HealthStatus]:
        """Check health of all configured providers."""
        if not self.registry:
            return {}

        providers = self.registry.list_providers()
        tasks = [self.check_provider(p) for p in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            p: r if isinstance(r, HealthStatus) else HealthStatus(provider=p, status="unknown", error=str(r))
            for p, r in zip(providers, results)
        }

    async def check_provider(self, provider: str) -> HealthStatus:
        """
        Check a single provider's health.

        Performs a minimal API call to verify connectivity.

        Args:
            provider: Provider name to check

        Returns:
            HealthStatus for the provider
        """
        start_time = time.time()
        status = self._status.get(provider, HealthStatus(provider=provider))

        try:
            # Import litellm for health check
            import litellm

            # Get a simple model for this provider
            test_model = self._get_test_model(provider)
            if not test_model:
                status.status = "unknown"
                status.error = f"No test model configured for {provider}"
                status.last_check = datetime.utcnow()
                self._status[provider] = status
                return status

            # Minimal completion call
            await litellm.acompletion(
                model=test_model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
                timeout=10.0,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Success
            status.latency_ms = latency_ms
            status.error = None
            status.last_check = datetime.utcnow()
            status.last_success = datetime.utcnow()
            status.consecutive_failures = 0
            self._consecutive_successes[provider] = self._consecutive_successes.get(provider, 0) + 1

            # Update status based on recovery threshold
            if self._consecutive_successes.get(provider, 0) >= self.recovery_threshold:
                status.status = "healthy"
            elif status.status == "unhealthy":
                status.status = "degraded"

            # Record metrics
            self._ensure_metrics(provider).record_request(True, latency_ms)

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_str = str(e).lower()

            status.latency_ms = latency_ms
            status.error = str(e)
            status.last_check = datetime.utcnow()
            status.consecutive_failures += 1
            self._consecutive_successes[provider] = 0

            # Check for rate limiting
            if "rate" in error_str or "429" in error_str or "quota" in error_str:
                status.rate_limited = True
                # Estimate reset time (default 60 seconds)
                status.rate_limit_reset = datetime.utcnow() + timedelta(seconds=60)
                self._ensure_metrics(provider).record_request(False, latency_ms, rate_limited=True)
            else:
                status.rate_limited = False
                self._ensure_metrics(provider).record_request(False, latency_ms)

            # Update status based on failure threshold
            if status.consecutive_failures >= self.failure_threshold:
                status.status = "unhealthy"
            elif status.status == "healthy":
                status.status = "degraded"

        self._status[provider] = status
        return status

    def get_status(self, provider: str) -> HealthStatus:
        """Get cached health status for a provider."""
        return self._status.get(provider, HealthStatus(provider=provider))

    def get_metrics(self, provider: str) -> HealthMetrics:
        """Get metrics for a provider."""
        return self._ensure_metrics(provider)

    def is_healthy(self, provider: str) -> bool:
        """Quick check if provider is healthy."""
        status = self._status.get(provider)
        if not status:
            return True  # Assume healthy if unknown
        return status.is_healthy()

    def mark_rate_limited(
        self,
        provider: str,
        reset_after_seconds: float = 60.0,
    ) -> None:
        """
        Mark a provider as rate limited.

        Called when a rate limit error is received during normal operation.

        Args:
            provider: Provider name
            reset_after_seconds: Seconds until rate limit resets
        """
        status = self._status.get(provider, HealthStatus(provider=provider))
        status.rate_limited = True
        status.rate_limit_reset = datetime.utcnow() + timedelta(seconds=reset_after_seconds)
        status.status = "degraded" if status.status == "healthy" else status.status
        self._status[provider] = status

    def mark_error(self, provider: str, error: str) -> None:
        """
        Mark a provider error from normal operation.

        Args:
            provider: Provider name
            error: Error message
        """
        status = self._status.get(provider, HealthStatus(provider=provider))
        status.consecutive_failures += 1
        status.error = error
        self._consecutive_successes[provider] = 0

        if status.consecutive_failures >= self.failure_threshold:
            status.status = "unhealthy"
        elif status.status == "healthy":
            status.status = "degraded"

        self._status[provider] = status

    def mark_success(self, provider: str, latency_ms: float) -> None:
        """
        Mark a successful request.

        Args:
            provider: Provider name
            latency_ms: Request latency
        """
        status = self._status.get(provider, HealthStatus(provider=provider))
        status.consecutive_failures = 0
        status.last_success = datetime.utcnow()
        status.latency_ms = latency_ms
        self._consecutive_successes[provider] = self._consecutive_successes.get(provider, 0) + 1

        if self._consecutive_successes.get(provider, 0) >= self.recovery_threshold:
            status.status = "healthy"
            status.rate_limited = False

        self._status[provider] = status
        self._ensure_metrics(provider).record_request(True, latency_ms)

    def _get_test_model(self, provider: str) -> str | None:
        """Get a minimal test model for a provider."""
        test_models = {
            "openai": "gpt-5.2",
            "anthropic": "claude-haiku-4-5-20251001",
            "google": "gemini-3-flash",
            "mistral": "mistral-small-latest",
            "cohere": "command-light",
        }
        return test_models.get(provider)

    def _ensure_metrics(self, provider: str) -> HealthMetrics:
        """Get or create metrics for a provider."""
        if provider not in self._metrics:
            self._metrics[provider] = HealthMetrics(provider=provider)
        return self._metrics[provider]

    def get_all_status(self) -> dict[str, HealthStatus]:
        """Get health status for all tracked providers."""
        return dict(self._status)

    def get_all_metrics(self) -> dict[str, HealthMetrics]:
        """Get metrics for all tracked providers."""
        return dict(self._metrics)
