"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flowforge_server.api.error_handlers import register_error_handlers
from flowforge_server.api.middleware import add_api_middleware
from flowforge_server.api.routes import (
    ai_providers_router,
    approvals_router,
    audit_router,
    auth_router,
    credentials_router,
    dlq_router,
    events_router,
    functions_router,
    health_router,
    model_pricing_router,
    runs_router,
    stats_router,
    stream_router,
    tools_router,
    usage_router,
    users_router,
)
from flowforge_server.config import get_settings
from flowforge_server.db import close_db, init_db, run_migrations
from flowforge_server.logging import Loggers, configure_logging
from flowforge_server.middleware.correlation import add_correlation_middleware
from flowforge_server.services.container import create_service_container
from flowforge_server.services.seed import run_all_seeds
from flowforge_server.telemetry.metrics import add_metrics_middleware, metrics_router
from flowforge_server.telemetry.tracing import (
    OTEL_AVAILABLE,
    init_tracing,
    instrument_app,
    instrument_httpx,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Configure logging first
    configure_logging()
    log = Loggers.api()

    # Startup
    settings = get_settings()
    log.info("starting_application", env=settings.env)

    # Initialize OpenTelemetry tracing if configured
    if settings.otlp_endpoint:
        init_tracing(service_name=settings.service_name, otlp_endpoint=settings.otlp_endpoint)
        instrument_httpx()  # Instrument HTTPX for AI provider calls
        if OTEL_AVAILABLE:
            log.info("opentelemetry_initialized", endpoint=settings.otlp_endpoint)

    if settings.is_development:
        # Initialize database tables in development
        await init_db()

    # Run any pending migrations
    await run_migrations()

    # Seed built-in tools and default data
    await run_all_seeds()

    # Initialize service container
    services = create_service_container()
    await services.initialize()
    app.state.services = services

    log.info("application_started")

    yield

    # Shutdown
    log.info("shutting_down_application")
    await services.close()
    await close_db()
    log.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # OpenAPI tags for better documentation organization
    tags_metadata = [
        {
            "name": "health",
            "description": "Health check endpoints",
        },
        {
            "name": "events",
            "description": "Event ingestion - trigger workflows by sending events",
        },
        {
            "name": "functions",
            "description": "Function management - register and configure workflow functions (both worker and serverless modes)",
        },
        {
            "name": "tools",
            "description": "Tool management - manage built-in and custom tools for agent-based functions",
        },
        {
            "name": "runs",
            "description": "Run management - view and control workflow executions",
        },
        {
            "name": "approvals",
            "description": "Human-in-the-Loop (HITL) - approve or reject tool calls that require human approval",
        },
        {
            "name": "stream",
            "description": "Real-time streaming - SSE endpoints for live run progress",
        },
        {
            "name": "auth",
            "description": "Authentication - API key management and token exchange",
        },
        {
            "name": "users",
            "description": "User management - dashboard user authentication and administration",
        },
        {
            "name": "stats",
            "description": "Dashboard statistics - aggregated metrics for the dashboard",
        },
    ]

    app = FastAPI(
        title="FlowForge API",
        description="""
## FlowForge - AI Workflow Orchestration Platform

FlowForge provides durable execution for AI-powered workflows with:

### Features
- **Serverless Functions**: Define agent-based functions via API (no worker needed)
- **Worker Functions**: Register functions from your own worker process
- **Built-in Tools**: Pre-configured tools for web search, image generation, social posting
- **Custom Tools**: Add your own tools with custom Python code
- **Human-in-the-Loop**: Tools can require human approval before execution
- **Real-time Streaming**: SSE support for live progress updates
- **Durable Execution**: Automatic retries, checkpointing, and recovery

### Execution Modes
1. **Serverless (Inline)**: Functions defined via API, executed internally by FlowForge
2. **Worker Mode**: Functions defined in code, executed by your worker process

### Quick Start
1. Create tools via `POST /api/v1/tools` (or use built-in tools)
2. Create a serverless function via `POST /api/v1/functions/inline`
3. Trigger via `POST /api/v1/events`
4. Stream progress via `GET /api/v1/runs/{id}/stream`
        """,
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_tags=tags_metadata,
        lifespan=lifespan,
    )

    # CORS middleware
    # In production, only configured origins are allowed
    # In development, all origins are allowed for convenience
    cors_origins = settings.cors_origins
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=settings.effective_cors_allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(functions_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(approvals_router, prefix="/api/v1")
    app.include_router(stream_router, prefix="/api/v1")
    app.include_router(tools_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(stats_router, prefix="/api/v1")
    app.include_router(ai_providers_router, prefix="/api/v1")
    app.include_router(usage_router, prefix="/api/v1")
    app.include_router(model_pricing_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(dlq_router, prefix="/api/v1")
    app.include_router(credentials_router, prefix="/api/v1")

    # Prometheus metrics (no prefix - exposed at /metrics)
    app.include_router(metrics_router)

    # Register global error handlers
    register_error_handlers(app)

    # Add correlation ID middleware (must be added after error handlers)
    add_correlation_middleware(app)

    # Add metrics middleware (tracks request duration/count)
    add_metrics_middleware(app)

    # Add security headers (X-Content-Type-Options, X-Frame-Options, etc.)
    add_api_middleware(app)

    # Instrument FastAPI with OpenTelemetry (if configured)
    settings = get_settings()
    if settings.otlp_endpoint:
        instrument_app(app)

    return app


# Create default app instance
app = create_app()
