"""Function versioning service for tracking and rolling back changes."""

from __future__ import annotations

from typing import TYPE_CHECKING
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models.function import Function
from flowforge_server.db.models.function_version import FunctionVersion
from flowforge_server.logging import Loggers

if TYPE_CHECKING:
    pass


class FunctionVersioningService:
    """Service for managing function version history."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._log = Loggers.services()

    async def create_version(
        self,
        function: Function,
        created_by_id: uuid.UUID | None = None,
        change_reason: str | None = None,
    ) -> FunctionVersion:
        """
        Create a new version snapshot of a function.

        Should be called before updating a function to preserve the current state.

        Args:
            function: The function to create a version for
            created_by_id: ID of the user making the change
            change_reason: Optional description of the change

        Returns:
            The newly created FunctionVersion
        """
        # Get the next version number
        result = await self.session.execute(
            select(func.max(FunctionVersion.version))
            .where(FunctionVersion.function_id == function.id)
        )
        max_version = result.scalar() or 0
        next_version = max_version + 1

        version = FunctionVersion(
            function_id=function.id,
            version=next_version,
            created_by_id=created_by_id,
            change_reason=change_reason,
            # Snapshot current state
            name=function.name,
            trigger_type=function.trigger_type,
            trigger_value=function.trigger_value,
            trigger_expression=function.trigger_expression,
            endpoint_url=function.endpoint_url,
            is_inline=function.is_inline,
            system_prompt=function.system_prompt,
            tools_config=function.tools_config,
            agent_config=function.agent_config,
            config=function.config,
        )

        self.session.add(version)

        self._log.info(
            "function_version_created",
            function_id=str(function.id),
            function_slug=function.function_id,
            version=next_version,
            created_by=str(created_by_id) if created_by_id else None,
        )

        return version

    async def get_versions(
        self,
        function_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FunctionVersion]:
        """
        Get version history for a function.

        Args:
            function_id: The function's database ID
            limit: Maximum number of versions to return
            offset: Number of versions to skip

        Returns:
            List of FunctionVersion objects, most recent first
        """
        result = await self.session.execute(
            select(FunctionVersion)
            .where(FunctionVersion.function_id == function_id)
            .order_by(FunctionVersion.version.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_version(
        self,
        function_id: uuid.UUID,
        version: int,
    ) -> FunctionVersion | None:
        """
        Get a specific version of a function.

        Args:
            function_id: The function's database ID
            version: The version number

        Returns:
            FunctionVersion or None if not found
        """
        result = await self.session.execute(
            select(FunctionVersion)
            .where(FunctionVersion.function_id == function_id)
            .where(FunctionVersion.version == version)
        )
        return result.scalar_one_or_none()

    async def get_version_count(self, function_id: uuid.UUID) -> int:
        """Get the total number of versions for a function."""
        result = await self.session.execute(
            select(func.count(FunctionVersion.id))
            .where(FunctionVersion.function_id == function_id)
        )
        return result.scalar() or 0

    async def rollback_to_version(
        self,
        function: Function,
        version: int,
        created_by_id: uuid.UUID | None = None,
    ) -> FunctionVersion:
        """
        Rollback a function to a previous version.

        This creates a new version snapshot (before the rollback),
        then applies the historical version's configuration.

        Args:
            function: The function to rollback
            version: The version number to rollback to
            created_by_id: ID of the user performing the rollback

        Returns:
            The newly created version (snapshot before rollback)

        Raises:
            ValueError: If the target version doesn't exist
        """
        # Get the target version
        target = await self.get_version(function.id, version)
        if not target:
            raise ValueError(f"Version {version} not found for function {function.id}")

        # Create a snapshot of the current state first
        snapshot = await self.create_version(
            function,
            created_by_id=created_by_id,
            change_reason=f"Snapshot before rollback to version {version}",
        )

        # Apply the historical version's configuration
        function.name = target.name
        function.trigger_type = target.trigger_type
        function.trigger_value = target.trigger_value
        function.trigger_expression = target.trigger_expression
        function.endpoint_url = target.endpoint_url
        function.is_inline = target.is_inline
        function.system_prompt = target.system_prompt
        function.tools_config = target.tools_config
        function.agent_config = target.agent_config
        function.config = target.config

        self._log.info(
            "function_rolled_back",
            function_id=str(function.id),
            function_slug=function.function_id,
            rolled_back_to=version,
            snapshot_version=snapshot.version,
            created_by=str(created_by_id) if created_by_id else None,
        )

        return snapshot

    async def compare_versions(
        self,
        function_id: uuid.UUID,
        version_a: int,
        version_b: int,
    ) -> dict:
        """
        Compare two versions of a function.

        Args:
            function_id: The function's database ID
            version_a: First version to compare
            version_b: Second version to compare

        Returns:
            Dictionary with differences between versions
        """
        va = await self.get_version(function_id, version_a)
        vb = await self.get_version(function_id, version_b)

        if not va or not vb:
            raise ValueError("One or both versions not found")

        # Fields to compare
        fields = [
            "name", "trigger_type", "trigger_value", "trigger_expression",
            "endpoint_url", "is_inline", "system_prompt", "tools_config",
            "agent_config", "config"
        ]

        differences = {}
        for field in fields:
            val_a = getattr(va, field)
            val_b = getattr(vb, field)
            if val_a != val_b:
                differences[field] = {
                    "version_a": val_a,
                    "version_b": val_b,
                }

        return {
            "version_a": version_a,
            "version_b": version_b,
            "has_changes": len(differences) > 0,
            "differences": differences,
        }
