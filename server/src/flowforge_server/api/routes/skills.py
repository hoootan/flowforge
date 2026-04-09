"""Skill template library + marketplace endpoints."""

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.db import get_session
from flowforge_server.db.models import SkillTemplate
from flowforge_server.services.skill_marketplace import (
    fetch_skill_md,
    search_skills_sh,
)

router = APIRouter(prefix="/skills", tags=["skills"])


# ── Schemas ────────────────────────────────────────────────────────

class CreateSkillRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    function_config: dict = Field(default_factory=dict)
    tools_config: list[dict] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class UpdateSkillRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    function_config: dict | None = None
    tools_config: list[dict] | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class ImportSkillRequest(BaseModel):
    repo: str = Field(..., min_length=3, description="GitHub owner/repo")
    path: str = Field(default="SKILL.md")
    source: str = Field(default="skills_sh", description="skills_sh or github")
    external_id: str | None = None
    name_override: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class SkillResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    category: str | None
    icon: str | None
    version: int
    function_config: dict
    tools_config: list | dict
    usage_count: int
    is_builtin: bool
    is_active: bool
    tags: list | dict
    source: str
    instructions: str | None
    source_metadata: dict | None
    created_by_user_id: str | None
    created_at: str | None
    updated_at: str | None


class SkillsListResponse(BaseModel):
    skills: list[SkillResponse]
    total: int


class MarketplaceSearchResult(BaseModel):
    external_id: str
    name: str
    description: str
    source: str
    repo: str
    install_count: int
    preview_url: str | None


class MarketplaceSearchResponse(BaseModel):
    results: list[MarketplaceSearchResult]
    total: int


class SkillPreviewResponse(BaseModel):
    name: str
    description: str
    raw_content: str
    frontmatter: dict
    body: str
    repo: str
    path: str


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# ── Local Skill CRUD ───────────────────────────────────────────────

@router.get("", response_model=SkillsListResponse)
async def list_skills(
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
    category: str | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    source: str | None = Query(None, description="Filter by source: local, skills_sh, github, external"),
) -> SkillsListResponse:
    """List available skill templates."""
    query = select(SkillTemplate).where(
        (SkillTemplate.tenant_id == tenant.id) | (SkillTemplate.is_builtin == True)
    )

    if category:
        query = query.where(SkillTemplate.category == category)
    if is_active is not None:
        query = query.where(SkillTemplate.is_active == is_active)
    if search:
        query = query.where(SkillTemplate.name.ilike(f"%{search}%"))
    if source:
        if source == "external":
            query = query.where(SkillTemplate.source.in_(["skills_sh", "github"]))
        else:
            query = query.where(SkillTemplate.source == source)

    query = query.order_by(SkillTemplate.usage_count.desc(), SkillTemplate.name)
    result = await session.execute(query)
    skills = result.scalars().all()

    return SkillsListResponse(
        skills=[SkillResponse(**s.to_dict()) for s in skills],
        total=len(skills),
    )


