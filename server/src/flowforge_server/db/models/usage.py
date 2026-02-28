"""Usage tracking model for AI calls."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from flowforge_server.db.models.base import Base, TimestampMixin


class UsageRecord(Base, TimestampMixin):
    """
    Record of AI usage for billing and analytics.

    Tracks every AI call with token counts, costs, and metadata.
    """

    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Tenant association
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional run association
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Model information
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Token counts
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Cost tracking
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Performance metrics
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Request metadata
    request_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="completion",
        index=True,
    )  # completion, streaming, tool_call

    # Additional context (tool calls, errors, etc.)
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Timestamp for when the request was made
    requested_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_usage_tenant_date", "tenant_id", "requested_at"),
        Index("ix_usage_tenant_model", "tenant_id", "model"),
    )

    def __repr__(self) -> str:
        return f"<UsageRecord {self.model} {self.total_tokens} tokens ${self.cost_usd:.4f}>"
