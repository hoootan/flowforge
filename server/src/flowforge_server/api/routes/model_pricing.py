"""Model pricing management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import CurrentUserAdmin, TenantWithDevFallback
from flowforge_server.api.schemas.model_pricing import (
    DefaultModelPricing,
    DefaultModelPricingListResponse,
    EffectiveModelPricing,
    EffectiveModelPricingListResponse,
    ModelPricingCreate,
    ModelPricingListResponse,
    ModelPricingResponse,
    ModelPricingUpdate,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import ModelPricing
from flowforge_server.services.model_pricing import (
    FALLBACK_INPUT_PRICE,
    FALLBACK_OUTPUT_PRICE,
    ModelPricingError,
    ModelPricingExistsError,
    ModelPricingNotFoundError,
    get_model_pricing_service,
)
from flowforge_server.services.providers.config import DEFAULT_MODEL_CONFIGS

router = APIRouter(prefix="/ai/pricing", tags=["ai-pricing"])


def model_pricing_to_response(pricing: ModelPricing) -> ModelPricingResponse:
    """Convert ModelPricing model to response schema."""
    return ModelPricingResponse(
        id=str(pricing.id),
        model_id=pricing.model_id,
        provider=pricing.provider,
        input_price_per_m=pricing.input_price_per_m,
        output_price_per_m=pricing.output_price_per_m,
        display_name=pricing.display_name,
        is_active=pricing.is_active,
        is_global=pricing.tenant_id is None,
        created_at=pricing.created_at,
        updated_at=pricing.updated_at,
    )


@router.get("", response_model=ModelPricingListResponse)
async def list_pricing_configs(
    tenant: TenantWithDevFallback,
    include_global: bool = True,
    session: AsyncSession = Depends(get_session),
) -> ModelPricingListResponse:
    """
    List custom pricing configurations.

    Returns tenant-specific pricing configs and optionally global configs.
    """
    service = get_model_pricing_service()
    configs = await service.list_custom_pricing(
        session, tenant.id, include_global=include_global
    )

    return ModelPricingListResponse(
        pricing_configs=[model_pricing_to_response(c) for c in configs],
        total=len(configs),
    )


@router.get("/effective", response_model=EffectiveModelPricingListResponse)
async def list_effective_pricing(
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> EffectiveModelPricingListResponse:
    """
    List all models with their effective (resolved) pricing.

    This shows what pricing will actually be used for each model,
    including the source of that pricing (tenant, global, default, or fallback).
    """
    service = get_model_pricing_service()
    models = await service.list_effective_pricing(session, tenant.id)

    return EffectiveModelPricingListResponse(
        models=[
            EffectiveModelPricing(
                model_id=m["model_id"],
                provider=m["provider"],
                input_price_per_m=m["input_price_per_m"],
                output_price_per_m=m["output_price_per_m"],
                display_name=m["display_name"],
                source=m["source"],
                pricing_id=m["pricing_id"],
            )
            for m in models
        ],
        total=len(models),
    )


@router.get("/defaults", response_model=DefaultModelPricingListResponse)
async def list_default_pricing() -> DefaultModelPricingListResponse:
    """
    List hardcoded default pricing from DEFAULT_MODEL_CONFIGS.

    This endpoint does not require authentication.
    These are the prices used when no custom pricing is configured.
    """
    defaults = [
        DefaultModelPricing(
            model_id=model_id,
            provider=config.provider,
            input_price_per_m=config.input_price_per_m or FALLBACK_INPUT_PRICE,
            output_price_per_m=config.output_price_per_m or FALLBACK_OUTPUT_PRICE,
        )
        for model_id, config in DEFAULT_MODEL_CONFIGS.items()
    ]

    return DefaultModelPricingListResponse(
        defaults=defaults,
        total=len(defaults),
        fallback_input_price=FALLBACK_INPUT_PRICE,
        fallback_output_price=FALLBACK_OUTPUT_PRICE,
    )


@router.get("/{pricing_id}", response_model=ModelPricingResponse)
async def get_pricing_config(
    pricing_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ModelPricingResponse:
    """
    Get a specific pricing configuration by ID.
    """
    service = get_model_pricing_service()

    try:
        pricing_uuid = uuid.UUID(pricing_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pricing ID format",
        )

    pricing = await service.get_pricing(session, pricing_uuid)

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config {pricing_id} not found",
        )

    # Verify access (must be global or belong to this tenant)
    if pricing.tenant_id and pricing.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config {pricing_id} not found",
        )

    return model_pricing_to_response(pricing)


@router.post("", response_model=ModelPricingResponse, status_code=201)
async def create_pricing_config(
    pricing_data: ModelPricingCreate,
    tenant: TenantWithDevFallback,
    admin_user: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> ModelPricingResponse:
    """
    Create a new pricing configuration.

    **Requires admin role.**

    By default, creates tenant-specific pricing. Set `is_global=true` to create
    global pricing that applies as a default for all tenants.
    """
    service = get_model_pricing_service()

    # Determine tenant_id (None for global)
    target_tenant_id = None if pricing_data.is_global else tenant.id

    try:
        pricing = await service.create_pricing(
            session=session,
            model_id=pricing_data.model_id,
            provider=pricing_data.provider,
            input_price_per_m=pricing_data.input_price_per_m,
            output_price_per_m=pricing_data.output_price_per_m,
            tenant_id=target_tenant_id,
            display_name=pricing_data.display_name,
        )
        await session.commit()

        return model_pricing_to_response(pricing)

    except ModelPricingExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ModelPricingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{pricing_id}", response_model=ModelPricingResponse)
async def update_pricing_config(
    pricing_id: str,
    pricing_data: ModelPricingUpdate,
    tenant: TenantWithDevFallback,
    admin_user: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> ModelPricingResponse:
    """
    Update a pricing configuration.

    **Requires admin role.**

    All fields are optional - only provided fields will be updated.
    """
    service = get_model_pricing_service()

    try:
        pricing_uuid = uuid.UUID(pricing_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pricing ID format",
        )

    # First verify the pricing exists and user has access
    pricing = await service.get_pricing(session, pricing_uuid)

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config {pricing_id} not found",
        )

    # Verify access (must be global or belong to this tenant)
    if pricing.tenant_id and pricing.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config {pricing_id} not found",
        )

    try:
        updated = await service.update_pricing(
            session=session,
            pricing_id=pricing_uuid,
            input_price_per_m=pricing_data.input_price_per_m,
            output_price_per_m=pricing_data.output_price_per_m,
            display_name=pricing_data.display_name,
            is_active=pricing_data.is_active,
        )
        await session.commit()

        return model_pricing_to_response(updated)

    except ModelPricingNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ModelPricingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{pricing_id}", status_code=204)
async def delete_pricing_config(
    pricing_id: str,
    tenant: TenantWithDevFallback,
    admin_user: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a pricing configuration.

    **Requires admin role.**

    This removes the custom pricing. The model will fall back to the next
    available pricing source (global, default, or fallback).
    """
    service = get_model_pricing_service()

    try:
        pricing_uuid = uuid.UUID(pricing_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pricing ID format",
        )

    # First verify the pricing exists and user has access
    pricing = await service.get_pricing(session, pricing_uuid)

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config {pricing_id} not found",
        )

    # Verify access (must be global or belong to this tenant)
    if pricing.tenant_id and pricing.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config {pricing_id} not found",
        )

    deleted = await service.delete_pricing(session, pricing_uuid)
    await session.commit()

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config {pricing_id} not found",
        )
