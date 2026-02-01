"""Health check endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from flowforge_server.db import get_session
from flowforge_server.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database: str
    redis: str


class ReadyResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    checks: dict[str, bool]


class DetailedHealthResponse(BaseModel):
    """Detailed health check response with latencies."""

    status: str
    version: str
    checks: dict[str, dict]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    from flowforge_server import __version__

    return HealthResponse(
        status="healthy",
        version=__version__,
        database="unknown",
        redis="unknown",
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(
    session: AsyncSession = Depends(get_session),
) -> ReadyResponse:
    """
    Readiness check endpoint.

    Verifies that all required services are available.
    """
    settings = get_settings()
    checks = {
        "database": False,
        "redis": False,
    }

    # Check database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    # Check Redis
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await redis_client.ping()
        await redis_client.aclose()
        checks["redis"] = True
    except Exception:
        pass

    ready = all(checks.values())

    return ReadyResponse(ready=ready, checks=checks)


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    session: AsyncSession = Depends(get_session),
) -> DetailedHealthResponse:
    """
    Detailed health check with latency measurements.

    Use this endpoint for monitoring and alerting.
    """
    import time
    from flowforge_server import __version__

    settings = get_settings()
    checks = {}

    # Check database with latency
    db_start = time.time()
    try:
        await session.execute(text("SELECT 1"))
        db_latency = (time.time() - db_start) * 1000  # ms
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round(db_latency, 2),
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Check Redis with latency
    redis_start = time.time()
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await redis_client.ping()
        redis_latency = (time.time() - redis_start) * 1000  # ms
        await redis_client.aclose()
        checks["redis"] = {
            "status": "healthy",
            "latency_ms": round(redis_latency, 2),
        }
    except Exception as e:
        checks["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Determine overall status
    all_healthy = all(c.get("status") == "healthy" for c in checks.values())
    overall_status = "healthy" if all_healthy else "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        version=__version__,
        checks=checks,
    )
