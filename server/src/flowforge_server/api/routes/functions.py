"""Function registration and management endpoints."""

import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.api.schemas.functions import (
    FunctionCreate,
    FunctionResponse,
    FunctionsResponse,
    FunctionUpdate,
    InlineFunctionCreate,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import Function, Tool

router = APIRouter(prefix="/functions", tags=["functions"])


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


def fn_to_response(fn: Function) -> FunctionResponse:
    """Convert Function model to response schema."""
    return FunctionResponse(
        id=str(fn.id),
        function_id=fn.function_id,
        name=fn.name,
        trigger_type=fn.trigger_type,
        trigger_value=fn.trigger_value,
        trigger_expression=fn.trigger_expression,
        endpoint_url=fn.endpoint_url,
        is_inline=fn.is_inline,
        system_prompt=fn.system_prompt,
        tools_config=fn.tools_config,
        agent_config=fn.agent_config,
        config=fn.config,
        is_active=fn.is_active,
        created_at=fn.created_at,
        updated_at=fn.updated_at,
    )


@router.post("", response_model=FunctionResponse, status_code=201)
async def register_function(
    function_data: FunctionCreate,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> FunctionResponse:
    """
    Register a new function (worker mode).

    Functions define how workflows are triggered and configured.
    The SDK automatically registers functions on startup.

    For serverless/inline functions, use POST /functions/inline instead.
    """
    # Check for existing function with same ID
    existing = await session.execute(
        select(Function).where(
            Function.tenant_id == tenant.id,
            Function.function_id == function_data.id,
        )
    )
    existing_fn = existing.scalar_one_or_none()

    if existing_fn:
        # Re-registering an id restores a soft-deleted row.
        existing_fn.deleted_at = None
        existing_fn.name = function_data.name
        existing_fn.slug = slugify(function_data.name)
        existing_fn.trigger_type = function_data.trigger.type
        existing_fn.trigger_value = function_data.trigger.value
        existing_fn.trigger_expression = function_data.trigger.expression
        existing_fn.endpoint_url = function_data.endpoint_url
        existing_fn.config = function_data.config
        existing_fn.is_active = True
        existing_fn.is_inline = False  # Worker mode

        await session.commit()
        await session.refresh(existing_fn)
        fn = existing_fn
    else:
        # Create new function
        fn = Function(
            tenant_id=tenant.id,
            function_id=function_data.id,
            name=function_data.name,
            slug=slugify(function_data.name),
            trigger_type=function_data.trigger.type,
            trigger_value=function_data.trigger.value,
            trigger_expression=function_data.trigger.expression,
            endpoint_url=function_data.endpoint_url,
            config=function_data.config,
            is_active=True,
            is_inline=False,  # Worker mode
        )

        session.add(fn)
        await session.commit()
        await session.refresh(fn)

    return fn_to_response(fn)


@router.post("/inline", response_model=FunctionResponse, status_code=201)
async def create_inline_function(
    function_data: InlineFunctionCreate,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> FunctionResponse:
    """
    Create an inline/serverless function.

    Inline functions are executed directly by FlowForge without requiring
    an external worker. They use an agent-based architecture with:
    - A system prompt to define behavior
    - A list of tools the agent can use
    - Configuration for the AI model and execution limits
    """
    # Check for existing function with same ID. A soft-deleted row holds the
    # unique-constraint slot, so we restore it instead of hitting IntegrityError.
    existing = await session.execute(
        select(Function).where(
            Function.tenant_id == tenant.id,
            Function.function_id == function_data.id,
        )
    )
    existing_fn = existing.scalar_one_or_none()
    if existing_fn and existing_fn.deleted_at is None:
        raise HTTPException(
            status_code=409,
            detail=f"Function with ID '{function_data.id}' already exists"
        )

    # Validate that all tools exist
    for tool_name in function_data.tools:
        tool_result = await session.execute(
            select(Tool).where(
                or_(
                    (Tool.tenant_id == tenant.id) & (Tool.name == tool_name),
                    (Tool.is_builtin == True) & (Tool.name == tool_name),
                )
            )
        )
        if not tool_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Tool '{tool_name}' not found. Create it first via POST /tools"
            )

    if existing_fn and existing_fn.deleted_at is not None:
        # Restore and overwrite the soft-deleted row.
        existing_fn.deleted_at = None
        existing_fn.name = function_data.name
        existing_fn.slug = slugify(function_data.name)
        existing_fn.trigger_type = function_data.trigger.type
        existing_fn.trigger_value = function_data.trigger.value
        existing_fn.trigger_expression = function_data.trigger.expression
        existing_fn.endpoint_url = None
        existing_fn.is_inline = True
        existing_fn.system_prompt = function_data.system_prompt
        existing_fn.tools_config = function_data.tools
        existing_fn.agent_config = function_data.agent_config.model_dump()
        existing_fn.config = function_data.config
        existing_fn.is_active = True
        fn = existing_fn
    else:
        fn = Function(
            tenant_id=tenant.id,
            function_id=function_data.id,
            name=function_data.name,
            slug=slugify(function_data.name),
            trigger_type=function_data.trigger.type,
            trigger_value=function_data.trigger.value,
            trigger_expression=function_data.trigger.expression,
            endpoint_url=None,  # No endpoint for inline functions
            is_inline=True,
            system_prompt=function_data.system_prompt,
            tools_config=function_data.tools,
            agent_config=function_data.agent_config.model_dump(),
            config=function_data.config,
            is_active=True,
        )
        session.add(fn)

    await session.commit()
    await session.refresh(fn)

    return fn_to_response(fn)


@router.get("", response_model=FunctionsResponse)
async def list_functions(
    tenant: TenantWithDevFallback,
    trigger_type: str | None = Query(None, description="Filter by trigger type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    is_inline: bool | None = Query(None, description="Filter by inline/worker mode"),
    session: AsyncSession = Depends(get_session),
) -> FunctionsResponse:
    """List all registered functions."""
    query = select(Function).where(
        Function.tenant_id == tenant.id,
        Function.deleted_at.is_(None),
    )

    if trigger_type:
        query = query.where(Function.trigger_type == trigger_type)
    if is_active is not None:
        query = query.where(Function.is_active == is_active)
    if is_inline is not None:
        query = query.where(Function.is_inline == is_inline)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Get results
    query = query.order_by(Function.created_at.desc())
    result = await session.execute(query)
    functions = result.scalars().all()

    return FunctionsResponse(
        functions=[fn_to_response(fn) for fn in functions],
        total=total,
    )


@router.get("/{function_id}", response_model=FunctionResponse)
async def get_function(
    function_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> FunctionResponse:
    """Get a specific function by ID."""
    result = await session.execute(
        select(Function).where(
            Function.tenant_id == tenant.id,
            Function.function_id == function_id,
            Function.deleted_at.is_(None),
        )
    )
    fn = result.scalar_one_or_none()

    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")

    return fn_to_response(fn)


@router.patch("/{function_id}", response_model=FunctionResponse)
async def update_function(
    function_id: str,
    update_data: FunctionUpdate,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> FunctionResponse:
    """Update a function's configuration."""
    result = await session.execute(
        select(Function).where(
            Function.tenant_id == tenant.id,
            Function.function_id == function_id,
            Function.deleted_at.is_(None),
        )
    )
    fn = result.scalar_one_or_none()

    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")

    if update_data.name is not None:
        fn.name = update_data.name
        fn.slug = slugify(update_data.name)
    if update_data.endpoint_url is not None:
        fn.endpoint_url = update_data.endpoint_url
    if update_data.config is not None:
        fn.config = {**fn.config, **update_data.config}
    if update_data.is_active is not None:
        fn.is_active = update_data.is_active

    # Inline function specific updates
    if fn.is_inline:
        if update_data.system_prompt is not None:
            fn.system_prompt = update_data.system_prompt
        if update_data.tools is not None:
            # Validate tools exist
            for tool_name in update_data.tools:
                tool_result = await session.execute(
                    select(Tool).where(
                        or_(
                            (Tool.tenant_id == tenant.id) & (Tool.name == tool_name),
                            (Tool.is_builtin == True) & (Tool.name == tool_name),
                        )
                    )
                )
                if not tool_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Tool '{tool_name}' not found"
                    )
            fn.tools_config = update_data.tools
        if update_data.agent_config is not None:
            fn.agent_config = {
                **(fn.agent_config or {}),
                **update_data.agent_config.model_dump(exclude_unset=True),
            }

    await session.commit()
    await session.refresh(fn)

    return fn_to_response(fn)


@router.delete("/{function_id}")
async def delete_function(
    function_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Soft-delete a function.

    The row is retained so existing runs and versions stay linked and the
    run history UI can still resolve the function name. It is excluded from
    all user-facing list/get queries and from event matching (via is_active).
    Re-registering the same function_id restores the row.
    """
    result = await session.execute(
        select(Function).where(
            Function.tenant_id == tenant.id,
            Function.function_id == function_id,
            Function.deleted_at.is_(None),
        )
    )
    fn = result.scalar_one_or_none()

    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")

    # tz-aware UTC to match the DateTime(timezone=True) column on Function.
    fn.deleted_at = datetime.now(timezone.utc)
    fn.is_active = False  # Stop matching new events immediately
    await session.commit()

    return {"success": True, "message": f"Function '{function_id}' deleted"}


@router.post("/heartbeat")
async def worker_heartbeat(
    function_ids: list[str],
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Worker heartbeat endpoint.

    Workers should call this periodically to indicate they are still alive.
    Updates worker_last_seen for all registered functions.

    Args:
        function_ids: List of function IDs this worker is serving.

    Returns:
        Status with count of updated functions.
    """
    now = datetime.utcnow()
    updated_count = 0

    for function_id in function_ids:
        result = await session.execute(
            select(Function).where(
                Function.tenant_id == tenant.id,
                Function.function_id == function_id,
                Function.is_active == True,
            )
        )
        fn = result.scalar_one_or_none()
        if fn:
            fn.worker_last_seen = now
            updated_count += 1

    await session.commit()

    return {
        "status": "ok",
        "updated": updated_count,
        "timestamp": now.isoformat() + "Z",
    }


@router.put("/{function_id}/skills")
async def set_function_skills(
    function_id: str,
    skill_ids: list[str],
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Set the enabled skills for a function.

    Skills are loaded at runtime and their instructions are injected
    into the agent's system prompt. Pass an empty list to disable all skills.
    """
    result = await session.execute(
        select(Function).where(
            Function.tenant_id == tenant.id,
            Function.function_id == function_id,
            Function.deleted_at.is_(None),
        )
    )
    fn = result.scalar_one_or_none()

    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")

    fn.enabled_skills = skill_ids
    await session.commit()

    return {
        "function_id": function_id,
        "enabled_skills": skill_ids,
        "message": f"Updated to {len(skill_ids)} enabled skill(s)",
    }


@router.get("/{function_id}/skills")
async def get_function_skills(
    function_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get the enabled skills for a function."""
    result = await session.execute(
        select(Function).where(
            Function.tenant_id == tenant.id,
            Function.function_id == function_id,
            Function.deleted_at.is_(None),
        )
    )
    fn = result.scalar_one_or_none()

    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")

    return {
        "function_id": function_id,
        "enabled_skills": fn.enabled_skills or [],
    }
