"""Network security utilities — SSRF protection."""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx


def is_private_ip(hostname: str) -> bool:
    """Check if a hostname is a private/reserved IP address."""
    try:
        addr = ipaddress.ip_address(hostname)
        return not addr.is_global
    except ValueError:
        return hostname in ("localhost", "0.0.0.0", "127.0.0.1", "::1")


def resolve_and_validate_host(hostname: str, port: int | None = None) -> None:
    """
    Resolve hostname via DNS and reject if any resolved IP is non-global.

    Prevents DNS rebinding attacks where a public domain resolves to
    a private/loopback/link-local address.
    """
    try:
        results = socket.getaddrinfo(hostname, port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")
    for _family, _type, _proto, _canonname, sockaddr in results:
        ip_str = sockaddr[0]
        if is_private_ip(ip_str):
            raise ValueError(
                f"Hostname '{hostname}' resolves to blocked address: {ip_str}"
            )


def validate_webhook_url(url: str) -> None:
    """
    Validate that a URL does not target private/internal networks.

    Checks: scheme whitelist, raw IP check, and DNS resolution of hostname.
    Raises ValueError if the URL is unsafe.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"URL scheme '{parsed.scheme}' is not allowed (use http or https)"
        )
    hostname = parsed.hostname or ""
    if not hostname:
        raise ValueError("URL has no hostname")
    # Fast path: raw IP literals
    if is_private_ip(hostname):
        raise ValueError(
            f"Requests to private/reserved addresses are blocked: {hostname}"
        )
    # DNS resolution check (catches domains that resolve to private IPs)
    resolve_and_validate_host(hostname, parsed.port)


def _check_redirect(response: httpx.Response) -> None:
    """httpx event hook: validate redirect targets against SSRF."""
    if response.is_redirect and "location" in response.headers:
        target = response.headers["location"]
        target_url = response.url.join(target)
        hostname = str(target_url.host) or ""
        if not hostname:
            return
        if is_private_ip(hostname):
            raise ValueError(f"Redirect to private address blocked: {hostname}")
        resolve_and_validate_host(hostname, target_url.port)


def create_ssrf_safe_client(**kwargs: object) -> httpx.AsyncClient:
    """Create an async httpx client that validates redirect targets."""
    kwargs.setdefault("follow_redirects", True)
    kwargs.setdefault("timeout", 30.0)
    return httpx.AsyncClient(
        event_hooks={"response": [_check_redirect]}, **kwargs  # type: ignore[arg-type]
    )


def create_ssrf_safe_sync_client(**kwargs: object) -> httpx.Client:
    """Create a sync httpx client that validates redirect targets."""
    kwargs.setdefault("follow_redirects", True)
    kwargs.setdefault("timeout", 30.0)
    return httpx.Client(
        event_hooks={"response": [_check_redirect]}, **kwargs  # type: ignore[arg-type]
    )
