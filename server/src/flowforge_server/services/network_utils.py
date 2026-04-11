"""Network security utilities — SSRF protection."""

import ipaddress
from urllib.parse import urlparse


def is_private_ip(hostname: str) -> bool:
    """Check if a hostname is a private/reserved IP address."""
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local
    except ValueError:
        return hostname in ("localhost", "0.0.0.0", "127.0.0.1", "::1")


def validate_webhook_url(url: str) -> None:
    """
    Validate that a URL does not target private/internal networks.

    Raises ValueError if the URL targets a private, loopback, reserved,
    or link-local address.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if is_private_ip(hostname):
        raise ValueError(
            f"Requests to private/reserved addresses are blocked: {hostname}"
        )
