"""Tool management endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.api.schemas.tools import (
    ToolCreate,
    ToolResponse,
    ToolsResponse,
    ToolUpdate,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import Tool

router = APIRouter(prefix="/tools", tags=["tools"])


def _tool_response(tool: Tool, hide_code: bool = False) -> ToolResponse:
    """Build a ToolResponse from a Tool model."""
    return ToolResponse(
        id=str(tool.id),
        name=tool.name,
        description=tool.description,
        parameters=tool.parameters,
        tool_type=getattr(tool, "tool_type", "custom"),
        code=None if hide_code else tool.code,
        webhook_url=getattr(tool, "webhook_url", None),
        webhook_method=getattr(tool, "webhook_method", "POST"),
        webhook_headers=getattr(tool, "webhook_headers", None),
        is_builtin=tool.is_builtin,
        requires_approval=tool.requires_approval,
        approval_timeout=tool.approval_timeout,
        is_active=tool.is_active,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


@router.post("", response_model=ToolResponse, status_code=201)
async def create_tool(
    tool_data: ToolCreate,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    """
    Create a new custom tool.

    Tools can be referenced by functions and used by agents.
    Built-in tools cannot be created via this endpoint.
    """
    # Check for existing tool with same name. A soft-deleted row holds the
    # unique-constraint slot, so we restore it instead of hitting IntegrityError.
    existing = await session.execute(
        select(Tool).where(
            Tool.tenant_id == tenant.id,
            Tool.name == tool_data.name,
        )
    )
    existing_tool = existing.scalar_one_or_none()
    if existing_tool and existing_tool.deleted_at is None:
        raise HTTPException(
            status_code=409,
            detail=f"Tool with name '{tool_data.name}' already exists"
        )

    # Also check built-in tools
    builtin = await session.execute(
        select(Tool).where(
            Tool.is_builtin == True,
            Tool.name == tool_data.name,
        )
    )
    if builtin.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Cannot create tool '{tool_data.name}' - a built-in tool with this name exists"
        )

    if existing_tool and existing_tool.deleted_at is not None:
        # Restore the soft-deleted row rather than creating a new UUID.
        existing_tool.deleted_at = None
        existing_tool.description = tool_data.description
        existing_tool.parameters = tool_data.parameters
        existing_tool.tool_type = tool_data.tool_type
        existing_tool.code = tool_data.code
        existing_tool.webhook_url = tool_data.webhook_url
        existing_tool.webhook_method = tool_data.webhook_method
        existing_tool.webhook_headers = tool_data.webhook_headers
        existing_tool.requires_approval = tool_data.requires_approval
        existing_tool.approval_timeout = tool_data.approval_timeout
        existing_tool.is_active = True
        tool = existing_tool
    else:
        tool = Tool(
            tenant_id=tenant.id,
            name=tool_data.name,
            description=tool_data.description,
            parameters=tool_data.parameters,
            tool_type=tool_data.tool_type,
            code=tool_data.code,
            webhook_url=tool_data.webhook_url,
            webhook_method=tool_data.webhook_method,
            webhook_headers=tool_data.webhook_headers,
            is_builtin=False,
            requires_approval=tool_data.requires_approval,
            approval_timeout=tool_data.approval_timeout,
            is_active=True,
        )
        session.add(tool)

    await session.commit()
    await session.refresh(tool)

    return _tool_response(tool)


@router.get("", response_model=ToolsResponse)
async def list_tools(
    tenant: TenantWithDevFallback,
    include_builtin: bool = Query(True, description="Include built-in tools"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    requires_approval: bool | None = Query(None, description="Filter by approval requirement"),
    session: AsyncSession = Depends(get_session),
) -> ToolsResponse:
    """
    List all tools available to the tenant.

    Includes both built-in tools and custom tenant tools.
    """
    # Build query for tenant tools + optionally built-in tools
    if include_builtin:
        query = select(Tool).where(
            or_(
                Tool.tenant_id == tenant.id,
                Tool.is_builtin == True,
            ),
            Tool.deleted_at.is_(None),
        )
    else:
        query = select(Tool).where(
            Tool.tenant_id == tenant.id,
            Tool.deleted_at.is_(None),
        )

    if is_active is not None:
        query = query.where(Tool.is_active == is_active)
    if requires_approval is not None:
        query = query.where(Tool.requires_approval == requires_approval)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Get results
    query = query.order_by(Tool.is_builtin.desc(), Tool.name)
    result = await session.execute(query)
    tools = result.scalars().all()

    return ToolsResponse(
        tools=[_tool_response(tool, hide_code=tool.is_builtin) for tool in tools],
        total=total,
    )


@router.get("/{tool_name}", response_model=ToolResponse)
async def get_tool(
    tool_name: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    """Get a specific tool by name."""
    # Look for tenant tool first, then built-in. Exclude soft-deleted rows;
    # built-ins should always have deleted_at=NULL in practice, so the filter
    # applies uniformly to both.
    result = await session.execute(
        select(Tool).where(
            or_(
                (Tool.tenant_id == tenant.id) & (Tool.name == tool_name),
                (Tool.is_builtin == True) & (Tool.name == tool_name),
            ),
            Tool.deleted_at.is_(None),
        ).order_by(Tool.is_builtin)  # Prefer tenant tools over built-in
    )
    tool = result.scalars().first()

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    return _tool_response(tool, hide_code=tool.is_builtin)


@router.patch("/{tool_name}", response_model=ToolResponse)
async def update_tool(
    tool_name: str,
    update_data: ToolUpdate,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    """Update a tool's configuration. Built-in tools cannot be modified."""
    result = await session.execute(
        select(Tool).where(
            Tool.tenant_id == tenant.id,
            Tool.name == tool_name,
            Tool.deleted_at.is_(None),
        )
    )
    tool = result.scalar_one_or_none()

    if not tool:
        # Check if it's a built-in tool
        builtin = await session.execute(
            select(Tool).where(
                Tool.is_builtin == True,
                Tool.name == tool_name,
            )
        )
        if builtin.scalar_one_or_none():
            raise HTTPException(
                status_code=403,
                detail="Cannot modify built-in tools"
            )
        raise HTTPException(status_code=404, detail="Tool not found")

    if update_data.description is not None:
        tool.description = update_data.description
    if update_data.parameters is not None:
        tool.parameters = update_data.parameters
    if update_data.tool_type is not None:
        tool.tool_type = update_data.tool_type
    if update_data.code is not None:
        tool.code = update_data.code
    if update_data.webhook_url is not None:
        tool.webhook_url = update_data.webhook_url
    if update_data.webhook_method is not None:
        tool.webhook_method = update_data.webhook_method
    if update_data.webhook_headers is not None:
        tool.webhook_headers = update_data.webhook_headers
    if update_data.requires_approval is not None:
        tool.requires_approval = update_data.requires_approval
    if update_data.approval_timeout is not None:
        tool.approval_timeout = update_data.approval_timeout
    if update_data.is_active is not None:
        tool.is_active = update_data.is_active

    await session.commit()
    await session.refresh(tool)

    return _tool_response(tool)


@router.delete("/{tool_name}")
async def delete_tool(
    tool_name: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Soft-delete a tool.

    The row is retained so in-flight runs that already loaded the tool can
    finish, but it is hidden from all user-facing list/get/update queries and
    from the executor (via is_active=False). Built-in tools cannot be deleted.
    Re-creating a tool with the same name restores the row.
    """
    result = await session.execute(
        select(Tool).where(
            Tool.tenant_id == tenant.id,
            Tool.name == tool_name,
            Tool.deleted_at.is_(None),
        )
    )
    tool = result.scalar_one_or_none()

    if not tool:
        # Check if it's a built-in tool
        builtin = await session.execute(
            select(Tool).where(
                Tool.is_builtin == True,
                Tool.name == tool_name,
            )
        )
        if builtin.scalar_one_or_none():
            raise HTTPException(
                status_code=403,
                detail="Cannot delete built-in tools"
            )
        raise HTTPException(status_code=404, detail="Tool not found")

    # tz-aware UTC to match the DateTime(timezone=True) column on Tool.
    tool.deleted_at = datetime.now(UTC)
    tool.is_active = False
    await session.commit()

    return {"success": True, "message": f"Tool '{tool_name}' deleted"}
