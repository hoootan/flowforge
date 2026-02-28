"""Observability layer for FlowForge.

High-level health aggregation on top of the low-level telemetry instrumentation.
Provides deep health checks that go beyond the simple liveness probe — verifying
that all critical dependencies (database, Redis, queue) are actually reachable and
responsive, suitable for Kubernetes readiness probes and dashboards.

Usage:
    from flowforge_server.observability import HealthChecker

    checker = HealthChecker()
    health = await checker.check_all()
    if not health.healthy:
        return JSONResponse(status_code=503, content=health.to_dict())
"""

from flowforge_server.observability.health import (
    ComponentHealth,
    SystemHealth,
    HealthChecker,
    HealthStatus,
)

__all__ = [
    "ComponentHealth",
    "SystemHealth",
    "HealthChecker",
    "HealthStatus",
]
