"""Telemetry and observability for FlowForge."""

from flowforge_server.telemetry.metrics import (
    metrics_router,
    track_queue_size,
    track_request,
    track_run_completed,
    track_run_failed,
    track_run_started,
)
from flowforge_server.telemetry.tracing import (
    OTEL_AVAILABLE,
    add_span_attributes,
    create_span,
    get_span_id,
    get_trace_id,
    init_tracing,
    instrument_app,
    instrument_httpx,
    instrument_redis,
    instrument_sqlalchemy,
    record_exception,
    set_span_status,
)

__all__ = [
    # Metrics
    "metrics_router",
    "track_request",
    "track_run_started",
    "track_run_completed",
    "track_run_failed",
    "track_queue_size",
    # Tracing
    "init_tracing",
    "instrument_app",
    "instrument_sqlalchemy",
    "instrument_redis",
    "instrument_httpx",
    "create_span",
    "add_span_attributes",
    "record_exception",
    "set_span_status",
    "get_trace_id",
    "get_span_id",
    "OTEL_AVAILABLE",
]
