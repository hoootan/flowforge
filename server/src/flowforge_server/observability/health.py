"""Deep health checks for all critical FlowForge dependencies.

Provides component-level health status suitable for Kubernetes readiness probes,
uptime monitors, and the dashboard's system status page.

Unlike the simple liveness probe (which just checks if the process is alive),
these checks actively verify that each dependency can serve requests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from flowforge_server.config import get_settings
from flowforge_server.logging import Loggers


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status for a single system component."""

    name: str
    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2) if self.latency_ms is not None else None,
            "message": self.message,
            **self.details,
        }


@dataclass
class SystemHealth:
    """Aggregated health status across all components."""

    components: list[ComponentHealth] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return all(c.healthy for c in self.components)

    @property
    def status(self) -> HealthStatus:
        if all(c.status == HealthStatus.HEALTHY for c in self.components):
            return HealthStatus.HEALTHY
        if any(c.status == HealthStatus.UNHEALTHY for c in self.components):
            return HealthStatus.UNHEALTHY
        return HealthStatus.DEGRADED

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "healthy": self.healthy,
            "components": [c.to_dict() for c in self.components],
        }


class HealthChecker:
    """Performs deep health checks across all critical dependencies."""

    def __init__(self) -> None:
        self._log = Loggers.api()

    async def check_database(self) -> ComponentHealth:
        """Verify PostgreSQL is reachable and can execute a simple query."""
        start = time.perf_counter()
        try:
            from sqlalchemy import text
            from flowforge_server.db.session import get_session_factory

            factory = get_session_factory()
            async with factory() as session:
                await session.execute(text("SELECT 1"))

            latency_ms = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            self._log.warning("health_check_database_failed", error=str(exc))
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message=str(exc),
            )

    async def check_redis(self) -> ComponentHealth:
        """Verify Redis is reachable and responding to PING."""
        start = time.perf_counter()
        try:
            import redis.asyncio as aioredis

            settings = get_settings()
            client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
            await client.ping()
            await client.aclose()

            latency_ms = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            self._log.warning("health_check_redis_failed", error=str(exc))
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message=str(exc),
            )

    async def check_queue(self) -> ComponentHealth:
        """Verify the job queue is operational and report queue depth."""
        start = time.perf_counter()
        try:
            from flowforge_server.queue import FairQueue

            settings = get_settings()
            queue = FairQueue(redis_url=settings.redis_url)
            stats = await queue.get_stats()
            await queue.close()

            latency_ms = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name="queue",
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
                details={
                    "pending": stats.get("pending", 0),
                    "running": stats.get("running", 0),
                },
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            self._log.warning("health_check_queue_failed", error=str(exc))
            return ComponentHealth(
                name="queue",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message=str(exc),
            )

    async def check_all(self) -> SystemHealth:
        """Run all component checks concurrently and return the aggregate result."""
        import asyncio

        results = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_queue(),
            return_exceptions=False,
        )

        health = SystemHealth(components=list(results))
        self._log.info(
            "health_check_complete",
            status=health.status.value,
            components={c.name: c.status.value for c in health.components},
        )
        return health
