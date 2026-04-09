"""Notification inbox endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import CurrentUser
from flowforge_server.db import get_session
from flowforge_server.db.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    body: str | None
    resource_type: str | None
    resource_id: str | None
    data: dict
    is_read: bool
    is_archived: bool
    created_at: str | None


class NotificationsListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    unread_count: int


@router.get("", response_model=NotificationsListResponse)
async def list_notifications(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    is_read: bool | None = Query(None),
    is_archived: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> NotificationsListResponse:
    """List notifications for the current user."""
    query = select(Notification).where(
        Notification.user_id == user.id,
        Notification.is_archived == is_archived,
    )

    if is_read is not None:
        query = query.where(Notification.is_read == is_read)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Count unread
    unread_result = await session.execute(
        select(func.count()).where(
            Notification.user_id == user.id,
            Notification.is_read == False,
            Notification.is_archived == False,
        )
    )
    unread_count = unread_result.scalar() or 0

    # Paginate
    query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    notifications = result.scalars().all()

    return NotificationsListResponse(
        notifications=[NotificationResponse(**n.to_dict()) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Mark a notification as read."""
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    result = await session.execute(
        select(Notification).where(
            Notification.id == notif_uuid,
            Notification.user_id == user.id,
        )
    )
    notif = result.scalar_one_or_none()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    await session.commit()

    return {"success": True}


@router.post("/read-all")
async def mark_all_read(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Mark all notifications as read."""
    await session.execute(
        update(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    await session.commit()

    return {"success": True}


@router.post("/{notification_id}/archive")
async def archive_notification(
    notification_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Archive a notification."""
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    result = await session.execute(
        select(Notification).where(
            Notification.id == notif_uuid,
            Notification.user_id == user.id,
        )
    )
    notif = result.scalar_one_or_none()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_archived = True
    notif.is_read = True
    await session.commit()

    return {"success": True}
