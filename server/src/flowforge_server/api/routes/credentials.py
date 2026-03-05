"""Credential management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.api.schemas.credentials import (
    CredentialCreate,
    CredentialResponse,
    CredentialsResponse,
    CredentialUpdate,
)
from flowforge_server.db import get_session
from flowforge_server.db.models.credential import Credential
from flowforge_server.services.crypto import encrypt_value, get_key_prefix

router = APIRouter(prefix="/credentials", tags=["credentials"])


def _to_response(cred: Credential) -> CredentialResponse:
    return CredentialResponse(
        id=str(cred.id),
        name=cred.name,
        credential_type=cred.credential_type,
        value_prefix=cred.value_prefix,
        description=cred.description,
        is_active=cred.is_active,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
    )


@router.post("", response_model=CredentialResponse, status_code=201)
async def create_credential(
    data: CredentialCreate,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> CredentialResponse:
    """Create a new encrypted credential."""
    # Check for existing
    existing = await session.execute(
        select(Credential).where(
            Credential.tenant_id == tenant.id,
            Credential.name == data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Credential with name '{data.name}' already exists",
        )

    cred = Credential(
        tenant_id=tenant.id,
        name=data.name,
        credential_type=data.credential_type,
        encrypted_value=encrypt_value(data.value),
        value_prefix=get_key_prefix(data.value),
        description=data.description,
        is_active=True,
    )
    session.add(cred)
    await session.commit()
    await session.refresh(cred)

    return _to_response(cred)


@router.get("", response_model=CredentialsResponse)
async def list_credentials(
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> CredentialsResponse:
    """List all credentials for the tenant (values are never returned)."""
    query = select(Credential).where(Credential.tenant_id == tenant.id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    result = await session.execute(query.order_by(Credential.name))
    creds = result.scalars().all()

    return CredentialsResponse(
        credentials=[_to_response(c) for c in creds],
        total=total,
    )


@router.get("/{name}", response_model=CredentialResponse)
async def get_credential(
    name: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> CredentialResponse:
    """Get a credential's metadata by name (value is never returned)."""
    result = await session.execute(
        select(Credential).where(
            Credential.tenant_id == tenant.id,
            Credential.name == name,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    return _to_response(cred)


@router.patch("/{name}", response_model=CredentialResponse)
async def update_credential(
    name: str,
    data: CredentialUpdate,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> CredentialResponse:
    """Update a credential. If value is provided, it is re-encrypted."""
    result = await session.execute(
        select(Credential).where(
            Credential.tenant_id == tenant.id,
            Credential.name == name,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    if data.value is not None:
        cred.encrypted_value = encrypt_value(data.value)
        cred.value_prefix = get_key_prefix(data.value)
    if data.description is not None:
        cred.description = data.description
    if data.credential_type is not None:
        cred.credential_type = data.credential_type
    if data.is_active is not None:
        cred.is_active = data.is_active

    await session.commit()
    await session.refresh(cred)

    return _to_response(cred)


@router.delete("/{name}", status_code=204)
async def delete_credential(
    name: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a credential."""
    result = await session.execute(
        select(Credential).where(
            Credential.tenant_id == tenant.id,
            Credential.name == name,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    await session.delete(cred)
    await session.commit()
