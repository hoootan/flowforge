"""Run management endpoints."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.api.schemas.approvals import (
    ToolCallResponse,
    ToolCallsResponse,
)
from flowforge_server.api.schemas.runs import (
    RunActionResponse,
    RunResponse,
    RunsResponse,
    StepResponse,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import Function, Run, RunStatus, Step, StepStatus
from flowforge_server.queue import FairQueue, Job

router = APIRouter(prefix="/runs", tags=["runs"])


def run_to_response(run: Run) -> RunResponse:
    """Convert Run model to response schema."""
    return RunResponse(
        id=str(run.id),
        function_id=str(run.function_id),
        event_id=str(run.event_id) if run.event_id else None,
        status=run.status.value if isinstance(run.status, RunStatus) else run.status,
        trigger_type=run.trigger_type,
        trigger_data=run.trigger_data,
        attempt=run.attempt,
        max_attempts=run.max_attempts,
        output=run.output,
        error=run.error,
        started_at=run.started_at,
        ended_at=run.ended_at,
        created_at=run.created_at,
        steps=[
            StepResponse(
                id=str(step.id),
                step_id=step.step_id,
                step_type=step.step_type.value if hasattr(step.step_type, 'value') else step.step_type,
                status=step.status.value if hasattr(step.status, 'value') else step.status,
                input=step.input,
                output=step.output,
                error=step.error,
                attempt=step.attempt,
                max_attempts=step.max_attempts,
                tool_name=step.tool_name,
                tool_call_id=step.tool_call_id,
                tool_input=step.tool_input,
                tool_output=step.tool_output,
                agent_state=step.agent_state,
                started_at=step.started_at,
                ended_at=step.ended_at,
                created_at=step.created_at,
            )
            for step in (run.steps if "steps" in run.__dict__ else [])
        ],
    )


@router.get("", response_model=RunsResponse)
async def list_runs(
    tenant: TenantWithDevFallback,
    function_id: str | None = Query(None, description="Filter by function ID"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> RunsResponse:
    """List runs with optional filtering."""
    filters = [Run.tenant_id == tenant.id]

    if function_id:
        fn_result = await session.execute(
            select(Function.id).where(
                Function.tenant_id == tenant.id,
                Function.function_id == function_id,
            )
        )
        fn_uuid = fn_result.scalar_one_or_none()
        if fn_uuid:
            filters.append(Run.function_id == fn_uuid)

    if status:
        filters.append(Run.status == status)

    # Single count query respecting all filters
    total = (await session.execute(
        select(func.count()).select_from(select(Run.id).where(*filters).subquery())
    )).scalar() or 0

    # Fetch runs without steps — steps are heavy and not needed for the list view
    result = await session.execute(
        select(Run)
        .where(*filters)
        .order_by(Run.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    runs = result.scalars().unique().all()

    return RunsResponse(
        runs=[run_to_response(run) for run in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> RunResponse:
    """Get a specific run by ID."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    result = await session.execute(
        select(Run)
        .where(
            Run.tenant_id == tenant.id,
            Run.id == run_uuid,
        )
        .options(selectinload(Run.steps))
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return run_to_response(run)


