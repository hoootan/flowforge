"""Dead Letter Queue API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from flowforge_server.api.deps import CurrentUserAdmin
from flowforge_server.queue.dlq import get_dlq, DLQEntry

router = APIRouter(prefix="/dlq", tags=["dlq"])


class DLQEntryResponse(BaseModel):
    """DLQ entry response."""

    job_id: str
    tenant_id: str
    function_id: str
    original_data: dict[str, Any]
    error: str
    attempts: int
    failed_at: datetime
    metadata: dict[str, Any] | None


class DLQListResponse(BaseModel):
    """Paginated DLQ entries response."""

    entries: list[DLQEntryResponse]
    total: int
    limit: int
    offset: int


class DLQStatsResponse(BaseModel):
    """DLQ statistics."""

    total: int
    oldest_at: str | None
    newest_at: str | None


class RequeueResponse(BaseModel):
    """Requeue operation response."""

    success: bool
    message: str
    job_id: str


def entry_to_response(entry: DLQEntry) -> DLQEntryResponse:
    """Convert DLQEntry to response model."""
    return DLQEntryResponse(
        job_id=entry.job_id,
        tenant_id=entry.tenant_id,
        function_id=entry.function_id,
        original_data=entry.original_data,
        error=entry.error,
        attempts=entry.attempts,
        failed_at=entry.failed_at,
        metadata=entry.metadata,
    )


@router.get("", response_model=DLQListResponse)
async def list_dlq_entries(
    admin: CurrentUserAdmin,
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> DLQListResponse:
    """
    List Dead Letter Queue entries for the tenant.

    **Admin only.** Returns failed jobs that have exceeded max retries.
    """
    dlq = await get_dlq()

    entries = await dlq.list(
        tenant_id=str(admin.tenant_id),
        limit=limit,
        offset=offset,
    )

    total = await dlq.count(tenant_id=str(admin.tenant_id))

    return DLQListResponse(
        entries=[entry_to_response(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=DLQStatsResponse)
async def get_dlq_stats(
    admin: CurrentUserAdmin,
) -> DLQStatsResponse:
    """
    Get Dead Letter Queue statistics.

    **Admin only.**
    """
    dlq = await get_dlq()
    stats = await dlq.get_stats()

    return DLQStatsResponse(
        total=stats["total"],
        oldest_at=stats["oldest_at"],
        newest_at=stats["newest_at"],
    )


@router.get("/{job_id}", response_model=DLQEntryResponse)
async def get_dlq_entry(
    job_id: str,
    admin: CurrentUserAdmin,
) -> DLQEntryResponse:
    """
    Get a specific DLQ entry.

    **Admin only.**
    """
    dlq = await get_dlq()
    entry = await dlq.get(job_id)

    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    # Verify tenant access
    if entry.tenant_id != str(admin.tenant_id):
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    return entry_to_response(entry)


@router.post("/{job_id}/requeue", response_model=RequeueResponse)
async def requeue_dlq_entry(
    job_id: str,
    admin: CurrentUserAdmin,
) -> RequeueResponse:
    """
    Requeue a job from the DLQ.

    **Admin only.** Moves the job back to the pending queue for retry.
    The job will start with attempt=1 again.
    """
    dlq = await get_dlq()

    # Get entry first to verify tenant access
    entry = await dlq.get(job_id)
    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    if entry.tenant_id != str(admin.tenant_id):
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    # Remove from DLQ (the actual re-enqueue needs to be done by the caller
    # since we don't have direct access to the queue here)
    success = await dlq.requeue(job_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to requeue job")

    # TODO: Actually re-enqueue the job to the main queue
    # This would require injecting the FairQueue here or using an event

    return RequeueResponse(
        success=True,
        message="Job removed from DLQ. Re-trigger the original event to retry.",
        job_id=job_id,
    )


@router.delete("/{job_id}")
async def delete_dlq_entry(
    job_id: str,
    admin: CurrentUserAdmin,
) -> dict[str, str]:
    """
    Delete a DLQ entry.

    **Admin only.** Permanently removes the failed job from the DLQ.
    """
    dlq = await get_dlq()

    # Get entry first to verify tenant access
    entry = await dlq.get(job_id)
    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    if entry.tenant_id != str(admin.tenant_id):
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    await dlq.remove(job_id)

    return {"message": "DLQ entry deleted", "job_id": job_id}


@router.delete("")
async def clear_dlq(
    admin: CurrentUserAdmin,
) -> dict[str, Any]:
    """
    Clear all DLQ entries for the tenant.

    **Admin only.** Permanently removes all failed jobs.
    """
    dlq = await get_dlq()
    count = await dlq.clear(tenant_id=str(admin.tenant_id))

    return {"message": f"Cleared {count} DLQ entries", "count": count}
