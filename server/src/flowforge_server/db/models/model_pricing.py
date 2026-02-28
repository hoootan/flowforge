"""Model pricing configuration."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.tenant import Tenant


class ModelPricing(Base, TimestampMixin):
    """
    Custom pricing configuration for AI models.

    Pricing can be set at two levels:
    - Global (tenant_id is NULL): Applies as default for all tenants
    - Tenant-specific (tenant_id is set): Overrides global/default pricing

    Resolution order for pricing:
    1. Tenant-specific custom pricing
    2. Global custom pricing (tenant_id is NULL)
    3. Hardcoded defaults in DEFAULT_MODEL_CONFIGS
    4. Fallback pricing for unknown models
    """

    __tablename__ = "model_pricing"

    # Unique constraint: only one pricing config per model per tenant (or global)
    __table_args__ = (
        UniqueConstraint("tenant_id", "model_id", name="uq_model_pricing_tenant_model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # NULL means global pricing (applies to all tenants as default)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Model identifier (e.g., "gpt-5.3", "claude-sonnet-4-6")
    model_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Provider name (e.g., "openai", "anthropic", "google")
    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Pricing per 1 million tokens (in USD)
    input_price_per_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    output_price_per_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Optional display name for the model
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Whether this pricing config is active
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationship to tenant (optional)
    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="model_pricing_configs",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        scope = f"tenant={self.tenant_id}" if self.tenant_id else "global"
        return f"<ModelPricing {self.model_id} ({scope}) ${self.input_price_per_m}/${self.output_price_per_m}>"
