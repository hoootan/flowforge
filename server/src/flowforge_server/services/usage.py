"""Usage tracking service for AI calls.

This module provides functionality for recording and querying
AI usage statistics per tenant.
"""

from datetime import datetime, timedelta
from typing import Any
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models import UsageRecord
from flowforge_server.logging import Loggers

log = Loggers.ai()


class UsageTracker:
    """
    Service for tracking and querying AI usage.

    Records all AI calls with token counts, costs, and metadata.
    Provides aggregation queries for billing and analytics.
    """

    async def record_usage(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        latency_ms: int = 0,
        run_id: uuid.UUID | None = None,
        request_type: str = "completion",
        extra_data: dict[str, Any] | None = None,
    ) -> UsageRecord:
        """
        Record an AI usage event.

        Args:
            session: Database session
            tenant_id: Tenant UUID
            model: Model name (e.g., "gpt-5")
            provider: Provider name (e.g., "openai")
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            cost_usd: Estimated cost in USD
            latency_ms: Request latency in milliseconds
            run_id: Optional run UUID
            request_type: Type of request (completion, streaming, tool_call)
            extra_data: Additional context data

        Returns:
            The created UsageRecord
        """
        record = UsageRecord(
            tenant_id=tenant_id,
            run_id=run_id,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            request_type=request_type,
            extra_data=extra_data or {},
            requested_at=datetime.utcnow(),
        )
        session.add(record)
        await session.flush()

        log.debug(
            "usage_recorded",
            tenant_id=str(tenant_id),
            model=model,
            tokens=record.total_tokens,
            cost_usd=cost_usd,
        )

        return record

    async def get_usage_stats(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get aggregated usage statistics for a tenant.

        Args:
            session: Database session
            tenant_id: Tenant UUID
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            Dictionary with usage statistics
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow()

        # Base query
        base_filter = [
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.requested_at >= start_date,
            UsageRecord.requested_at <= end_date,
        ]

        # Total aggregates
        totals_query = select(
            func.count(UsageRecord.id).label("total_requests"),
            func.sum(UsageRecord.prompt_tokens).label("total_prompt_tokens"),
            func.sum(UsageRecord.completion_tokens).label("total_completion_tokens"),
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.sum(UsageRecord.cost_usd).label("total_cost_usd"),
            func.avg(UsageRecord.latency_ms).label("avg_latency_ms"),
        ).where(*base_filter)

        totals_result = await session.execute(totals_query)
        totals = totals_result.one()

        # By model aggregates
        by_model_query = (
            select(
                UsageRecord.model,
                func.count(UsageRecord.id).label("requests"),
                func.sum(UsageRecord.total_tokens).label("tokens"),
                func.sum(UsageRecord.cost_usd).label("cost_usd"),
            )
            .where(*base_filter)
            .group_by(UsageRecord.model)
            .order_by(func.sum(UsageRecord.cost_usd).desc())
        )

        by_model_result = await session.execute(by_model_query)
        by_model = {
            row.model: {
                "requests": row.requests,
                "tokens": row.tokens or 0,
                "cost_usd": float(row.cost_usd or 0),
            }
            for row in by_model_result
        }

        # By day aggregates (for charts)
        by_day_query = (
            select(
                func.date_trunc("day", UsageRecord.requested_at).label("date"),
                func.count(UsageRecord.id).label("requests"),
                func.sum(UsageRecord.total_tokens).label("tokens"),
                func.sum(UsageRecord.cost_usd).label("cost_usd"),
            )
            .where(*base_filter)
            .group_by(func.date_trunc("day", UsageRecord.requested_at))
            .order_by(func.date_trunc("day", UsageRecord.requested_at))
        )

        by_day_result = await session.execute(by_day_query)
        by_day = [
            {
                "date": row.date.isoformat() if row.date else None,
                "requests": row.requests,
                "tokens": row.tokens or 0,
                "cost_usd": float(row.cost_usd or 0),
            }
            for row in by_day_result
        ]

        return {
            "tenant_id": str(tenant_id),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "totals": {
                "requests": totals.total_requests or 0,
                "prompt_tokens": totals.total_prompt_tokens or 0,
                "completion_tokens": totals.total_completion_tokens or 0,
                "total_tokens": totals.total_tokens or 0,
                "cost_usd": float(totals.total_cost_usd or 0),
                "avg_latency_ms": float(totals.avg_latency_ms or 0),
            },
            "by_model": by_model,
            "by_day": by_day,
        }

    async def get_run_usage(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Get usage statistics for a specific run.

        Args:
            session: Database session
            run_id: Run UUID

        Returns:
            Dictionary with run usage statistics
        """
        query = select(
            func.count(UsageRecord.id).label("requests"),
            func.sum(UsageRecord.prompt_tokens).label("prompt_tokens"),
            func.sum(UsageRecord.completion_tokens).label("completion_tokens"),
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.sum(UsageRecord.cost_usd).label("cost_usd"),
            func.sum(UsageRecord.latency_ms).label("total_latency_ms"),
        ).where(UsageRecord.run_id == run_id)

        result = await session.execute(query)
        row = result.one()

        return {
            "run_id": str(run_id),
            "requests": row.requests or 0,
            "prompt_tokens": row.prompt_tokens or 0,
            "completion_tokens": row.completion_tokens or 0,
            "total_tokens": row.total_tokens or 0,
            "cost_usd": float(row.cost_usd or 0),
            "total_latency_ms": row.total_latency_ms or 0,
        }


# Global instance
_usage_tracker: UsageTracker | None = None


def get_usage_tracker() -> UsageTracker:
    """Get the global usage tracker instance."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker
