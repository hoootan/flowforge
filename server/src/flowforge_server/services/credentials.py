"""Credential resolution service.

Resolves {{credential:name}} and {{env:VAR}} placeholders in tool
configurations (webhook URLs, headers, body templates).
"""

import os
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models.credential import Credential
from flowforge_server.services.crypto import decrypt_value


class CredentialResolutionError(Exception):
    """Raised when a credential placeholder cannot be resolved."""


_PLACEHOLDER_RE = re.compile(r"\{\{(credential|env):([^}]+)\}\}")


async def resolve_placeholders(
    text: str,
    tenant_id: UUID,
    session: AsyncSession,
    *,
    _cache: dict[str, str] | None = None,
) -> str:
    """
    Replace ``{{credential:name}}`` and ``{{env:VAR}}`` in *text*.

    Args:
        text: String that may contain placeholders.
        tenant_id: Tenant whose credentials to look up.
        session: Active DB session.
        _cache: Optional dict to cache decrypted values within a single
                execution (avoids repeated DB lookups for the same name).

    Returns:
        The string with all placeholders resolved.

    Raises:
        CredentialResolutionError: If a credential is not found or inactive.
    """
    if "{{" not in text:
        return text

    if _cache is None:
        _cache = {}

    async def _replace(match: re.Match) -> str:
        kind = match.group(1)  # "credential" or "env"
        key = match.group(2).strip()

        if kind == "env":
            value = os.environ.get(key)
            if value is None:
                raise CredentialResolutionError(
                    f"Environment variable '{key}' is not set"
                )
            return value

        # kind == "credential"
        if key in _cache:
            return _cache[key]

        result = await session.execute(
            select(Credential).where(
                Credential.tenant_id == tenant_id,
                Credential.name == key,
                Credential.is_active == True,  # noqa: E712
            )
        )
        cred = result.scalar_one_or_none()
        if cred is None:
            raise CredentialResolutionError(
                f"Credential '{key}' not found or inactive"
            )

        decrypted = decrypt_value(cred.encrypted_value)
        _cache[key] = decrypted
        return decrypted

    # Process all matches (we need async replacements so can't use re.sub directly)
    parts: list[str] = []
    last_end = 0
    for match in _PLACEHOLDER_RE.finditer(text):
        parts.append(text[last_end : match.start()])
        parts.append(await _replace(match))
        last_end = match.end()
    parts.append(text[last_end:])

    return "".join(parts)


async def resolve_dict_placeholders(
    data: dict,
    tenant_id: UUID,
    session: AsyncSession,
    *,
    _cache: dict[str, str] | None = None,
) -> dict:
    """Recursively resolve placeholders in all string values of a dict."""
    if _cache is None:
        _cache = {}

    resolved = {}
    for k, v in data.items():
        if isinstance(v, str):
            resolved[k] = await resolve_placeholders(v, tenant_id, session, _cache=_cache)
        elif isinstance(v, dict):
            resolved[k] = await resolve_dict_placeholders(v, tenant_id, session, _cache=_cache)
        else:
            resolved[k] = v
    return resolved
