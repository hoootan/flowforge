"""Prometheus metrics for FlowForge.

Exposes /metrics endpoint for Prometheus scraping.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Callable, Any

from fastapi import APIRouter, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
        REGISTRY,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Create router for metrics endpoint
metrics_router = APIRouter(tags=["metrics"])


# Define metrics only if prometheus_client is available
if PROMETHEUS_AVAILABLE:
    # HTTP request metrics
    HTTP_REQUESTS_TOTAL = Counter(
        "flowforge_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )

    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        "flowforge_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    # Run metrics
    RUNS_TOTAL = Counter(
        "flowforge_runs_total",
        "Total runs by status",
        ["tenant_id", "function_id", "status"],
    )

    RUNS_IN_PROGRESS = Gauge(
        "flowforge_runs_in_progress",
        "Number of currently running runs",
        ["tenant_id"],
    )

    RUN_DURATION_SECONDS = Histogram(
        "flowforge_run_duration_seconds",
        "Run duration in seconds",
        ["tenant_id", "function_id", "status"],
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
    )

    # Queue metrics
    QUEUE_SIZE = Gauge(
        "flowforge_queue_size",
        "Number of jobs in queue",
        ["queue_type"],  # pending, running, scheduled
    )

    QUEUE_JOBS_TOTAL = Counter(
        "flowforge_queue_jobs_total",
        "Total jobs processed",
        ["status"],  # completed, failed, retried
    )

    # Step metrics
    STEPS_TOTAL = Counter(
        "flowforge_steps_total",
        "Total steps executed",
        ["step_type", "status"],  # step_type: run, sleep, ai, wait_for_event, etc.
    )

    STEP_DURATION_SECONDS = Histogram(
        "flowforge_step_duration_seconds",
        "Step duration in seconds",
        ["step_type"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    )

    # AI metrics
    AI_REQUESTS_TOTAL = Counter(
        "flowforge_ai_requests_total",
        "Total AI provider requests",
        ["provider", "model", "status"],
    )

    AI_TOKENS_TOTAL = Counter(
        "flowforge_ai_tokens_total",
        "Total AI tokens used",
        ["provider", "model", "type"],  # type: input, output
    )

    AI_REQUEST_DURATION_SECONDS = Histogram(
        "flowforge_ai_request_duration_seconds",
        "AI request duration in seconds",
        ["provider", "model"],
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    )


@metrics_router.get("/metrics")
async def get_metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    """
    if not PROMETHEUS_AVAILABLE:
        return Response(
            content="prometheus_client not installed",
            status_code=501,
            media_type="text/plain",
        )

    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


def track_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Track an HTTP request."""
    if not PROMETHEUS_AVAILABLE:
        return

    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        endpoint=endpoint,
        status=str(status),
    ).inc()

    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        endpoint=endpoint,
    ).observe(duration)


def track_run_started(tenant_id: str, function_id: str) -> None:
    """Track a run starting."""
    if not PROMETHEUS_AVAILABLE:
        return

    RUNS_TOTAL.labels(
        tenant_id=tenant_id,
        function_id=function_id,
        status="started",
    ).inc()

    RUNS_IN_PROGRESS.labels(tenant_id=tenant_id).inc()


def track_run_completed(
    tenant_id: str,
    function_id: str,
    duration: float,
    success: bool = True,
) -> None:
    """Track a run completing."""
    if not PROMETHEUS_AVAILABLE:
        return

    status = "completed" if success else "failed"

    RUNS_TOTAL.labels(
        tenant_id=tenant_id,
        function_id=function_id,
        status=status,
    ).inc()

    RUNS_IN_PROGRESS.labels(tenant_id=tenant_id).dec()

    RUN_DURATION_SECONDS.labels(
        tenant_id=tenant_id,
        function_id=function_id,
        status=status,
    ).observe(duration)


def track_run_failed(tenant_id: str, function_id: str, duration: float) -> None:
    """Track a run failing."""
    track_run_completed(tenant_id, function_id, duration, success=False)


def track_queue_size(pending: int, running: int, scheduled: int) -> None:
    """Update queue size gauges."""
    if not PROMETHEUS_AVAILABLE:
        return

    QUEUE_SIZE.labels(queue_type="pending").set(pending)
    QUEUE_SIZE.labels(queue_type="running").set(running)
    QUEUE_SIZE.labels(queue_type="scheduled").set(scheduled)


def track_step(step_type: str, status: str, duration: float) -> None:
    """Track a step execution."""
    if not PROMETHEUS_AVAILABLE:
        return

    STEPS_TOTAL.labels(step_type=step_type, status=status).inc()
    STEP_DURATION_SECONDS.labels(step_type=step_type).observe(duration)


def track_ai_request(
    provider: str,
    model: str,
    status: str,
    duration: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """Track an AI provider request."""
    if not PROMETHEUS_AVAILABLE:
        return

    AI_REQUESTS_TOTAL.labels(
        provider=provider,
        model=model,
        status=status,
    ).inc()

    AI_REQUEST_DURATION_SECONDS.labels(
        provider=provider,
        model=model,
    ).observe(duration)

    if input_tokens > 0:
        AI_TOKENS_TOTAL.labels(
            provider=provider,
            model=model,
            type="input",
        ).inc(input_tokens)

    if output_tokens > 0:
        AI_TOKENS_TOTAL.labels(
            provider=provider,
            model=model,
            type="output",
        ).inc(output_tokens)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> StarletteResponse:
        if not PROMETHEUS_AVAILABLE:
            return await call_next(request)

        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Normalize endpoint path (replace IDs with placeholders)
        endpoint = self._normalize_path(request.url.path)

        track_request(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
            duration=duration,
        )

        return response

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing UUIDs and IDs with placeholders.

        This prevents high cardinality in metrics labels.
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)

        return path


def add_metrics_middleware(app: Any) -> None:
    """Add metrics middleware to FastAPI app."""
    if PROMETHEUS_AVAILABLE:
        app.add_middleware(MetricsMiddleware)
