"""Stats endpoints for dashboard."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import DEFAULT_TENANT_ID
from flowforge_server.db import get_session
from flowforge_server.db.models import Event, Function, Run

router = APIRouter(tags=["stats"])


class RunStats(BaseModel):
    """Run statistics."""

    total: int
    completed: int
    failed: int
    running: int


class FunctionStats(BaseModel):
    """Function statistics."""

    total: int
    active: int


class EventStats(BaseModel):
    """Event statistics."""

    today: int
    total: int


class QueueStats(BaseModel):
    """Queue statistics."""

    pending: int
    running: int
    scheduled: int


class StatsResponse(BaseModel):
    """Stats response."""

    runs: RunStats
    functions: FunctionStats
    events: EventStats
    queue: QueueStats


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_session),
) -> StatsResponse:
    """Get dashboard statistics."""
    tenant_id = DEFAULT_TENANT_ID

    # Run stats
    run_total = await session.scalar(
        select(func.count(Run.id)).where(Run.tenant_id == tenant_id)
    ) or 0

    run_completed = await session.scalar(
        select(func.count(Run.id)).where(
            Run.tenant_id == tenant_id,
            Run.status == "completed",
        )
    ) or 0

    run_failed = await session.scalar(
        select(func.count(Run.id)).where(
            Run.tenant_id == tenant_id,
            Run.status == "failed",
        )
    ) or 0

    run_running = await session.scalar(
        select(func.count(Run.id)).where(
            Run.tenant_id == tenant_id,
            Run.status == "running",
        )
    ) or 0

    # Function stats
    func_total = await session.scalar(
        select(func.count(Function.id)).where(Function.tenant_id == tenant_id)
    ) or 0

    func_active = await session.scalar(
        select(func.count(Function.id)).where(
            Function.tenant_id == tenant_id,
            Function.is_active == True,  # noqa: E712
        )
    ) or 0

    # Event stats
    event_total = await session.scalar(
        select(func.count(Event.id)).where(Event.tenant_id == tenant_id)
    ) or 0

    # Events today
    today_start = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    event_today = await session.scalar(
        select(func.count(Event.id)).where(
            Event.tenant_id == tenant_id,
            Event.created_at >= today_start,
        )
    ) or 0

    # Queue stats (from runs table)
    queue_pending = await session.scalar(
        select(func.count(Run.id)).where(
            Run.tenant_id == tenant_id,
            Run.status == "pending",
        )
    ) or 0

    queue_running = run_running

    queue_scheduled = await session.scalar(
        select(func.count(Run.id)).where(
            Run.tenant_id == tenant_id,
            Run.status == "scheduled",
        )
    ) or 0

    return StatsResponse(
        runs=RunStats(
            total=run_total,
            completed=run_completed,
            failed=run_failed,
            running=run_running,
        ),
        functions=FunctionStats(
            total=func_total,
            active=func_active,
        ),
        events=EventStats(
            today=event_today,
            total=event_total,
        ),
        queue=QueueStats(
            pending=queue_pending,
            running=queue_running,
            scheduled=queue_scheduled,
        ),
    )