@router.post("", response_model=SkillResponse, status_code=201)
async def create_skill(
    data: CreateSkillRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    """Create a new skill template."""
    slug = _slugify(data.name)

    existing = await session.execute(
        select(SkillTemplate).where(
            SkillTemplate.tenant_id == tenant.id,
            SkillTemplate.slug == slug,
        )
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    skill = SkillTemplate(
        tenant_id=tenant.id,
        name=data.name,
        slug=slug,
        description=data.description,
        category=data.category,
        icon=data.icon,
        function_config=data.function_config,
        tools_config=data.tools_config,
        tags=data.tags,
        source="local",
    )

    session.add(skill)
    await session.commit()
    await session.refresh(skill)

    return SkillResponse(**skill.to_dict())


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    """Get skill template details."""
    try:
        skill_uuid = uuid.UUID(skill_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid skill ID")

    result = await session.execute(
        select(SkillTemplate).where(
            SkillTemplate.id == skill_uuid,
            (SkillTemplate.tenant_id == tenant.id) | (SkillTemplate.is_builtin == True),
        )
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    return SkillResponse(**skill.to_dict())


@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    data: UpdateSkillRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    """Update a skill template (bumps version)."""
    try:
        skill_uuid = uuid.UUID(skill_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid skill ID")

    result = await session.execute(
        select(SkillTemplate).where(
            SkillTemplate.id == skill_uuid,
            SkillTemplate.tenant_id == tenant.id,
        )
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    update_data = data.model_dump(exclude_unset=True)

    if "function_config" in update_data or "tools_config" in update_data:
        skill.version += 1

    for key, value in update_data.items():
        setattr(skill, key, value)

    await session.commit()
    await session.refresh(skill)

    return SkillResponse(**skill.to_dict())


@router.post("/{skill_id}/use")
async def use_skill(
    skill_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Instantiate a skill template — returns config + instructions for function creation."""
    try:
        skill_uuid = uuid.UUID(skill_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid skill ID")

    result = await session.execute(
        select(SkillTemplate).where(
            SkillTemplate.id == skill_uuid,
            (SkillTemplate.tenant_id == tenant.id) | (SkillTemplate.is_builtin == True),
        )
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill.usage_count += 1
    await session.commit()

    response: dict = {
        "skill_id": str(skill.id),
        "skill_name": skill.name,
        "function_config": skill.function_config,
        "tools_config": skill.tools_config,
        "message": "Use this configuration to create a new function with the provided tools.",
    }

    # Include instructions for imported skills (knowledge payload)
    # Note: Skills are NOT baked into system prompts. Instead, enable them
    # on a function/agent via enabled_skills[] and they inject at runtime.
    if skill.instructions:
        response["instructions"] = skill.instructions
        response["has_instructions"] = True

    return response


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a skill template."""
    try:
        skill_uuid = uuid.UUID(skill_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid skill ID")

    result = await session.execute(
        select(SkillTemplate).where(
            SkillTemplate.id == skill_uuid,
            SkillTemplate.tenant_id == tenant.id,
            SkillTemplate.is_builtin == False,
        )
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found or is built-in")

    await session.delete(skill)
    await session.commit()


# ── Marketplace Endpoints ──────────────────────────────────────────

@router.get("/marketplace/search", response_model=MarketplaceSearchResponse)
async def marketplace_search(
    tenant: TenantWithDevFallback,
    q: str = Query(..., min_length=1, description="Search query"),
    source: str = Query("skills_sh", description="skills_sh or github"),
    limit: int = Query(10, ge=1, le=50),
) -> MarketplaceSearchResponse:
    """Search external skill marketplaces (skills.sh)."""
    if source == "skills_sh":
        results = await search_skills_sh(q, limit=limit)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")

    return MarketplaceSearchResponse(
        results=[MarketplaceSearchResult(**r) for r in results],
        total=len(results),
    )


@router.get("/marketplace/preview", response_model=SkillPreviewResponse)
async def marketplace_preview(
    tenant: TenantWithDevFallback,
    repo: str = Query(..., description="GitHub owner/repo"),
    path: str = Query("SKILL.md"),
) -> SkillPreviewResponse:
    """Fetch and preview a SKILL.md file from GitHub."""
    data = await fetch_skill_md(repo, path)

    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"SKILL.md not found at {repo}/{path}",
        )

    return SkillPreviewResponse(**data)


@router.post("/marketplace/import", response_model=SkillResponse, status_code=201)
async def marketplace_import(
    data: ImportSkillRequest,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    """Import a skill from an external marketplace into the local skill library."""
    # Fetch the SKILL.md
    skill_data = await fetch_skill_md(data.repo, data.path)

    if not skill_data:
        raise HTTPException(
            status_code=404,
            detail=f"SKILL.md not found at {data.repo}/{data.path}",
        )

    # Determine name
    name = data.name_override or skill_data["name"] or data.repo.split("/")[-1]
    slug = _slugify(name)

    # Handle slug collision
    existing = await session.execute(
        select(SkillTemplate).where(
            SkillTemplate.tenant_id == tenant.id,
            SkillTemplate.slug == slug,
        )
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    # Build source metadata
    source_metadata = {
        "repo": data.repo,
        "path": data.path,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "external_id": data.external_id,
        "frontmatter": skill_data["frontmatter"],
    }

    skill = SkillTemplate(
        tenant_id=tenant.id,
        name=name,
        slug=slug,
        description=skill_data["description"] or skill_data["frontmatter"].get("description"),
        category=data.category or skill_data["frontmatter"].get("category"),
        icon=skill_data["frontmatter"].get("icon"),
        source=data.source,
        instructions=skill_data["body"],
        source_metadata=source_metadata,
        function_config={},
        tools_config=[],
        tags=data.tags or [],
    )

    session.add(skill)
    await session.commit()
    await session.refresh(skill)

    return SkillResponse(**skill.to_dict())


@router.post("/{skill_id}/refresh", response_model=SkillResponse)
async def refresh_skill(
    skill_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> SkillResponse:
    """Re-fetch SKILL.md from the source repo and update instructions."""
    try:
        skill_uuid = uuid.UUID(skill_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid skill ID")

    result = await session.execute(
        select(SkillTemplate).where(
            SkillTemplate.id == skill_uuid,
            SkillTemplate.tenant_id == tenant.id,
        )
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if skill.source == "local":
        raise HTTPException(status_code=400, detail="Local skills cannot be refreshed from external source")

    meta = skill.source_metadata or {}
    repo = meta.get("repo")
    path = meta.get("path", "SKILL.md")

    if not repo:
        raise HTTPException(status_code=400, detail="No source repository configured")

    # Fetch fresh content
    skill_data = await fetch_skill_md(repo, path)

    if not skill_data:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch SKILL.md from {repo}/{path}",
        )

    # Update
    skill.instructions = skill_data["body"]
    skill.description = skill_data["description"] or skill.description
    skill.version += 1
    meta["fetched_at"] = datetime.now(timezone.utc).isoformat()
    meta["frontmatter"] = skill_data["frontmatter"]
    skill.source_metadata = meta

    await session.commit()
    await session.refresh(skill)

    return SkillResponse(**skill.to_dict())
