"""Audit log API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import CurrentUserAdmin
from flowforge_server.db import get_session
from flowforge_server.db.models.audit_log import AuditAction
from flowforge_server.services.audit import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: str
    timestamp: datetime
    tenant_id: str
    actor_id: str | None
    actor_type: str
    actor_display: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    resource_display: str | None
    details: dict[str, Any] | None
    ip_address: str | None
    correlation_id: str | None
    success: bool
    error_message: str | None


class AuditLogsResponse(BaseModel):
    """Paginated audit logs response."""

    logs: list[AuditLogResponse]
    total: int
    limit: int
    offset: int


class AuditStatsResponse(BaseModel):
    """Audit log statistics."""

    total_events: int
    login_success: int
    login_failed: int
    user_changes: int
    api_key_changes: int


@router.get("", response_model=AuditLogsResponse)
async def list_audit_logs(
    admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
    action: str | None = Query(None, description="Filter by action type"),
    actor_id: str | None = Query(None, description="Filter by actor ID"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    start_time: datetime | None = Query(None, description="Filter by start time"),
    end_time: datetime | None = Query(None, description="Filter by end time"),
    success: bool | None = Query(None, description="Filter by success status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> AuditLogsResponse:
    """
    List audit logs for the tenant.

    **Admin only.** Returns paginated audit log entries with optional filters.
    """
    import uuid

    audit_service = AuditService(session)

    # Convert string IDs to UUIDs
    actor_uuid = uuid.UUID(actor_id) if actor_id else None
    resource_uuid = uuid.UUID(resource_id) if resource_id else None

    logs = await audit_service.query(
        tenant_id=admin.tenant_id,
        action=action,
        actor_id=actor_uuid,
        resource_type=resource_type,
        resource_id=resource_uuid,
        start_time=start_time,
        end_time=end_time,
        success=success,
        limit=limit,
        offset=offset,
    )

    total = await audit_service.count(
        tenant_id=admin.tenant_id,
        action=action,
        start_time=start_time,
        end_time=end_time,
    )

    return AuditLogsResponse(
        logs=[
            AuditLogResponse(
                id=str(log.id),
                timestamp=log.timestamp,
                tenant_id=str(log.tenant_id),
                actor_id=str(log.actor_id) if log.actor_id else None,
                actor_type=log.actor_type,
                actor_display=log.actor_display,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=str(log.resource_id) if log.resource_id else None,
                resource_display=log.resource_display,
                details=log.details,
                ip_address=log.ip_address,
                correlation_id=log.correlation_id,
                success=log.success,
                error_message=log.error_message,
            )
            for log in logs
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
    start_time: datetime | None = Query(None, description="Filter by start time"),
    end_time: datetime | None = Query(None, description="Filter by end time"),
) -> AuditStatsResponse:
    """
    Get audit log statistics.

    **Admin only.** Returns counts of different event types.
    """
    audit_service = AuditService(session)

    total = await audit_service.count(
        tenant_id=admin.tenant_id,
        start_time=start_time,
        end_time=end_time,
    )

    login_success = await audit_service.count(
        tenant_id=admin.tenant_id,
        action=AuditAction.LOGIN_SUCCESS,
        start_time=start_time,
        end_time=end_time,
    )

    login_failed = await audit_service.count(
        tenant_id=admin.tenant_id,
        action=AuditAction.LOGIN_FAILED,
        start_time=start_time,
        end_time=end_time,
    )

    # Count user changes
    user_actions = [
        AuditAction.USER_CREATED,
        AuditAction.USER_UPDATED,
        AuditAction.USER_DELETED,
        AuditAction.USER_ROLE_CHANGED,
    ]
    user_changes = 0
    for action in user_actions:
        user_changes += await audit_service.count(
            tenant_id=admin.tenant_id,
            action=action,
            start_time=start_time,
            end_time=end_time,
        )

    # Count API key changes
    api_key_actions = [
        AuditAction.API_KEY_CREATED,
        AuditAction.API_KEY_REVOKED,
    ]
    api_key_changes = 0
    for action in api_key_actions:
        api_key_changes += await audit_service.count(
            tenant_id=admin.tenant_id,
            action=action,
            start_time=start_time,
            end_time=end_time,
        )

    return AuditStatsResponse(
        total_events=total,
        login_success=login_success,
        login_failed=login_failed,
        user_changes=user_changes,
        api_key_changes=api_key_changes,
    )


@router.get("/actions")
async def list_audit_actions(
    admin: CurrentUserAdmin,
) -> list[dict[str, str]]:
    """
    List all available audit action types.

    **Admin only.** Useful for building filter UIs.
    """
    return [
        {"value": action.value, "label": action.value.replace("_", " ").title()}
        for action in AuditAction
    ]
