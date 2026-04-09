"""Comment and collaboration endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.db import get_session
from flowforge_server.db.models import Comment, Task

router = APIRouter(prefix="/comments", tags=["collaboration"])


# --- Schemas ---

class CreateCommentRequest(BaseModel):
    task_id: str | None = None
    run_id: str | None = None
    content: str = Field(..., min_length=1)
    comment_type: str = "comment"
    author_user_id: str | None = None
    author_agent_id: str | None = None
    mentions: list[dict] = Field(default_factory=list)


class UpdateCommentRequest(BaseModel):
    content: str | None = None


class AddReactionRequest(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=10)
    user_id: str


class CommentResponse(BaseModel):
    id: str
    task_id: str | None
    run_id: str | None
    author_type: str
    author_user_id: str | None
    author_agent_id: str | None
    author: dict | None
    content: str
    comment_type: str
    mentions: list | dict
    reactions: dict
    created_at: str | None
    updated_at: str | None


class CommentsListResponse(BaseModel):
    comments: list[CommentResponse]
    total: int


def _safe_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {value}")


# --- Endpoints ---

@router.get("", response_model=CommentsListResponse)
async def list_comments(
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
    task_id: str | None = Query(None),
    run_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> CommentsListResponse:
    """List comments for a task or run."""
    query = select(Comment)

    if task_id:
        # Verify task belongs to tenant
        task_uuid = _safe_uuid(task_id)
        task_result = await session.execute(
            select(Task).where(Task.id == task_uuid, Task.tenant_id == tenant.id)
        )
        if not task_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Task not found")
        query = query.where(Comment.task_id == task_uuid)
    elif run_id:
        query = query.where(Comment.run_id == _safe_uuid(run_id))
    else:
        raise HTTPException(status_code=400, detail="Provide task_id or run_id")

    query = query.order_by(Comment.created_at.asc()).limit(limit).offset(offset)
    result = await session.execute(query)
    comments = result.scalars().all()

    return CommentsListResponse(
        comments=[CommentResponse(**c.to_dict()) for c in comments],
        total=len(comments),
    )


@router.post("", response_model=CommentResponse, status_code=201)
async def create_comment(
    data: CreateCommentRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> CommentResponse:
    """Create a comment on a task or run."""
    if not data.task_id and not data.run_id:
        raise HTTPException(status_code=400, detail="Provide task_id or run_id")

    comment = Comment(
        task_id=_safe_uuid(data.task_id),
        run_id=_safe_uuid(data.run_id),
        content=data.content,
        comment_type=data.comment_type,
        author_user_id=_safe_uuid(data.author_user_id),
        author_agent_id=_safe_uuid(data.author_agent_id),
        mentions=data.mentions,
    )

    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    return CommentResponse(**comment.to_dict())


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: str,
    data: UpdateCommentRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> CommentResponse:
    """Update a comment."""
    comment_uuid = _safe_uuid(comment_id)
    result = await session.execute(
        select(Comment).where(Comment.id == comment_uuid)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if data.content is not None:
        comment.content = data.content

    await session.commit()
    await session.refresh(comment)

    return CommentResponse(**comment.to_dict())


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a comment."""
    comment_uuid = _safe_uuid(comment_id)
    result = await session.execute(
        select(Comment).where(Comment.id == comment_uuid)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    await session.delete(comment)
    await session.commit()


@router.post("/{comment_id}/reactions", response_model=CommentResponse)
async def add_reaction(
    comment_id: str,
    data: AddReactionRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> CommentResponse:
    """Add an emoji reaction to a comment."""
    comment_uuid = _safe_uuid(comment_id)
    result = await session.execute(
        select(Comment).where(Comment.id == comment_uuid)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    reactions = dict(comment.reactions or {})
    if data.emoji not in reactions:
        reactions[data.emoji] = []
    if data.user_id not in reactions[data.emoji]:
        reactions[data.emoji].append(data.user_id)

    comment.reactions = reactions
    await session.commit()
    await session.refresh(comment)

    return CommentResponse(**comment.to_dict())
