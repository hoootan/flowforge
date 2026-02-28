"""AI Provider management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import CurrentUserAdmin, TenantWithDevFallback
from flowforge_server.api.schemas.ai_providers import (
    AIProviderCreate,
    AIProviderResponse,
    AIProviderRotateRequest,
    AIProvidersResponse,
    AIProviderTestResponse,
    AIProviderUpdate,
    KnownProviderInfo,
    KnownProvidersResponse,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import AIProvider
from flowforge_server.services.ai_provider import (
    KNOWN_PROVIDERS,
    AIProviderError,
    AIProviderNotFoundError,
    get_ai_provider_service,
)
from flowforge_server.services.crypto import EncryptionKeyMissing

router = APIRouter(prefix="/ai/providers", tags=["ai-providers"])


def ai_provider_to_response(provider: AIProvider) -> AIProviderResponse:
    """Convert AIProvider model to response schema."""
    return AIProviderResponse(
        id=str(provider.id),
        provider_name=provider.provider_name,
        display_name=provider.display_name,
        api_key_prefix=provider.api_key_prefix,
        auth_type=provider.auth_type or "api_key",
        base_url=provider.base_url,
        is_active=provider.is_active,
        is_default=provider.is_default,
        config=provider.config,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.get("", response_model=AIProvidersResponse)
async def list_providers(
    tenant: TenantWithDevFallback,
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
) -> AIProvidersResponse:
    """
    List all AI providers for the current tenant.

    By default, only active providers are returned.
    Set `include_inactive=true` to include disabled providers.
    """
    service = get_ai_provider_service()
    providers = await service.list_providers(
        session, tenant.id, include_inactive=include_inactive
    )

    return AIProvidersResponse(
        providers=[ai_provider_to_response(p) for p in providers],
        total=len(providers),
    )


@router.get("/known", response_model=KnownProvidersResponse)
async def list_known_providers() -> KnownProvidersResponse:
    """
    List known AI providers and their available models.

    This endpoint does not require authentication.
    """
    providers = [
        KnownProviderInfo(
            name=name,
            display_name=info["display_name"],
            models=info["models"],
            default_model=info["default_model"],
        )
        for name, info in KNOWN_PROVIDERS.items()
    ]

    return KnownProvidersResponse(providers=providers)


@router.post("", response_model=AIProviderResponse, status_code=201)
async def create_provider(
    provider_data: AIProviderCreate,
    tenant: TenantWithDevFallback,
    admin_user: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> AIProviderResponse:
    """
    Create a new AI provider configuration.

    **Requires admin role.**

    Multiple providers of the same type are allowed.
    The API key is encrypted at rest using Fernet encryption.
    Only the first 8 characters are stored for display purposes.
    """
    service = get_ai_provider_service()

    try:
        provider = await service.create_provider(
            session=session,
            tenant_id=tenant.id,
            provider_name=provider_data.provider_name,
            api_key=provider_data.api_key,
            display_name=provider_data.display_name,
            base_url=provider_data.base_url,
            is_default=provider_data.is_default,
            config=provider_data.config,
            auth_type=provider_data.auth_type,
        )
        await session.commit()

        return ai_provider_to_response(provider)

    except EncryptionKeyMissing as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except AIProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{provider_id}", response_model=AIProviderResponse)
async def get_provider(
    provider_id: uuid.UUID,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> AIProviderResponse:
    """
    Get details of a specific AI provider by ID.

    The API key is never returned - only the masked prefix.
    """
    service = get_ai_provider_service()

    try:
        provider = await service.get_provider_by_id(session, provider_id, tenant.id)
        return ai_provider_to_response(provider)
    except AIProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch("/{provider_id}", response_model=AIProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    provider_data: AIProviderUpdate,
    tenant: TenantWithDevFallback,
    admin_user: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> AIProviderResponse:
    """
    Update an AI provider configuration by ID.

    **Requires admin role.**

    All fields are optional - only provided fields will be updated.
    If updating the API key, it will be re-encrypted.
    """
    service = get_ai_provider_service()

    try:
        provider = await service.update_provider(
            session=session,
            tenant_id=tenant.id,
            provider_id=provider_id,
            api_key=provider_data.api_key,
            display_name=provider_data.display_name,
            base_url=provider_data.base_url,
            is_active=provider_data.is_active,
            is_default=provider_data.is_default,
            config=provider_data.config,
            auth_type=provider_data.auth_type,
        )
        await session.commit()

        return ai_provider_to_response(provider)

    except EncryptionKeyMissing as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except AIProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AIProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: uuid.UUID,
    tenant: TenantWithDevFallback,
    admin_user: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete an AI provider configuration by ID.

    **Requires admin role.**

    This permanently removes the provider and its encrypted API key.
    """
    service = get_ai_provider_service()

    deleted = await service.delete_provider(session, tenant.id, provider_id)
    await session.commit()

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )


@router.post("/{provider_id}/test", response_model=AIProviderTestResponse)
async def test_provider(
    provider_id: uuid.UUID,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> AIProviderTestResponse:
    """
    Test connectivity to an AI provider by ID.

    Makes a minimal API call to verify the API key is valid.
    """
    service = get_ai_provider_service()

    try:
        result = await service.test_provider(session, tenant.id, provider_id)
        return AIProviderTestResponse(**result)
    except AIProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{provider_id}/rotate", response_model=AIProviderResponse)
async def rotate_provider_key(
    provider_id: uuid.UUID,
    rotate_data: AIProviderRotateRequest,
    tenant: TenantWithDevFallback,
    admin_user: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> AIProviderResponse:
    """
    Rotate the API key for a provider by ID.

    **Requires admin role.**

    This replaces the existing API key with a new one.
    The old key is immediately invalidated (in our storage).
    """
    service = get_ai_provider_service()

    try:
        provider = await service.rotate_key(
            session=session,
            tenant_id=tenant.id,
            provider_id=provider_id,
            new_api_key=rotate_data.new_api_key,
        )
        await session.commit()

        return ai_provider_to_response(provider)

    except EncryptionKeyMissing as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except AIProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AIProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
