"""Health check endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db import get_session

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

    # Check Redis (TODO: implement when Redis is integrated)
    checks["redis"] = True  # Placeholder

    ready = all(checks.values())

    return ReadyResponse(ready=ready, checks=checks)
