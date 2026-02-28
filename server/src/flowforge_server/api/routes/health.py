"""Health check endpoints."""

from fastapi import APIRouter, Response
from pydantic import BaseModel

from flowforge_server.observability import HealthChecker

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


class ReadyResponse(BaseModel):
    ready: bool
    checks: dict[str, bool]


class DetailedHealthResponse(BaseModel):
    status: str
    version: str
    checks: dict[str, dict]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — confirms the process is running."""
    from flowforge_server import __version__

    return HealthResponse(status="healthy", version=__version__)


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(response: Response) -> ReadyResponse:
    """Readiness probe — verifies all dependencies are reachable.

    Returns 503 if any critical dependency (database, Redis, queue) is down.
    Suitable for Kubernetes readinessProbe.
    """
    health = await HealthChecker().check_all()

    if not health.healthy:
        response.status_code = 503

    return ReadyResponse(
        ready=health.healthy,
        checks={c.name: c.healthy for c in health.components},
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(response: Response) -> DetailedHealthResponse:
    """Detailed health check with per-component latency measurements.

    Use this endpoint for monitoring dashboards and alerting.
    Returns 503 if any component is unhealthy.
    """
    from flowforge_server import __version__

    health = await HealthChecker().check_all()

    if not health.healthy:
        response.status_code = 503

    return DetailedHealthResponse(
        status=health.status.value,
        version=__version__,
        checks={c.name: c.to_dict() for c in health.components},
    )
