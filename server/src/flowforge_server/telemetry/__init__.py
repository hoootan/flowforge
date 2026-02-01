"""Telemetry and observability for FlowForge."""

from flowforge_server.telemetry.metrics import (
    metrics_router,
    track_request,
    track_run_started,
    track_run_completed,
    track_run_failed,
    track_queue_size,
)
from flowforge_server.telemetry.tracing import (
    init_tracing,
    instrument_app,
    instrument_sqlalchemy,
    instrument_redis,
    instrument_httpx,
    create_span,
    add_span_attributes,
    record_exception,
    set_span_status,
    get_trace_id,
    get_span_id,
    OTEL_AVAILABLE,
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
