"""Runner service - event consumer and job scheduler."""

import asyncio
import signal
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.config import get_settings
from flowforge_server.db import get_session_context
from flowforge_server.db.models import Function, Run, RunStatus, Step, StepStatus
from flowforge_server.queue import FairQueue, Job
from flowforge_server.stream import RedisEventStream, StreamMessage


class Runner:
    """
    Runner service - consumes events and schedules function runs.

    The Runner is responsible for:
    - Consuming events from the event stream
    - Matching events to registered functions
    - Creating run records in the database
    - Enqueueing jobs for the Executor
    - Handling cron-triggered functions
    - Managing run lifecycle
    """

    def __init__(
        self,
        consumer_group: str = "runners",
        consumer_name: str | None = None,
    ) -> None:
        """
        Initialize the Runner.

        Args:
            consumer_group: Consumer group for event stream.
            consumer_name: Unique name for this runner instance.
        """
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name or f"runner-{uuid.uuid4().hex[:8]}"

        self.settings = get_settings()
        self.event_stream = RedisEventStream()
        self.queue = FairQueue()

        self._running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the runner service."""
        print(f"[Runner] Starting {self.consumer_name}...")

        self._running = True

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        try:
            await asyncio.gather(
                self._consume_events(),
                self._process_scheduled_runs(),
                self._recover_pending_messages(),
            )
        except asyncio.CancelledError:
            print("[Runner] Cancelled")
        finally:
            await self._cleanup()

    def _handle_shutdown(self) -> None:
        """Handle shutdown signals."""
        print("[Runner] Shutdown requested...")
        self._running = False
        self._shutdown_event.set()

    async def _cleanup(self) -> None:
        """Clean up resources."""
        print("[Runner] Cleaning up...")
        await self.event_stream.close()
        await self.queue.close()

    async def _consume_events(self) -> None:
        """Main event consumption loop."""
        print("[Runner] Consuming events from stream...")

        while self._running:
            try:
                # Get messages from stream
                messages = await self.event_stream.subscribe(
                    consumer_group=self.consumer_group,
                    consumer_name=self.consumer_name,
                    count=10,
                    block_ms=5000,
                )

                for message in messages:
                    await self._process_event(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Runner] Error consuming events: {e}")
                await asyncio.sleep(1)

    async def _process_event(self, message: StreamMessage) -> None:
        """Process a single event message."""
        try:
            print(f"[Runner] Processing event: {message.event_name} ({message.event_id})")

            async with get_session_context() as session:
                # Check if run was pre-created by API (for immediate run_id response)
                if message.run_id:
                    # Use existing run - just enqueue the job
                    run_result = await session.execute(
                        select(Run).where(Run.id == uuid.UUID(message.run_id))
                    )
                    run = run_result.scalar_one_or_none()

                    if run:
                        # Get the function
                        fn_result = await session.execute(
                            select(Function).where(Function.id == run.function_id)
                        )
                        fn = fn_result.scalar_one_or_none()

                        if fn:
                            await self._enqueue_run(run, fn)
                            print(f"[Runner] Enqueued pre-created run {run.id} for function {fn.function_id}")
                        else:
                            print(f"[Runner] Function not found for run {run.id}")
                    else:
                        print(f"[Runner] Pre-created run {message.run_id} not found")
                else:
                    # No pre-created run - find matching functions and create runs
                    functions = await self._find_matching_functions(
                        session,
                        message.event_name,
                        message.tenant_id,
                    )

                    for fn in functions:
                        # Check if function matches filter expression
                        if fn.trigger_expression:
                            if not self._evaluate_expression(
                                fn.trigger_expression,
                                message.event_data,
                            ):
                                continue

                        # Create run
                        run = await self._create_run(
                            session,
                            fn,
                            message,
                        )

                        # Enqueue job for executor
                        await self._enqueue_run(run, fn)

                        print(f"[Runner] Created run {run.id} for function {fn.function_id}")

                # Resolve any waiting steps that match this event
                await self._resolve_waiting_steps(
                    session,
                    message.event_name,
                    message.event_data,
                    message.tenant_id,
                )

            # Acknowledge the message
            if message.stream_id:
                await self.event_stream.acknowledge_for_group(
                    self.consumer_group,
                    [message.stream_id],
                )

        except Exception as e:
            print(f"[Runner] Error processing event: {e}")
            # Don't acknowledge - message will be redelivered

    async def _find_matching_functions(
        self,
        session: AsyncSession,
        event_name: str,
        tenant_id: str,
    ) -> list[Function]:
        """Find functions that match the event."""
        result = await session.execute(
            select(Function).where(
                Function.tenant_id == uuid.UUID(tenant_id) if tenant_id else True,
                Function.trigger_type == "event",
                Function.trigger_value == event_name,
                Function.is_active == True,
            )
        )
        return list(result.scalars().all())

    def _evaluate_expression(
        self,
        expression: str,
        event_data: dict[str, Any],
    ) -> bool:
        """
        Evaluate a filter expression against event data.

        Simple implementation - in production, use a proper expression evaluator.
        """
        # TODO: Implement proper expression evaluation (CEL, JSONPath, etc.)
        return True

    @staticmethod
    def _evaluate_match_expression(
        expression: str,
        event_data: dict[str, Any],
    ) -> bool:
        """
        Evaluate a wait_for_event match expression against event data.

        Supports format: "data.field.path == 'value'" or "data.field == 123"
        Uses safe dot-path traversal — no eval().
        """
        expression = expression.strip()
        if "==" not in expression:
            return False

        left_raw, right_raw = expression.split("==", 1)
        left_path = left_raw.strip()
        right_literal = right_raw.strip()

        # Strip surrounding quotes from the right-hand value
        if (
            (right_literal.startswith("'") and right_literal.endswith("'"))
            or (right_literal.startswith('"') and right_literal.endswith('"'))
        ):
            right_value: Any = right_literal[1:-1]
        else:
            # Try numeric
            try:
                right_value = int(right_literal)
            except ValueError:
                try:
                    right_value = float(right_literal)
                except ValueError:
                    right_value = right_literal

        # Resolve dot-path against event data
        # If path starts with "data.", strip that prefix since event_data IS the data
        parts = left_path.split(".")
        if parts and parts[0] == "data":
            parts = parts[1:]

        current: Any = event_data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False

        return str(current) == str(right_value)

    async def _resolve_waiting_steps(
        self,
        session: AsyncSession,
        event_name: str,
        event_data: dict[str, Any],
        tenant_id: str,
    ) -> None:
        """
        Find waiting steps that match the incoming event and resume their runs.
        """
        if not tenant_id:
            return

        # Query steps that are waiting for this event name
        # Join with Run to filter by tenant and ensure run is paused
        result = await session.execute(
            select(Step)
            .join(Run, Step.run_id == Run.id)
            .where(
                Step.status == StepStatus.WAITING,
                Step.wait_event_name == event_name,
                Run.tenant_id == uuid.UUID(tenant_id),
                Run.status == RunStatus.PAUSED,
            )
        )
        waiting_steps = result.scalars().all()

        now = datetime.now(UTC)

        for step in waiting_steps:
            # Evaluate match expression if present
            if step.wait_expression:
                if not self._evaluate_match_expression(step.wait_expression, event_data):
                    continue

            # Mark step as completed with event data
            step.status = StepStatus.COMPLETED
            step.output = event_data
            step.ended_at = now

            # Resume the parent run
            run_result = await session.execute(
                select(Run).where(Run.id == step.run_id)
            )
            run = run_result.scalar_one_or_none()

            if not run:
                continue

            run.status = RunStatus.RUNNING
            run.resume_at = None

            # Get the function to enqueue
            fn_result = await session.execute(
                select(Function).where(Function.id == run.function_id)
            )
            fn = fn_result.scalar_one_or_none()

            if fn:
                await self._enqueue_run(run, fn)
                print(f"[Runner] Resolved wait step '{step.step_id}' on run {run.id} — resuming")

    async def _create_run(
        self,
        session: AsyncSession,
        fn: Function,
        message: StreamMessage,
    ) -> Run:
        """Create a new run record."""
        run = Run(
            tenant_id=fn.tenant_id,
            function_id=fn.id,
            status=RunStatus.PENDING,
            trigger_type="event",
            trigger_data={
                "event": {
                    "id": message.event_id,
                    "name": message.event_name,
                    "data": message.event_data,
                    "timestamp": message.timestamp.isoformat(),
                }
            },
            max_attempts=fn.retries,
        )

        session.add(run)
        await session.flush()
        await session.refresh(run)

        return run

    async def _enqueue_run(self, run: Run, fn: Function) -> None:
        """Enqueue a job for the executor."""
        job = Job(
            job_type="execute_run",
            run_id=str(run.id),
            function_id=fn.function_id,
            tenant_id=str(run.tenant_id),
            data={
                "function_uuid": str(fn.id),
                "endpoint_url": fn.endpoint_url,
                "config": fn.config,
                "trigger_data": run.trigger_data,
            },
            max_attempts=fn.retries,
        )

        await self.queue.enqueue(job)

    async def _process_scheduled_runs(self) -> None:
        """Process runs that are scheduled to resume (sleep, etc.)."""
        print("[Runner] Starting scheduled run processor...")

        while self._running:
            try:
                async with get_session_context() as session:
                    # Find runs that are paused and due to resume
                    now = datetime.now(UTC)
                    result = await session.execute(
                        select(Run).where(
                            Run.status == RunStatus.PAUSED,
                            Run.resume_at <= now,
                        ).limit(100)
                    )

                    runs = result.scalars().all()

                    for run in runs:
                        # Resume the run
                        run.status = RunStatus.RUNNING
                        run.resume_at = None

                        # Get function
                        fn_result = await session.execute(
                            select(Function).where(Function.id == run.function_id)
                        )
                        fn = fn_result.scalar_one_or_none()

                        if fn:
                            await self._enqueue_run(run, fn)
                            print(f"[Runner] Resumed run {run.id}")

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Runner] Error processing scheduled runs: {e}")
                await asyncio.sleep(5)

    async def _recover_pending_messages(self) -> None:
        """Recover and reprocess pending messages that weren't acknowledged."""
        print("[Runner] Starting pending message recovery...")

        while self._running:
            try:
                # Get pending messages older than 30 seconds
                pending = await self.event_stream.get_pending(
                    self.consumer_group,
                    count=10,
                )

                for message in pending:
                    print(f"[Runner] Recovering pending message: {message.event_id}")
                    await self._process_event(message)

                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Runner] Error recovering pending messages: {e}")
                await asyncio.sleep(30)


async def main() -> None:
    """Main entry point for the runner service."""
    runner = Runner()
    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())
