"""Security headers middleware.

Adds defensive HTTP headers to every response. These headers instruct browsers
to apply restrictions that reduce the impact of XSS, clickjacking, MIME sniffing,
and other client-side attacks — important for the dashboard and API clients.

Headers added:
- X-Content-Type-Options: nosniff — prevents MIME-type sniffing
- X-Frame-Options: DENY — blocks iframe embedding (clickjacking)
- X-XSS-Protection: 0 — disables legacy XSS filter (modern browsers use CSP instead)
- Referrer-Policy: strict-origin-when-cross-origin — limits referrer leakage
- Permissions-Policy: disables camera/microphone/geolocation access
- Strict-Transport-Security: enforces HTTPS in production
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from flowforge_server.config import get_settings

# Headers applied to every response regardless of environment
_ALWAYS_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    # Disable the legacy XSS auditor — it can itself introduce vulnerabilities.
    # Modern apps rely on CSP instead.
    "X-XSS-Protection": "0",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# HSTS is only meaningful over HTTPS — skip in development to avoid breaking HTTP
_PRODUCTION_HEADERS: dict[str, str] = {
    # max-age=1 year, include subdomains
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Append security headers to every HTTP response."""

    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        settings = get_settings()
        self._headers = dict(_ALWAYS_HEADERS)
        if not settings.is_development:
            self._headers.update(_PRODUCTION_HEADERS)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        for header, value in self._headers.items():
            response.headers.setdefault(header, value)
        return response
