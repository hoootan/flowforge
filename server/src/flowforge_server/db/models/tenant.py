"""Tenant model for multi-tenancy support."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.ai_provider import AIProvider
    from flowforge_server.db.models.api_key import ApiKey
    from flowforge_server.db.models.credential import Credential
    from flowforge_server.db.models.event import Event
    from flowforge_server.db.models.function import Function
    from flowforge_server.db.models.model_pricing import ModelPricing
    from flowforge_server.db.models.tool import Tool
    from flowforge_server.db.models.user import User


class Tenant(Base, TimestampMixin):
    """
    Tenant/workspace for multi-tenancy.

    Each tenant has isolated functions, events, and runs.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Hashed API key for event ingestion
    api_key_hash: Mapped[str] = mapped_column(Text, nullable=False)

    # Hashed signing key for webhook verification
    signing_key_hash: Mapped[str] = mapped_column(Text, nullable=False)

    # Tenant-specific settings
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    functions: Mapped[list["Function"]] = relationship(
        "Function",
        back_populates="tenant",
        lazy="selectin",
    )

    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="tenant",
        lazy="selectin",
    )

    tools: Mapped[list["Tool"]] = relationship(
        "Tool",
        back_populates="tenant",
        lazy="selectin",
    )

    api_keys: Mapped[list["ApiKey"]] = relationship(
        "ApiKey",
        back_populates="tenant",
        lazy="selectin",
    )

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        lazy="selectin",
    )

    ai_providers: Mapped[list["AIProvider"]] = relationship(
        "AIProvider",
        back_populates="tenant",
        lazy="selectin",
    )

    model_pricing_configs: Mapped[list["ModelPricing"]] = relationship(
        "ModelPricing",
        back_populates="tenant",
        lazy="selectin",
    )

    credentials: Mapped[list["Credential"]] = relationship(
        "Credential",
        back_populates="tenant",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"
