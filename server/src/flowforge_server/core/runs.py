"""Run lifecycle management service."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from flowforge_server.db.models import Function, Run, RunStatus, Step, StepStatus
from flowforge_server.queue import FairQueue


class RunService:
    """
    Service for managing function run lifecycle.

    Handles:
    - Run creation and status management
    - Step management
    - Run replay and cancellation
    """

    def __init__(self) -> None:
        self.queue = FairQueue()

    async def create_run(
        self,
        session: AsyncSession,
        function: Function,
        trigger_type: str,
        trigger_data: dict[str, Any],
        event_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> Run:
        """
        Create a new function run.

        Args:
            session: Database session.
            function: The function to run.
            trigger_type: How the run was triggered.
            trigger_data: The trigger data (event, cron info, etc.).
            event_id: Optional triggering event ID.
            idempotency_key: Optional key for deduplication.

        Returns:
            The created Run.
        """
        # Check for duplicate if idempotency key provided
        if idempotency_key:
            existing = await session.execute(
                select(Run).where(
                    Run.tenant_id == function.tenant_id,
                    Run.idempotency_key == idempotency_key,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Run with idempotency key '{idempotency_key}' already exists")

        run = Run(
            tenant_id=function.tenant_id,
            function_id=function.id,
            event_id=event_id,
            idempotency_key=idempotency_key,
            status=RunStatus.PENDING,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            max_attempts=function.retries,
        )

        session.add(run)
        await session.flush()
        await session.refresh(run)

        return run

    async def start_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
    ) -> Run | None:
        """Mark a run as started."""
        run = await self.get_run(session, run_id)
        if not run:
            return None

        if run.status != RunStatus.PENDING:
            return run

        run.status = RunStatus.RUNNING
        run.started_at = datetime.utcnow()

        await session.commit()
        return run

    async def complete_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        output: Any = None,
    ) -> Run | None:
        """Mark a run as completed."""
        run = await self.get_run(session, run_id)
        if not run:
            return None

        run.status = RunStatus.COMPLETED
        run.output = output
        run.ended_at = datetime.utcnow()

        await session.commit()
        return run

    async def fail_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        error: dict[str, Any],
        retry: bool = True,
    ) -> tuple[Run | None, bool]:
        """
        Mark a run as failed.

        Returns:
            Tuple of (run, will_retry).
        """
        run = await self.get_run(session, run_id)
        if not run:
            return None, False

        run.error = error
        will_retry = retry and run.attempt < run.max_attempts

        if will_retry:
            run.attempt += 1
            # Don't change status - will be re-queued
        else:
            run.status = RunStatus.FAILED
            run.ended_at = datetime.utcnow()

        await session.commit()
        return run, will_retry

    async def pause_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        resume_at: datetime | None = None,
    ) -> Run | None:
        """Pause a run (for sleep or wait_for_event)."""
        run = await self.get_run(session, run_id)
        if not run:
            return None

        run.status = RunStatus.PAUSED
        run.resume_at = resume_at

        await session.commit()
        return run

    async def resume_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
    ) -> Run | None:
        """Resume a paused run."""
        run = await self.get_run(session, run_id)
        if not run:
            return None

        if run.status != RunStatus.PAUSED:
            return run

        run.status = RunStatus.RUNNING
        run.resume_at = None

        await session.commit()
        return run

    async def cancel_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
    ) -> Run | None:
        """Cancel a run."""
        run = await self.get_run(session, run_id)
        if not run:
            return None

        if run.is_terminal:
            raise ValueError(f"Cannot cancel run with status '{run.status}'")

        run.status = RunStatus.CANCELLED
        run.ended_at = datetime.utcnow()

        await session.commit()
        return run

    async def replay_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
    ) -> Run | None:
        """
        Replay a run by creating a new run with the same trigger data.
        """
        original = await self.get_run(session, run_id, include_function=True)
        if not original:
            return None

        new_run = Run(
            tenant_id=original.tenant_id,
            function_id=original.function_id,
            event_id=original.event_id,
            status=RunStatus.PENDING,
            trigger_type=original.trigger_type,
            trigger_data=original.trigger_data,
            max_attempts=original.max_attempts,
        )

        session.add(new_run)
        await session.flush()
        await session.refresh(new_run)

        return new_run

    async def get_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        include_steps: bool = False,
        include_function: bool = False,
    ) -> Run | None:
        """Get a run by ID."""
        query = select(Run).where(Run.id == run_id)

        if include_steps:
            query = query.options(selectinload(Run.steps))
        if include_function:
            query = query.options(selectinload(Run.function))

        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def list_runs(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        function_id: uuid.UUID | None = None,
        status: RunStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Run]:
        """List runs with optional filtering."""
        query = select(Run).where(Run.tenant_id == tenant_id)

        if function_id:
            query = query.where(Run.function_id == function_id)
        if status:
            query = query.where(Run.status == status)

        query = query.order_by(Run.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def add_step(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        step_id: str,
        step_hash: str,
        step_type: str,
        output: Any = None,
        status: StepStatus = StepStatus.COMPLETED,
    ) -> Step:
        """Add a step to a run."""
        step = Step(
            run_id=run_id,
            step_id=step_id,
            step_hash=step_hash,
            step_type=step_type,
            status=status,
            output=output,
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow() if status == StepStatus.COMPLETED else None,
        )

        session.add(step)
        await session.flush()
        return step

    async def get_completed_steps(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get completed step results for memoization."""
        result = await session.execute(
            select(Step).where(
                Step.run_id == run_id,
                Step.status == StepStatus.COMPLETED,
            )
        )

        steps = result.scalars().all()
        return {
            step.step_hash: step.output
            for step in steps
            if step.output is not None
        }

    async def close(self) -> None:
        """Close resources."""
        await self.queue.close()
