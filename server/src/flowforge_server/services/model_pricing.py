"""Model pricing service for configurable AI model costs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models import ModelPricing
from flowforge_server.services.providers.config import DEFAULT_MODEL_CONFIGS

if TYPE_CHECKING:
    pass

# Fallback pricing for completely unknown models (per 1M tokens)
FALLBACK_INPUT_PRICE = 1.0
FALLBACK_OUTPUT_PRICE = 2.0

# Type alias for pricing source
PricingSource = Literal["tenant", "global", "default", "fallback"]


class ModelPricingError(Exception):
    """Base exception for model pricing errors."""

    pass


class ModelPricingExistsError(ModelPricingError):
    """Raised when pricing config already exists for this model."""

    pass


class ModelPricingNotFoundError(ModelPricingError):
    """Raised when pricing config is not found."""

    pass


class ModelPricingService:
    """
    Service for managing custom AI model pricing.

    Pricing resolution order:
    1. Tenant-specific custom pricing (highest priority)
    2. Global custom pricing (tenant_id is NULL)
    3. Hardcoded defaults in DEFAULT_MODEL_CONFIGS
    4. Fallback pricing for unknown models (lowest priority)
    """

    async def get_effective_pricing(
        self,
        session: AsyncSession,
        model_id: str,
        tenant_id: uuid.UUID | None = None,
    ) -> tuple[float, float, PricingSource, str | None]:
        """
        Get the effective pricing for a model.

        Resolution order:
        1. Tenant-specific pricing (if tenant_id provided)
        2. Global custom pricing
        3. DEFAULT_MODEL_CONFIGS
        4. Fallback pricing

        Args:
            session: Database session
            model_id: Model identifier
            tenant_id: Optional tenant ID for tenant-specific pricing

        Returns:
            Tuple of (input_price, output_price, source, pricing_id)
            - source: "tenant", "global", "default", or "fallback"
            - pricing_id: ID of custom pricing config if applicable
        """
        # 1. Check tenant-specific pricing
        if tenant_id:
            tenant_pricing = await self._get_pricing_by_tenant(
                session, model_id, tenant_id
            )
            if tenant_pricing and tenant_pricing.is_active:
                return (
                    tenant_pricing.input_price_per_m,
                    tenant_pricing.output_price_per_m,
                    "tenant",
                    str(tenant_pricing.id),
                )

        # 2. Check global custom pricing
        global_pricing = await self._get_global_pricing(session, model_id)
        if global_pricing and global_pricing.is_active:
            return (
                global_pricing.input_price_per_m,
                global_pricing.output_price_per_m,
                "global",
                str(global_pricing.id),
            )

        # 3. Check hardcoded defaults
        if model_id in DEFAULT_MODEL_CONFIGS:
            config = DEFAULT_MODEL_CONFIGS[model_id]
            input_price = config.input_price_per_m or FALLBACK_INPUT_PRICE
            output_price = config.output_price_per_m or FALLBACK_OUTPUT_PRICE
            return (input_price, output_price, "default", None)

        # 4. Fallback pricing for unknown models
        return (FALLBACK_INPUT_PRICE, FALLBACK_OUTPUT_PRICE, "fallback", None)

    async def list_effective_pricing(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """
        List all models with their effective pricing.

        This combines:
        - All models from DEFAULT_MODEL_CONFIGS
        - All custom pricing configs (global and tenant-specific)

        Args:
            session: Database session
            tenant_id: Optional tenant ID for tenant-specific pricing

        Returns:
            List of dicts with model_id, provider, input/output prices, source, etc.
        """
        result: dict[str, dict] = {}

        # Start with hardcoded defaults
        for model_id, config in DEFAULT_MODEL_CONFIGS.items():
            result[model_id] = {
                "model_id": model_id,
                "provider": config.provider,
                "input_price_per_m": config.input_price_per_m or FALLBACK_INPUT_PRICE,
                "output_price_per_m": config.output_price_per_m or FALLBACK_OUTPUT_PRICE,
                "display_name": None,
                "source": "default",
                "pricing_id": None,
            }

        # Layer on global custom pricing
        global_configs = await self._list_global_pricing(session)
        for pricing in global_configs:
            if pricing.is_active:
                result[pricing.model_id] = {
                    "model_id": pricing.model_id,
                    "provider": pricing.provider,
                    "input_price_per_m": pricing.input_price_per_m,
                    "output_price_per_m": pricing.output_price_per_m,
                    "display_name": pricing.display_name,
                    "source": "global",
                    "pricing_id": str(pricing.id),
                }

        # Layer on tenant-specific pricing (highest priority)
        if tenant_id:
            tenant_configs = await self._list_tenant_pricing(session, tenant_id)
            for pricing in tenant_configs:
                if pricing.is_active:
                    result[pricing.model_id] = {
                        "model_id": pricing.model_id,
                        "provider": pricing.provider,
                        "input_price_per_m": pricing.input_price_per_m,
                        "output_price_per_m": pricing.output_price_per_m,
                        "display_name": pricing.display_name,
                        "source": "tenant",
                        "pricing_id": str(pricing.id),
                    }

        return list(result.values())

    async def list_custom_pricing(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID | None = None,
        include_global: bool = True,
    ) -> list[ModelPricing]:
        """
        List custom pricing configs.

        Args:
            session: Database session
            tenant_id: If provided, list tenant-specific pricing
            include_global: Whether to include global pricing configs

        Returns:
            List of ModelPricing records
        """
        conditions = []

        if tenant_id:
            conditions.append(ModelPricing.tenant_id == tenant_id)

        if include_global:
            if tenant_id:
                # Include both tenant and global
                conditions = [
                    or_(
                        ModelPricing.tenant_id == tenant_id,
                        ModelPricing.tenant_id.is_(None),
                    )
                ]
            else:
                # Only global
                conditions.append(ModelPricing.tenant_id.is_(None))

        query = select(ModelPricing).order_by(ModelPricing.model_id)
        if conditions:
            query = query.where(and_(*conditions))

        result = await session.execute(query)
        return list(result.scalars().all())

    async def create_pricing(
        self,
        session: AsyncSession,
        model_id: str,
        provider: str,
        input_price_per_m: float,
        output_price_per_m: float,
        tenant_id: uuid.UUID | None = None,
        display_name: str | None = None,
    ) -> ModelPricing:
        """
        Create a new pricing config.

        Args:
            session: Database session
            model_id: Model identifier
            provider: Provider name
            input_price_per_m: Price per 1M input tokens
            output_price_per_m: Price per 1M output tokens
            tenant_id: Optional tenant ID (None for global pricing)
            display_name: Optional display name

        Returns:
            Created ModelPricing record

        Raises:
            ModelPricingExistsError: If pricing already exists for this model/tenant
        """
        # Check if pricing already exists
        existing = await self._get_pricing_by_tenant(
            session, model_id, tenant_id
        ) if tenant_id else await self._get_global_pricing(session, model_id)

        if existing:
            scope = f"tenant {tenant_id}" if tenant_id else "global"
            raise ModelPricingExistsError(
                f"Pricing for model '{model_id}' already exists at {scope} scope"
            )

        pricing = ModelPricing(
            model_id=model_id,
            provider=provider,
            input_price_per_m=input_price_per_m,
            output_price_per_m=output_price_per_m,
            tenant_id=tenant_id,
            display_name=display_name,
            is_active=True,
        )

        session.add(pricing)
        await session.flush()
        await session.refresh(pricing)

        return pricing

    async def update_pricing(
        self,
        session: AsyncSession,
        pricing_id: uuid.UUID,
        input_price_per_m: float | None = None,
        output_price_per_m: float | None = None,
        display_name: str | None = None,
        is_active: bool | None = None,
    ) -> ModelPricing:
        """
        Update a pricing config.

        Args:
            session: Database session
            pricing_id: Pricing config ID
            input_price_per_m: New input price (optional)
            output_price_per_m: New output price (optional)
            display_name: New display name (optional)
            is_active: Enable/disable config (optional)

        Returns:
            Updated ModelPricing record

        Raises:
            ModelPricingNotFoundError: If pricing config not found
        """
        pricing = await session.get(ModelPricing, pricing_id)
        if not pricing:
            raise ModelPricingNotFoundError(f"Pricing config {pricing_id} not found")

        if input_price_per_m is not None:
            pricing.input_price_per_m = input_price_per_m
        if output_price_per_m is not None:
            pricing.output_price_per_m = output_price_per_m
        if display_name is not None:
            pricing.display_name = display_name
        if is_active is not None:
            pricing.is_active = is_active

        await session.flush()
        await session.refresh(pricing)

        return pricing

    async def delete_pricing(
        self,
        session: AsyncSession,
        pricing_id: uuid.UUID,
    ) -> bool:
        """
        Delete a pricing config.

        Args:
            session: Database session
            pricing_id: Pricing config ID

        Returns:
            True if deleted, False if not found
        """
        pricing = await session.get(ModelPricing, pricing_id)
        if not pricing:
            return False

        await session.delete(pricing)
        await session.flush()

        return True

    async def get_pricing(
        self,
        session: AsyncSession,
        pricing_id: uuid.UUID,
    ) -> ModelPricing | None:
        """Get a specific pricing config by ID."""
        return await session.get(ModelPricing, pricing_id)

    # Private helper methods

    async def _get_pricing_by_tenant(
        self,
        session: AsyncSession,
        model_id: str,
        tenant_id: uuid.UUID | None,
    ) -> ModelPricing | None:
        """Get tenant-specific pricing for a model."""
        if tenant_id is None:
            return None

        query = select(ModelPricing).where(
            and_(
                ModelPricing.model_id == model_id,
                ModelPricing.tenant_id == tenant_id,
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def _get_global_pricing(
        self,
        session: AsyncSession,
        model_id: str,
    ) -> ModelPricing | None:
        """Get global pricing for a model."""
        query = select(ModelPricing).where(
            and_(
                ModelPricing.model_id == model_id,
                ModelPricing.tenant_id.is_(None),
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def _list_global_pricing(
        self,
        session: AsyncSession,
    ) -> list[ModelPricing]:
        """List all global pricing configs."""
        query = select(ModelPricing).where(
            ModelPricing.tenant_id.is_(None)
        ).order_by(ModelPricing.model_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def _list_tenant_pricing(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> list[ModelPricing]:
        """List all pricing configs for a tenant."""
        query = select(ModelPricing).where(
            ModelPricing.tenant_id == tenant_id
        ).order_by(ModelPricing.model_id)
        result = await session.execute(query)
        return list(result.scalars().all())


# Global service instance
_model_pricing_service: ModelPricingService | None = None


def get_model_pricing_service() -> ModelPricingService:
    """Get the global model pricing service instance."""
    global _model_pricing_service
    if _model_pricing_service is None:
        _model_pricing_service = ModelPricingService()
    return _model_pricing_service
