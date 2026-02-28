"""Usage statistics endpoints."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.api.schemas.usage import (
    DailyUsage,
    DailyUsageResponse,
    RunUsageResponse,
    UsageByModel,
    UsageByModelResponse,
    UsageByProvider,
    UsageByProviderResponse,
    UsageSummary,
    UsageSummaryResponse,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import Run, UsageRecord

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    tenant: TenantWithDevFallback,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    session: AsyncSession = Depends(get_session),
) -> UsageSummaryResponse:
    """
    Get aggregate usage summary for the tenant.

    Returns total requests, tokens, cost, and average latency.
    """
    period_start = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(
            func.count(UsageRecord.id).label("total_requests"),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0).label("total_cost_usd"),
            func.coalesce(func.avg(UsageRecord.latency_ms), 0.0).label("avg_latency_ms"),
        ).where(
            UsageRecord.tenant_id == tenant.id,
            UsageRecord.requested_at >= period_start,
        )
    )

    row = result.one()

    summary = UsageSummary(
        total_requests=row.total_requests or 0,
        total_tokens=int(row.total_tokens or 0),
        prompt_tokens=int(row.prompt_tokens or 0),
        completion_tokens=int(row.completion_tokens or 0),
        total_cost_usd=float(row.total_cost_usd or 0.0),
        avg_latency_ms=float(row.avg_latency_ms or 0.0),
        period_start=period_start,
        period_end=datetime.utcnow(),
    )

    return UsageSummaryResponse(summary=summary)


@router.get("/by-provider", response_model=UsageByProviderResponse)
async def get_usage_by_provider(
    tenant: TenantWithDevFallback,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    session: AsyncSession = Depends(get_session),
) -> UsageByProviderResponse:
    """
    Get usage breakdown by AI provider.
    """
    period_start = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(
            UsageRecord.provider,
            func.count(UsageRecord.id).label("requests"),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0).label("cost_usd"),
            func.coalesce(func.avg(UsageRecord.latency_ms), 0.0).label("avg_latency_ms"),
        ).where(
            UsageRecord.tenant_id == tenant.id,
            UsageRecord.requested_at >= period_start,
        ).group_by(
            UsageRecord.provider
        ).order_by(
            func.sum(UsageRecord.cost_usd).desc()
        )
    )

    providers = [
        UsageByProvider(
            provider=row.provider,
            requests=row.requests,
            total_tokens=int(row.total_tokens),
            cost_usd=float(row.cost_usd),
            avg_latency_ms=float(row.avg_latency_ms),
        )
        for row in result.all()
    ]

    return UsageByProviderResponse(providers=providers)


@router.get("/by-model", response_model=UsageByModelResponse)
async def get_usage_by_model(
    tenant: TenantWithDevFallback,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    session: AsyncSession = Depends(get_session),
) -> UsageByModelResponse:
    """
    Get usage breakdown by AI model.
    """
    period_start = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(
            UsageRecord.model,
            UsageRecord.provider,
            func.count(UsageRecord.id).label("requests"),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0).label("cost_usd"),
            func.coalesce(func.avg(UsageRecord.latency_ms), 0.0).label("avg_latency_ms"),
        ).where(
            UsageRecord.tenant_id == tenant.id,
            UsageRecord.requested_at >= period_start,
        ).group_by(
            UsageRecord.model,
            UsageRecord.provider,
        ).order_by(
            func.sum(UsageRecord.cost_usd).desc()
        )
    )

    models = [
        UsageByModel(
            model=row.model,
            provider=row.provider,
            requests=row.requests,
            total_tokens=int(row.total_tokens),
            cost_usd=float(row.cost_usd),
            avg_latency_ms=float(row.avg_latency_ms),
        )
        for row in result.all()
    ]

    return UsageByModelResponse(models=models)


@router.get("/daily", response_model=DailyUsageResponse)
async def get_daily_usage(
    tenant: TenantWithDevFallback,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    session: AsyncSession = Depends(get_session),
) -> DailyUsageResponse:
    """
    Get daily usage time series.
    """
    period_start = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(
            cast(UsageRecord.requested_at, Date).label("date"),
            func.count(UsageRecord.id).label("requests"),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0).label("cost_usd"),
        ).where(
            UsageRecord.tenant_id == tenant.id,
            UsageRecord.requested_at >= period_start,
        ).group_by(
            cast(UsageRecord.requested_at, Date)
        ).order_by(
            cast(UsageRecord.requested_at, Date)
        )
    )

    daily = [
        DailyUsage(
            date=str(row.date),
            requests=row.requests,
            total_tokens=int(row.total_tokens),
            cost_usd=float(row.cost_usd),
        )
        for row in result.all()
    ]

    return DailyUsageResponse(daily=daily)


@router.get("/runs/{run_id}", response_model=RunUsageResponse)
async def get_run_usage(
    run_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> RunUsageResponse:
    """
    Get usage breakdown for a specific run.
    """
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")

    # Verify run exists and belongs to tenant
    run_result = await session.execute(
        select(Run).where(
            Run.id == run_uuid,
            Run.tenant_id == tenant.id,
        )
    )
    run = run_result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get usage records for this run
    result = await session.execute(
        select(UsageRecord).where(
            UsageRecord.run_id == run_uuid,
        ).order_by(UsageRecord.requested_at)
    )

    records = result.scalars().all()

    # Calculate totals
    total_requests = len(records)
    total_tokens = sum(r.total_tokens for r in records)
    total_cost_usd = sum(r.cost_usd for r in records)

    # Build step breakdown
    by_step = []
    for record in records:
        step_info = {
            "step_id": record.extra_data.get("step_id") if record.extra_data else None,
            "model": record.model,
            "provider": record.provider,
            "tokens": record.total_tokens,
            "cost_usd": record.cost_usd,
            "latency_ms": record.latency_ms,
            "requested_at": record.requested_at.isoformat(),
        }
        by_step.append(step_info)

    return RunUsageResponse(
        run_id=run_id,
        total_requests=total_requests,
        total_tokens=total_tokens,
        total_cost_usd=total_cost_usd,
        by_step=by_step,
    )
