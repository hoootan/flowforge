"""Tool approval management endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.api.schemas.approvals import (
    ApprovalActionResponse,
    ApprovalsResponse,
    ApproveToolRequest,
    RejectToolRequest,
    ToolApprovalResponse,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import ApprovalStatus, Run, ToolApproval

router = APIRouter(prefix="/approvals", tags=["approvals"])


def approval_to_response(approval: ToolApproval) -> ToolApprovalResponse:
    """Convert ToolApproval model to response schema."""
    return ToolApprovalResponse(
        id=str(approval.id),
        run_id=str(approval.run_id),
        step_id=str(approval.step_id),
        tool_name=approval.tool_name,
        tool_call_id=approval.tool_call_id,
        tool_arguments=approval.tool_arguments,
        status=approval.status.value if isinstance(approval.status, ApprovalStatus) else approval.status,
        requested_at=approval.requested_at,
        timeout_at=approval.timeout_at,
        resolved_at=approval.resolved_at,
        resolved_by=approval.resolved_by,
        rejection_reason=approval.rejection_reason,
        created_at=approval.created_at,
    )


@router.get("", response_model=ApprovalsResponse)
async def list_approvals(
    tenant: TenantWithDevFallback,
    run_id: str | None = Query(None, description="Filter by run ID"),
    status: str | None = Query(None, description="Filter by status"),
    pending_only: bool = Query(False, description="Show only pending approvals"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> ApprovalsResponse:
    """List tool approval requests with optional filtering."""
    # Build query with joins to ensure tenant access control
    query = (
        select(ToolApproval)
        .join(Run, ToolApproval.run_id == Run.id)
        .where(Run.tenant_id == tenant.id)
        .options(selectinload(ToolApproval.run), selectinload(ToolApproval.step))
    )

    if run_id:
        try:
            run_uuid = uuid.UUID(run_id)
            query = query.where(ToolApproval.run_id == run_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid run ID format")

    if pending_only:
        query = query.where(ToolApproval.status == ApprovalStatus.PENDING)
    elif status:
        try:
            status_enum = ApprovalStatus(status)
            query = query.where(ToolApproval.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join([s.value for s in ApprovalStatus])}",
            )

    # Get total count
    count_query = select(func.count()).select_from(
        select(ToolApproval.id)
        .join(Run, ToolApproval.run_id == Run.id)
        .where(Run.tenant_id == tenant.id)
        .subquery()
    )

    if run_id:
        count_query = select(func.count()).select_from(
            select(ToolApproval.id)
            .join(Run, ToolApproval.run_id == Run.id)
            .where(
                Run.tenant_id == tenant.id,
                ToolApproval.run_id == run_uuid,
            )
            .subquery()
        )

    if pending_only:
        count_query = select(func.count()).select_from(
            select(ToolApproval.id)
            .join(Run, ToolApproval.run_id == Run.id)
            .where(
                Run.tenant_id == tenant.id,
                ToolApproval.status == ApprovalStatus.PENDING,
            )
            .subquery()
        )

    total = (await session.execute(count_query)).scalar() or 0

    # Get paginated results
    query = query.order_by(ToolApproval.requested_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    approvals = result.scalars().unique().all()

    return ApprovalsResponse(
        approvals=[approval_to_response(approval) for approval in approvals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{approval_id}", response_model=ToolApprovalResponse)
async def get_approval(
    approval_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ToolApprovalResponse:
    """Get a specific tool approval request by ID."""
    try:
        approval_uuid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval ID format")

    result = await session.execute(
        select(ToolApproval)
        .join(Run, ToolApproval.run_id == Run.id)
        .where(
            Run.tenant_id == tenant.id,
            ToolApproval.id == approval_uuid,
        )
        .options(selectinload(ToolApproval.run), selectinload(ToolApproval.step))
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    return approval_to_response(approval)


@router.post("/{approval_id}/approve", response_model=ApprovalActionResponse)
async def approve_tool(
    approval_id: str,
    request: ApproveToolRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ApprovalActionResponse:
    """Approve a pending tool call."""
    try:
        approval_uuid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval ID format")

    result = await session.execute(
        select(ToolApproval)
        .join(Run, ToolApproval.run_id == Run.id)
        .where(
            Run.tenant_id == tenant.id,
            ToolApproval.id == approval_uuid,
        )
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.is_terminal:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve tool call with status '{approval.status.value}'",
        )

    # Check if expired
    if approval.is_expired:
        approval.status = ApprovalStatus.TIMEOUT
        approval.resolved_at = datetime.utcnow()
        await session.commit()
        raise HTTPException(
            status_code=400,
            detail="Approval request has timed out",
        )

    # Approve the tool call
    approval.status = ApprovalStatus.APPROVED
    approval.resolved_at = datetime.utcnow()
    approval.resolved_by = request.resolved_by
    if request.modified_arguments:
        approval.modified_arguments = request.modified_arguments

    await session.commit()

    # TODO: Trigger event to resume the paused workflow
    # This would involve sending a "tool/approved" event with the approval details

    return ApprovalActionResponse(
        success=True,
        message="Tool call approved successfully",
        approval_id=approval_id,
    )


@router.post("/{approval_id}/reject", response_model=ApprovalActionResponse)
async def reject_tool(
    approval_id: str,
    request: RejectToolRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ApprovalActionResponse:
    """Reject a pending tool call."""
    try:
        approval_uuid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval ID format")

    result = await session.execute(
        select(ToolApproval)
        .join(Run, ToolApproval.run_id == Run.id)
        .where(
            Run.tenant_id == tenant.id,
            ToolApproval.id == approval_uuid,
        )
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.is_terminal:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject tool call with status '{approval.status.value}'",
        )

    # Check if expired
    if approval.is_expired:
        approval.status = ApprovalStatus.TIMEOUT
        approval.resolved_at = datetime.utcnow()
        await session.commit()
        raise HTTPException(
            status_code=400,
            detail="Approval request has timed out",
        )

    # Reject the tool call
    approval.status = ApprovalStatus.REJECTED
    approval.resolved_at = datetime.utcnow()
    approval.resolved_by = request.resolved_by
    approval.rejection_reason = request.reason

    await session.commit()

    # TODO: Trigger event to resume the paused workflow
    # This would involve sending a "tool/rejected" event with the rejection details

    return ApprovalActionResponse(
        success=True,
        message="Tool call rejected successfully",
        approval_id=approval_id,
    )


@router.post("/cleanup/orphaned", response_model=dict)
async def cleanup_orphaned_approvals(
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Clean up orphaned approvals whose runs are in a terminal state.

    This marks pending approvals as TIMEOUT if their associated run
    has already completed, failed, or been cancelled.
    """
    from flowforge_server.db.models import RunStatus

    # Find pending approvals whose runs are terminal
    result = await session.execute(
        select(ToolApproval)
        .join(Run, ToolApproval.run_id == Run.id)
        .where(
            Run.tenant_id == tenant.id,
            ToolApproval.status == ApprovalStatus.PENDING,
            Run.status.in_([
                RunStatus.COMPLETED,
                RunStatus.FAILED,
                RunStatus.CANCELLED,
            ])
        )
    )
    orphaned_approvals = result.scalars().all()

    cleaned_count = 0
    cleaned_ids = []

    for approval in orphaned_approvals:
        approval.status = ApprovalStatus.TIMEOUT
        approval.resolved_at = datetime.utcnow()
        approval.resolved_by = "system"
        approval.rejection_reason = "Run terminated before approval was resolved"
        cleaned_count += 1
        cleaned_ids.append(str(approval.id))

    if cleaned_count > 0:
        await session.commit()

    return {
        "success": True,
        "message": f"Cleaned up {cleaned_count} orphaned approvals",
        "cleaned_count": cleaned_count,
        "cleaned_approval_ids": cleaned_ids,
    }
