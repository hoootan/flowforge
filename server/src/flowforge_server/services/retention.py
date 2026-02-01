"""Data retention service for cleaning up old data.

Implements configurable retention policies for runs, events, and audit logs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.config import get_settings
from flowforge_server.db.models.run import Run, RunStatus
from flowforge_server.db.models.event import Event
from flowforge_server.db.models.step import Step
from flowforge_server.logging import Loggers

if TYPE_CHECKING:
    pass


@dataclass
class RetentionConfig:
    """Configuration for data retention policies."""

    # Run retention
    completed_run_days: int = 30  # Keep completed runs for 30 days
    failed_run_days: int = 90  # Keep failed runs longer for debugging
    cancelled_run_days: int = 30  # Keep cancelled runs for 30 days

    # Event retention
    processed_event_days: int = 30  # Keep processed events for 30 days
    unprocessed_event_days: int = 90  # Keep unprocessed events longer

    # Audit log retention
    audit_log_days: int = 365  # Keep audit logs for 1 year (compliance)

    # Batch sizes for deletion
    batch_size: int = 1000


@dataclass
class RetentionResult:
    """Result of a retention cleanup operation."""

    runs_deleted: int = 0
    steps_deleted: int = 0
    events_deleted: int = 0
    audit_logs_deleted: int = 0
    errors: list[str] | None = None

    @property
    def total_deleted(self) -> int:
        return self.runs_deleted + self.steps_deleted + self.events_deleted + self.audit_logs_deleted


class RetentionService:
    """Service for managing data retention and cleanup."""

    def __init__(
        self,
        session: AsyncSession,
        config: RetentionConfig | None = None,
    ) -> None:
        self.session = session
        self.config = config or RetentionConfig()
        self._log = Loggers.services()

    async def cleanup_runs(
        self,
        tenant_id: str | None = None,
        dry_run: bool = False,
    ) -> tuple[int, int]:
        """Clean up old runs and their steps.

        Args:
            tenant_id: Optional tenant to filter cleanup
            dry_run: If True, only count without deleting

        Returns:
            Tuple of (runs_deleted, steps_deleted)
        """
        now = datetime.now(timezone.utc)
        runs_deleted = 0
        steps_deleted = 0

        # Define cutoff dates for each status
        status_cutoffs = {
            RunStatus.COMPLETED: now - timedelta(days=self.config.completed_run_days),
            RunStatus.FAILED: now - timedelta(days=self.config.failed_run_days),
            RunStatus.CANCELLED: now - timedelta(days=self.config.cancelled_run_days),
        }

        for status, cutoff in status_cutoffs.items():
            # Find runs to delete
            query = select(Run.id).where(
                Run.status == status,
                Run.created_at < cutoff,
            )
            if tenant_id:
                query = query.where(Run.tenant_id == tenant_id)

            result = await self.session.execute(query.limit(self.config.batch_size))
            run_ids = [row[0] for row in result.fetchall()]

            if not run_ids:
                continue

            if dry_run:
                runs_deleted += len(run_ids)
                # Count steps for these runs
                step_count = await self.session.execute(
                    select(func.count(Step.id)).where(Step.run_id.in_(run_ids))
                )
                steps_deleted += step_count.scalar() or 0
            else:
                # Delete steps first (foreign key constraint)
                step_delete = delete(Step).where(Step.run_id.in_(run_ids))
                step_result = await self.session.execute(step_delete)
                steps_deleted += step_result.rowcount

                # Delete runs
                run_delete = delete(Run).where(Run.id.in_(run_ids))
                run_result = await self.session.execute(run_delete)
                runs_deleted += run_result.rowcount

                self._log.info(
                    "retention_runs_cleaned",
                    status=status.value,
                    runs_deleted=run_result.rowcount,
                    steps_deleted=step_result.rowcount,
                    cutoff_days=self.config.completed_run_days if status == RunStatus.COMPLETED else self.config.failed_run_days,
                )

        return runs_deleted, steps_deleted

    async def cleanup_events(
        self,
        tenant_id: str | None = None,
        dry_run: bool = False,
    ) -> int:
        """Clean up old events.

        Args:
            tenant_id: Optional tenant to filter cleanup
            dry_run: If True, only count without deleting

        Returns:
            Number of events deleted
        """
        now = datetime.now(timezone.utc)
        events_deleted = 0

        # Processed events (have at least one run)
        processed_cutoff = now - timedelta(days=self.config.processed_event_days)

        # Find old processed events
        query = select(Event.id).where(
            Event.created_at < processed_cutoff,
        )
        if tenant_id:
            query = query.where(Event.tenant_id == tenant_id)

        result = await self.session.execute(query.limit(self.config.batch_size))
        event_ids = [row[0] for row in result.fetchall()]

        if event_ids:
            if dry_run:
                events_deleted = len(event_ids)
            else:
                delete_stmt = delete(Event).where(Event.id.in_(event_ids))
                result = await self.session.execute(delete_stmt)
                events_deleted = result.rowcount

                self._log.info(
                    "retention_events_cleaned",
                    events_deleted=events_deleted,
                    cutoff_days=self.config.processed_event_days,
                )

        return events_deleted

    async def cleanup_audit_logs(
        self,
        tenant_id: str | None = None,
        dry_run: bool = False,
    ) -> int:
        """Clean up old audit logs.

        Args:
            tenant_id: Optional tenant to filter cleanup
            dry_run: If True, only count without deleting

        Returns:
            Number of audit logs deleted
        """
        try:
            from flowforge_server.db.models.audit_log import AuditLog
        except ImportError:
            self._log.debug("audit_log_model_not_available")
            return 0

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.config.audit_log_days)

        query = select(AuditLog.id).where(AuditLog.created_at < cutoff)
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)

        result = await self.session.execute(query.limit(self.config.batch_size))
        log_ids = [row[0] for row in result.fetchall()]

        if not log_ids:
            return 0

        if dry_run:
            return len(log_ids)

        delete_stmt = delete(AuditLog).where(AuditLog.id.in_(log_ids))
        result = await self.session.execute(delete_stmt)
        deleted = result.rowcount

        self._log.info(
            "retention_audit_logs_cleaned",
            logs_deleted=deleted,
            cutoff_days=self.config.audit_log_days,
        )

        return deleted

    async def run_cleanup(
        self,
        tenant_id: str | None = None,
        dry_run: bool = False,
    ) -> RetentionResult:
        """Run full retention cleanup.

        Args:
            tenant_id: Optional tenant to filter cleanup
            dry_run: If True, only count without deleting

        Returns:
            RetentionResult with counts of deleted items
        """
        result = RetentionResult(errors=[])

        try:
            runs, steps = await self.cleanup_runs(tenant_id, dry_run)
            result.runs_deleted = runs
            result.steps_deleted = steps
        except Exception as e:
            result.errors.append(f"Run cleanup error: {e}")
            self._log.error("retention_run_cleanup_error", error=str(e))

        try:
            result.events_deleted = await self.cleanup_events(tenant_id, dry_run)
        except Exception as e:
            result.errors.append(f"Event cleanup error: {e}")
            self._log.error("retention_event_cleanup_error", error=str(e))

        try:
            result.audit_logs_deleted = await self.cleanup_audit_logs(tenant_id, dry_run)
        except Exception as e:
            result.errors.append(f"Audit log cleanup error: {e}")
            self._log.error("retention_audit_cleanup_error", error=str(e))

        if not dry_run:
            await self.session.commit()

        self._log.info(
            "retention_cleanup_complete",
            dry_run=dry_run,
            runs_deleted=result.runs_deleted,
            steps_deleted=result.steps_deleted,
            events_deleted=result.events_deleted,
            audit_logs_deleted=result.audit_logs_deleted,
            total_deleted=result.total_deleted,
            errors=len(result.errors) if result.errors else 0,
        )

        return result

    async def get_retention_stats(
        self,
        tenant_id: str | None = None,
    ) -> dict:
        """Get statistics about data that would be cleaned up.

        Args:
            tenant_id: Optional tenant to filter

        Returns:
            Dict with counts of items eligible for cleanup
        """
        result = await self.run_cleanup(tenant_id, dry_run=True)
        return {
            "eligible_for_cleanup": {
                "runs": result.runs_deleted,
                "steps": result.steps_deleted,
                "events": result.events_deleted,
                "audit_logs": result.audit_logs_deleted,
                "total": result.total_deleted,
            },
            "retention_config": {
                "completed_run_days": self.config.completed_run_days,
                "failed_run_days": self.config.failed_run_days,
                "cancelled_run_days": self.config.cancelled_run_days,
                "processed_event_days": self.config.processed_event_days,
                "audit_log_days": self.config.audit_log_days,
            },
        }
