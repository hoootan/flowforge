"""Agent management endpoints."""

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.db import get_session
from flowforge_server.db.models import Agent, AgentStatus

router = APIRouter(prefix="/agents", tags=["agents"])


# --- Schemas ---

class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    avatar_url: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    capabilities: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    avatar_url: str | None = None
    status: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    capabilities: dict | None = None
    config: dict | None = None
    is_active: bool | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    slug: str
    avatar_url: str | None
    description: str | None
    status: str
    model: str | None
    system_prompt: str | None
    capabilities: dict
    config: dict
    stats: dict
    is_active: bool
    created_at: str | None
    updated_at: str | None


class AgentsListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


def _slugify(name: str) -> str:
    """Convert name to URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# --- Endpoints ---

@router.get("", response_model=AgentsListResponse)
async def list_agents(
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
    status: str | None = Query(None),
    is_active: bool | None = Query(None),
) -> AgentsListResponse:
    """List all agents for the tenant."""
    query = select(Agent).where(Agent.tenant_id == tenant.id)

    if status:
        query = query.where(Agent.status == status)
    if is_active is not None:
        query = query.where(Agent.is_active == is_active)

    query = query.order_by(Agent.created_at.desc())
    result = await session.execute(query)
    agents = result.scalars().all()

    return AgentsListResponse(
        agents=[AgentResponse(**a.to_dict()) for a in agents],
        total=len(agents),
    )


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    data: CreateAgentRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> AgentResponse:
    """Create a new agent."""
    slug = _slugify(data.name)

    # Check for duplicate slug
    existing = await session.execute(
        select(Agent).where(Agent.tenant_id == tenant.id, Agent.slug == slug)
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    agent = Agent(
        tenant_id=tenant.id,
        name=data.name,
        slug=slug,
        description=data.description,
        avatar_url=data.avatar_url,
        model=data.model,
        system_prompt=data.system_prompt,
        capabilities=data.capabilities,
        config=data.config,
        status=AgentStatus.IDLE.value,
    )

    session.add(agent)
    await session.commit()
    await session.refresh(agent)

    return AgentResponse(**agent.to_dict())


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> AgentResponse:
    """Get agent details with live stats."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    result = await session.execute(
        select(Agent).where(Agent.id == agent_uuid, Agent.tenant_id == tenant.id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(**agent.to_dict())


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: UpdateAgentRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> AgentResponse:
    """Update an agent."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    result = await session.execute(
        select(Agent).where(Agent.id == agent_uuid, Agent.tenant_id == tenant.id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    await session.commit()
    await session.refresh(agent)

    return AgentResponse(**agent.to_dict())


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an agent."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    result = await session.execute(
        select(Agent).where(Agent.id == agent_uuid, Agent.tenant_id == tenant.id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await session.delete(agent)
    await session.commit()


@router.get("/{agent_id}/stats")
async def get_agent_stats(
    agent_id: str,
    tenant: TenantWithDevFallback,
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get detailed performance stats for an agent."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    # Verify agent exists
    result = await session.execute(
        select(Agent).where(Agent.id == agent_uuid, Agent.tenant_id == tenant.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # For now, return placeholder stats
    # In a full implementation, we'd query runs linked to this agent
    return {
        "agent_id": agent_id,
        "total_runs": 0,
        "completed_runs": 0,
        "failed_runs": 0,
        "success_rate": 0.0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "avg_duration_ms": 0.0,
        "period_days": days,
    }


@router.put("/{agent_id}/skills")
async def set_agent_skills(
    agent_id: str,
    skill_ids: list[str],
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Set the enabled skills for an agent.

    Skills provide knowledge context that is injected at runtime.
    Pass an empty list to disable all skills.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    result = await session.execute(
        select(Agent).where(Agent.id == agent_uuid, Agent.tenant_id == tenant.id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.enabled_skills = skill_ids
    await session.commit()

    return {
        "agent_id": agent_id,
        "enabled_skills": skill_ids,
        "message": f"Updated to {len(skill_ids)} enabled skill(s)",
    }


@router.get("/{agent_id}/skills")
async def get_agent_skills(
    agent_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get the enabled skills for an agent."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    result = await session.execute(
        select(Agent).where(Agent.id == agent_uuid, Agent.tenant_id == tenant.id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "agent_id": agent_id,
        "enabled_skills": agent.enabled_skills or [],
    }
