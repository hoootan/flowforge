"""Task management endpoints for Kanban board."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.db import get_session
from flowforge_server.db.models import Task, TaskPriority, TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


# --- Schemas ---

class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    status: str = TaskStatus.TODO.value
    priority: str = TaskPriority.NONE.value
    labels: list[str] = Field(default_factory=list)
    assignee_user_id: str | None = None
    assignee_agent_id: str | None = None
    parent_task_id: str | None = None
    function_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    labels: list[str] | None = None
    assignee_user_id: str | None = None
    assignee_agent_id: str | None = None
    function_id: str | None = None
    run_id: str | None = None
    metadata: dict | None = None


class TaskResponse(BaseModel):
    id: str
    identifier: str
    title: str
    description: str | None
    status: str
    priority: str
    labels: list | dict
    assignee_type: str | None
    assignee_user_id: str | None
    assignee_agent_id: str | None
    assignee_user: dict | None
    assignee_agent: dict | None
    created_by_user_id: str | None
    parent_task_id: str | None
    function_id: str | None
    run_id: str | None
    sub_tasks_count: int
    comments_count: int
    metadata: dict
    created_at: str | None
    updated_at: str | None


class TasksListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int


class TasksBoardResponse(BaseModel):
    """Kanban board view grouped by status."""
    columns: dict[str, list[TaskResponse]]
    total: int


# --- Helpers ---

async def _get_next_sequence(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Get next task sequence number for the tenant."""
    result = await session.execute(
        select(func.coalesce(func.max(Task.sequence), 0)).where(
            Task.tenant_id == tenant_id
        )
    )
    return result.scalar() + 1


def _safe_uuid(value: str | None) -> uuid.UUID | None:
    """Parse optional UUID string."""
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {value}")


# --- Endpoints ---

@router.get("", response_model=TasksListResponse)
async def list_tasks(
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    assignee_user_id: str | None = Query(None),
    assignee_agent_id: str | None = Query(None),
    parent_task_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> TasksListResponse:
    """List tasks with optional filters."""
    query = select(Task).where(Task.tenant_id == tenant.id)

    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    if assignee_user_id:
        query = query.where(Task.assignee_user_id == uuid.UUID(assignee_user_id))
    if assignee_agent_id:
        query = query.where(Task.assignee_agent_id == uuid.UUID(assignee_agent_id))
    if parent_task_id:
        query = query.where(Task.parent_task_id == uuid.UUID(parent_task_id))
    else:
        # By default, only show top-level tasks
        query = query.where(Task.parent_task_id.is_(None))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(Task.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    tasks = result.scalars().all()

    return TasksListResponse(
        tasks=[TaskResponse(**t.to_dict()) for t in tasks],
        total=total,
    )


@router.get("/board", response_model=TasksBoardResponse)
async def get_task_board(
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
    assignee_user_id: str | None = Query(None),
    assignee_agent_id: str | None = Query(None),
) -> TasksBoardResponse:
    """Get tasks organized as a Kanban board."""
    query = select(Task).where(
        Task.tenant_id == tenant.id,
        Task.parent_task_id.is_(None),  # Top-level only
    )

    if assignee_user_id:
        query = query.where(Task.assignee_user_id == uuid.UUID(assignee_user_id))
    if assignee_agent_id:
        query = query.where(Task.assignee_agent_id == uuid.UUID(assignee_agent_id))

    query = query.order_by(Task.created_at.desc())
    result = await session.execute(query)
    tasks = result.scalars().all()

    # Group by status
    columns: dict[str, list[TaskResponse]] = {
        status.value: [] for status in TaskStatus
    }

    for task in tasks:
        col = task.status if task.status in columns else TaskStatus.TODO.value
        columns[col].append(TaskResponse(**task.to_dict()))

    return TasksBoardResponse(columns=columns, total=len(tasks))


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: CreateTaskRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """Create a new task."""
    sequence = await _get_next_sequence(session, tenant.id)
    identifier = f"FF-{sequence}"

    task = Task(
        tenant_id=tenant.id,
        identifier=identifier,
        sequence=sequence,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        labels=data.labels,
        assignee_user_id=_safe_uuid(data.assignee_user_id),
        assignee_agent_id=_safe_uuid(data.assignee_agent_id),
        parent_task_id=_safe_uuid(data.parent_task_id),
        function_id=_safe_uuid(data.function_id),
        metadata=data.metadata,
    )

    session.add(task)
    await session.commit()
    await session.refresh(task)

    return TaskResponse(**task.to_dict())


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """Get task details."""
    task_uuid = _safe_uuid(task_id)
    result = await session.execute(
        select(Task).where(Task.id == task_uuid, Task.tenant_id == tenant.id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(**task.to_dict())


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: UpdateTaskRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """Update a task (used for drag-and-drop status changes, assignment, etc.)."""
    task_uuid = _safe_uuid(task_id)
    result = await session.execute(
        select(Task).where(Task.id == task_uuid, Task.tenant_id == tenant.id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)

    # Convert UUID strings to UUID objects
    for field in ("assignee_user_id", "assignee_agent_id", "function_id", "run_id"):
        if field in update_data:
            update_data[field] = _safe_uuid(update_data[field])

    # Clear opposite assignee when setting one
    if "assignee_user_id" in update_data and update_data["assignee_user_id"]:
        update_data["assignee_agent_id"] = None
    elif "assignee_agent_id" in update_data and update_data["assignee_agent_id"]:
        update_data["assignee_user_id"] = None

    for key, value in update_data.items():
        setattr(task, key, value)

    await session.commit()
    await session.refresh(task)

    return TaskResponse(**task.to_dict())


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a task."""
    task_uuid = _safe_uuid(task_id)
    result = await session.execute(
        select(Task).where(Task.id == task_uuid, Task.tenant_id == tenant.id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await session.delete(task)
    await session.commit()
