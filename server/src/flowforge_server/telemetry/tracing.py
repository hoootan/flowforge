"""OpenTelemetry distributed tracing for FlowForge.

Provides request tracing across services for debugging and performance analysis.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from flowforge_server.config import get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

# Check if OpenTelemetry is available
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import Span, Status, StatusCode
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    Span = None


# Global tracer instance
_tracer = None


def get_tracer():
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None and OTEL_AVAILABLE:
        _tracer = trace.get_tracer("flowforge")
    return _tracer


def init_tracing(
    service_name: str = "flowforge-server",
    otlp_endpoint: str | None = None,
) -> None:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of this service for traces
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
    """
    if not OTEL_AVAILABLE:
        return

    settings = get_settings()

    # Use configured endpoint or default
    endpoint = otlp_endpoint or getattr(settings, "otlp_endpoint", None)

    if not endpoint:
        # No endpoint configured, skip initialization
        return

    # Create resource with service name
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": "0.1.0",
        "deployment.environment": settings.env,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter
    otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)

    # Set as global provider
    trace.set_tracer_provider(provider)


def instrument_app(app: FastAPI) -> None:
    """
    Instrument a FastAPI application with OpenTelemetry.

    Args:
        app: The FastAPI application to instrument
    """
    if not OTEL_AVAILABLE:
        return

    settings = get_settings()

    # Only instrument if endpoint is configured
    if not getattr(settings, "otlp_endpoint", None):
        return

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)


def instrument_sqlalchemy(engine) -> None:
    """Instrument SQLAlchemy engine."""
    if not OTEL_AVAILABLE:
        return

    settings = get_settings()
    if not getattr(settings, "otlp_endpoint", None):
        return

    SQLAlchemyInstrumentor().instrument(engine=engine)


def instrument_redis() -> None:
    """Instrument Redis client."""
    if not OTEL_AVAILABLE:
        return

    settings = get_settings()
    if not getattr(settings, "otlp_endpoint", None):
        return

    RedisInstrumentor().instrument()


def instrument_httpx() -> None:
    """Instrument HTTPX client (for AI provider calls)."""
    if not OTEL_AVAILABLE:
        return

    settings = get_settings()
    if not getattr(settings, "otlp_endpoint", None):
        return

    HTTPXClientInstrumentor().instrument()


@contextmanager
def create_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """
    Create a new span for tracing.

    Usage:
        with create_span("process_event", {"event.name": "order/created"}):
            # do work
            pass

    Args:
        name: Name of the span
        attributes: Optional attributes to add to the span

    Yields:
        The span object (or None if tracing is not available)
    """
    if not OTEL_AVAILABLE:
        yield None
        return

    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def add_span_attributes(attributes: dict[str, Any]) -> None:
    """Add attributes to the current span."""
    if not OTEL_AVAILABLE:
        return

    span = trace.get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)


def record_exception(exception: Exception) -> None:
    """Record an exception on the current span."""
    if not OTEL_AVAILABLE:
        return

    span = trace.get_current_span()
    if span:
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))


def set_span_status(success: bool, message: str = "") -> None:
    """Set the status of the current span."""
    if not OTEL_AVAILABLE:
        return

    span = trace.get_current_span()
    if span:
        if success:
            span.set_status(Status(StatusCode.OK, message))
        else:
            span.set_status(Status(StatusCode.ERROR, message))


def get_trace_id() -> str | None:
    """Get the current trace ID as a hex string."""
    if not OTEL_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return None


def get_span_id() -> str | None:
    """Get the current span ID as a hex string."""
    if not OTEL_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, "016x")
    return None
