"""API routes for FlowForge server."""

from flowforge_server.api.routes.ai_providers import router as ai_providers_router
from flowforge_server.api.routes.approvals import router as approvals_router
from flowforge_server.api.routes.audit import router as audit_router
from flowforge_server.api.routes.auth import router as auth_router
from flowforge_server.api.routes.dlq import router as dlq_router
from flowforge_server.api.routes.events import router as events_router
from flowforge_server.api.routes.functions import router as functions_router
from flowforge_server.api.routes.health import router as health_router
from flowforge_server.api.routes.model_pricing import router as model_pricing_router
from flowforge_server.api.routes.runs import router as runs_router
from flowforge_server.api.routes.stats import router as stats_router
from flowforge_server.api.routes.stream import router as stream_router
from flowforge_server.api.routes.tools import router as tools_router
from flowforge_server.api.routes.usage import router as usage_router
from flowforge_server.api.routes.users import router as users_router

__all__ = [
    "events_router",
    "functions_router",
    "runs_router",
    "health_router",
    "approvals_router",
    "stream_router",
    "tools_router",
    "auth_router",
    "users_router",
    "stats_router",
    "ai_providers_router",
    "usage_router",
    "model_pricing_router",
    "audit_router",
    "dlq_router",
]
