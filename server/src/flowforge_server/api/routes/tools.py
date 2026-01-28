"""Tool management endpoints."""

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db import get_session
from flowforge_server.db.models import Tool, Tenant
from flowforge_server.api.schemas.tools import (
    ToolCreate,
    ToolResponse,
    ToolUpdate,
    ToolsResponse,
)
from flowforge_server.api.deps import TenantWithDevFallback

router = APIRouter(prefix="/tools", tags=["tools"])


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
    # Check for existing tool with same name
    existing = await session.execute(
        select(Tool).where(
            Tool.tenant_id == tenant.id,
            Tool.name == tool_data.name,
        )
    )
    if existing.scalar_one_or_none():
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

    tool = Tool(
        tenant_id=tenant.id,
        name=tool_data.name,
        description=tool_data.description,
        parameters=tool_data.parameters,
        code=tool_data.code,
        is_builtin=False,
        requires_approval=tool_data.requires_approval,
        approval_timeout=tool_data.approval_timeout,
        is_active=True,
    )

    session.add(tool)
    await session.commit()
    await session.refresh(tool)

    return ToolResponse(
        id=str(tool.id),
        name=tool.name,
        description=tool.description,
        parameters=tool.parameters,
        code=tool.code,
        is_builtin=tool.is_builtin,
        requires_approval=tool.requires_approval,
        approval_timeout=tool.approval_timeout,
        is_active=tool.is_active,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


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
            )
        )
    else:
        query = select(Tool).where(Tool.tenant_id == tenant.id)

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
        tools=[
            ToolResponse(
                id=str(tool.id),
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
                code=tool.code if not tool.is_builtin else None,  # Hide built-in code
                is_builtin=tool.is_builtin,
                requires_approval=tool.requires_approval,
                approval_timeout=tool.approval_timeout,
                is_active=tool.is_active,
                created_at=tool.created_at,
                updated_at=tool.updated_at,
            )
            for tool in tools
        ],
        total=total,
    )


@router.get("/{tool_name}", response_model=ToolResponse)
async def get_tool(
    tool_name: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    """Get a specific tool by name."""
    # Look for tenant tool first, then built-in
    result = await session.execute(
        select(Tool).where(
            or_(
                (Tool.tenant_id == tenant.id) & (Tool.name == tool_name),
                (Tool.is_builtin == True) & (Tool.name == tool_name),
            )
        ).order_by(Tool.is_builtin)  # Prefer tenant tools over built-in
    )
    tool = result.scalars().first()

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    return ToolResponse(
        id=str(tool.id),
        name=tool.name,
        description=tool.description,
        parameters=tool.parameters,
        code=tool.code if not tool.is_builtin else None,
        is_builtin=tool.is_builtin,
        requires_approval=tool.requires_approval,
        approval_timeout=tool.approval_timeout,
        is_active=tool.is_active,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


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
    if update_data.code is not None:
        tool.code = update_data.code
    if update_data.requires_approval is not None:
        tool.requires_approval = update_data.requires_approval
    if update_data.approval_timeout is not None:
        tool.approval_timeout = update_data.approval_timeout
    if update_data.is_active is not None:
        tool.is_active = update_data.is_active

    await session.commit()
    await session.refresh(tool)

    return ToolResponse(
        id=str(tool.id),
        name=tool.name,
        description=tool.description,
        parameters=tool.parameters,
        code=tool.code,
        is_builtin=tool.is_builtin,
        requires_approval=tool.requires_approval,
        approval_timeout=tool.approval_timeout,
        is_active=tool.is_active,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


@router.delete("/{tool_name}", status_code=204)
async def delete_tool(
    tool_name: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a tool (soft delete by setting inactive). Built-in tools cannot be deleted."""
    result = await session.execute(
        select(Tool).where(
            Tool.tenant_id == tenant.id,
            Tool.name == tool_name,
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

    tool.is_active = False
    await session.commit()