@router.post("/{run_id}/cancel", response_model=RunActionResponse)
async def cancel_run(
    run_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> RunActionResponse:
    """Cancel a running or pending run."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    result = await session.execute(
        select(Run).where(
            Run.tenant_id == tenant.id,
            Run.id == run_uuid,
        )
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.is_terminal:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel run with status '{run.status}'",
        )

    run.status = RunStatus.CANCELLED
    run.ended_at = datetime.utcnow()

    await session.commit()

    return RunActionResponse(
        success=True,
        message="Run cancelled successfully",
        run_id=run_id,
    )


@router.post("/{run_id}/retry", response_model=RunActionResponse)
async def retry_run(
    run_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> RunActionResponse:
    """
    Retry a failed run in-place, preserving all completed steps.

    Unlike /replay (which starts a fresh run), this keeps all memoized
    step results so execution resumes from the point of failure rather
    than from the beginning.
    """
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    result = await session.execute(
        select(Run)
        .where(Run.tenant_id == tenant.id, Run.id == run_uuid)
        .options(selectinload(Run.steps))
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in (RunStatus.FAILED, RunStatus.RUNNING, RunStatus.PENDING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry run with status '{run.status.value}'",
        )

    # Fetch the function to build the job payload
    fn_result = await session.execute(
        select(Function).where(Function.id == run.function_id)
    )
    fn = fn_result.scalar_one_or_none()
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")

    # Delete failed/errored steps so they re-execute on the next attempt.
    # Completed steps stay intact — the SDK will replay them from cache.
    for step in list(run.steps):
        if step.status in (StepStatus.FAILED,):
            await session.delete(step)

    # Reset run so the executor picks it up again
    run.status = RunStatus.PENDING
    run.attempt = 1
    run.error = None
    run.ended_at = None

    await session.commit()

    # Enqueue a job so the executor actually processes it
    queue = FairQueue()
    try:
        job = Job(
            job_type="execute_run",
            run_id=run_id,
            function_id=fn.function_id,
            tenant_id=str(tenant.id),
            data={
                "function_uuid": str(fn.id),
                "endpoint_url": fn.endpoint_url,
                "config": fn.config,
                "trigger_data": run.trigger_data,
            },
            max_attempts=fn.retries,
        )
        await queue.enqueue(job)
    finally:
        await queue.close()

    return RunActionResponse(
        success=True,
        message="Run queued for retry. Completed steps will be replayed from cache.",
        run_id=run_id,
    )


@router.post("/{run_id}/replay", response_model=RunResponse)
async def replay_run(
    run_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> RunResponse:
    """
    Replay a failed or completed run.

    Creates a new run with the same trigger data.
    """
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    result = await session.execute(
        select(Run)
        .where(
            Run.tenant_id == tenant.id,
            Run.id == run_uuid,
        )
        .options(selectinload(Run.function))
    )
    original_run = result.scalar_one_or_none()

    if not original_run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Create new run
    new_run = Run(
        tenant_id=tenant.id,
        function_id=original_run.function_id,
        event_id=original_run.event_id,
        status=RunStatus.PENDING,
        trigger_type=original_run.trigger_type,
        trigger_data=original_run.trigger_data,
        max_attempts=original_run.max_attempts,
    )

    session.add(new_run)
    await session.commit()
    await session.refresh(new_run)

    # Fetch the function to build the job payload
    fn_result = await session.execute(
        select(Function).where(Function.id == new_run.function_id)
    )
    fn = fn_result.scalar_one_or_none()
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")

    # Load steps relationship
    result = await session.execute(
        select(Run)
        .where(Run.id == new_run.id)
        .options(selectinload(Run.steps))
    )
    new_run = result.scalar_one()

    # Enqueue the new run so the executor picks it up
    queue = FairQueue()
    try:
        job = Job(
            job_type="execute_run",
            run_id=str(new_run.id),
            function_id=fn.function_id,
            tenant_id=str(tenant.id),
            data={
                "function_uuid": str(fn.id),
                "endpoint_url": fn.endpoint_url,
                "config": fn.config,
                "trigger_data": new_run.trigger_data,
            },
            max_attempts=fn.retries,
        )
        await queue.enqueue(job)
    finally:
        await queue.close()

    return run_to_response(new_run)


@router.get("/{run_id}/steps", response_model=list[StepResponse])
async def get_run_steps(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[StepResponse]:
    """Get all steps for a run."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    result = await session.execute(
        select(Step)
        .where(Step.run_id == run_uuid)
        .order_by(Step.created_at)
    )
    steps = result.scalars().all()

    return [
        StepResponse(
            id=str(step.id),
            step_id=step.step_id,
            step_type=step.step_type.value if hasattr(step.step_type, 'value') else step.step_type,
            status=step.status.value if hasattr(step.status, 'value') else step.status,
            input=step.input,
            output=step.output,
            error=step.error,
            attempt=step.attempt,
            max_attempts=step.max_attempts,
            tool_name=step.tool_name,
            tool_call_id=step.tool_call_id,
            tool_input=step.tool_input,
            tool_output=step.tool_output,
            agent_state=step.agent_state,
            started_at=step.started_at,
            ended_at=step.ended_at,
            created_at=step.created_at,
        )
        for step in steps
    ]


@router.get("/{run_id}/tool-calls", response_model=ToolCallsResponse)
async def get_run_tool_calls(
    run_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ToolCallsResponse:
    """Get all tool calls for a specific run."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    # Verify run exists and belongs to tenant
    run_result = await session.execute(
        select(Run).where(
            Run.tenant_id == tenant.id,
            Run.id == run_uuid,
        )
    )
    run = run_result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get all steps with tool calls
    result = await session.execute(
        select(Step)
        .where(
            Step.run_id == run_uuid,
            Step.tool_name.isnot(None),
        )
        .order_by(Step.created_at)
    )
    steps = result.scalars().all()

    tool_calls = [
        ToolCallResponse(
            step_id=str(step.id),
            tool_name=step.tool_name,
            tool_call_id=step.tool_call_id,
            tool_input=step.tool_input,
            tool_output=step.tool_output,
            status=step.status.value if hasattr(step.status, 'value') else step.status,
            started_at=step.started_at,
            ended_at=step.ended_at,
        )
        for step in steps
    ]

    return ToolCallsResponse(
        tool_calls=tool_calls,
        total=len(tool_calls),
    )


@router.post("/cleanup/stale", response_model=dict)
async def cleanup_stale_runs(
    tenant: TenantWithDevFallback,
    max_age_hours: int = Query(1, ge=1, le=168, description="Max age in hours for running runs (1-168)"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Cancel stale runs that have been running/pending for too long without progress.

    This helps clean up runs that may have gotten stuck due to:
    - Executor crashes
    - Network issues
    - Long-running approval waits that timed out
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

    # Find stale runs: running or pending, started before cutoff, no recent step activity
    result = await session.execute(
        select(Run)
        .where(
            Run.tenant_id == tenant.id,
            Run.status.in_([RunStatus.RUNNING, RunStatus.PENDING, RunStatus.PAUSED]),
            or_(
                Run.started_at < cutoff_time,
                and_(Run.started_at.is_(None), Run.created_at < cutoff_time)
            )
        )
    )
    stale_runs = result.scalars().all()

    cancelled_count = 0
    cancelled_ids = []

    for run in stale_runs:
        run.status = RunStatus.FAILED
        run.ended_at = datetime.utcnow()
        run.error = {
            "type": "StaleRunTimeout",
            "message": f"Run was stale for over {max_age_hours} hours without completion"
        }
        cancelled_count += 1
        cancelled_ids.append(str(run.id))

    if cancelled_count > 0:
        await session.commit()

    return {
        "success": True,
        "message": f"Cleaned up {cancelled_count} stale runs",
        "cancelled_count": cancelled_count,
        "cancelled_run_ids": cancelled_ids,
    }
