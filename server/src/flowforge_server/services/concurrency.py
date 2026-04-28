"""Shared helpers for reading workspace concurrency settings.

Imported by both the runner (decides idempotency / per-function default /
max_concurrent_runs throttle at enqueue time) and the executor (falls back
to tenant default for step_timeout when the runner-injected job config is
absent — e.g. on the recovery enqueue path).

Lives in services/ rather than schemas/ because it touches the DB row and
schemas/ is supposed to be Pydantic-only. Avoids the circular-import risk
of executor importing from runner.
"""

from __future__ import annotations

from flowforge_server.api.schemas.tenant import ConcurrencySettings
from flowforge_server.db.models import Tenant


def read_tenant_concurrency(tenant: Tenant | None) -> ConcurrencySettings:
    """Read the workspace concurrency block from a tenant row, with defaults.

    Mirrors the route logic in api/routes/tenants.py so callers in the
    services layer can honor settings without going through the API.
    """
    if tenant is None:
        return ConcurrencySettings()
    raw = (tenant.settings or {}).get("concurrency") or {}
    return ConcurrencySettings(**{k: v for k, v in raw.items() if v is not None})
