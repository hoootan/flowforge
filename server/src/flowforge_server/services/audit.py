"""Audit logging service for security-sensitive operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models.audit_log import AuditLog, AuditAction
from flowforge_server.middleware.correlation import get_correlation_id
from flowforge_server.logging import Loggers


class AuditService:
    """
    Service for creating and querying audit logs.

    Usage:
        audit = AuditService(session)
        await audit.log(
            tenant_id=...,
            actor_id=...,
            action=AuditAction.LOGIN_SUCCESS,
            ...
        )
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._log = Loggers.api()

    async def log(
        self,
        tenant_id: uuid.UUID,
        action: AuditAction | str,
        actor_id: uuid.UUID | None = None,
        actor_type: str = "user",
        actor_display: str | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        resource_display: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            tenant_id: The tenant context
            action: The action being logged
            actor_id: ID of the user or API key performing the action
            actor_type: Type of actor ("user", "api_key", "system")
            actor_display: Display name for the actor (email, key prefix)
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource
            resource_display: Display name for the resource
            details: Additional context/details
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether the action succeeded
            error_message: Error message if failed

        Returns:
            The created AuditLog entry
        """
        # Get correlation ID from context if available
        correlation_id = get_correlation_id()

        # Convert action enum to string if needed
        action_str = action.value if isinstance(action, AuditAction) else action

        entry = AuditLog(
            tenant_id=tenant_id,
            timestamp=datetime.now(timezone.utc),
            actor_id=actor_id,
            actor_type=actor_type,
            actor_display=actor_display,
            action=action_str,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_display=resource_display,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            success=success,
            error_message=error_message,
        )

        self.session.add(entry)
        await self.session.flush()

        # Also log to structured logger for real-time monitoring
        self._log.info(
            "audit_event",
            action=action_str,
            actor_id=str(actor_id) if actor_id else None,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            success=success,
            correlation_id=correlation_id,
        )

        return entry

    async def log_login(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        """Log a login attempt."""
        action = AuditAction.LOGIN_SUCCESS if success else AuditAction.LOGIN_FAILED
        return await self.log(
            tenant_id=tenant_id,
            action=action,
            actor_id=user_id if success else None,
            actor_type="user",
            actor_display=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            details={"email": email},
        )

    async def log_user_action(
        self,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        actor_email: str,
        action: AuditAction,
        target_user_id: uuid.UUID,
        target_email: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log a user management action."""
        return await self.log(
            tenant_id=tenant_id,
            action=action,
            actor_id=actor_id,
            actor_type="user",
            actor_display=actor_email,
            resource_type="user",
            resource_id=target_user_id,
            resource_display=target_email,
            details=details,
            ip_address=ip_address,
        )

    async def log_api_key_action(
        self,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        actor_email: str,
        action: AuditAction,
        key_id: uuid.UUID,
        key_name: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log an API key management action."""
        return await self.log(
            tenant_id=tenant_id,
            action=action,
            actor_id=actor_id,
            actor_type="user",
            actor_display=actor_email,
            resource_type="api_key",
            resource_id=key_id,
            resource_display=key_name,
            details=details,
            ip_address=ip_address,
        )

    async def log_security_event(
        self,
        tenant_id: uuid.UUID,
        action: AuditAction,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a security event (rate limit, lockout, etc.)."""
        return await self.log(
            tenant_id=tenant_id,
            action=action,
            actor_type="system",
            ip_address=ip_address,
            details=details,
            success=False,
        )

    async def query(
        self,
        tenant_id: uuid.UUID,
        action: AuditAction | str | None = None,
        actor_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        success: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """
        Query audit logs with filters.

        Args:
            tenant_id: Required tenant context
            action: Filter by action type
            actor_id: Filter by actor
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            start_time: Filter by minimum timestamp
            end_time: Filter by maximum timestamp
            success: Filter by success status
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            List of matching AuditLog entries
        """
        query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if action:
            action_str = action.value if isinstance(action, AuditAction) else action
            query = query.where(AuditLog.action == action_str)

        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)

        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)

        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)

        if start_time:
            query = query.where(AuditLog.timestamp >= start_time)

        if end_time:
            query = query.where(AuditLog.timestamp <= end_time)

        if success is not None:
            query = query.where(AuditLog.success == success)

        query = query.order_by(desc(AuditLog.timestamp)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        tenant_id: uuid.UUID,
        action: AuditAction | str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Count audit log entries matching filters."""
        from sqlalchemy import func

        query = select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tenant_id)

        if action:
            action_str = action.value if isinstance(action, AuditAction) else action
            query = query.where(AuditLog.action == action_str)

        if start_time:
            query = query.where(AuditLog.timestamp >= start_time)

        if end_time:
            query = query.where(AuditLog.timestamp <= end_time)

        result = await self.session.execute(query)
        return result.scalar() or 0
