"""Executor service - job worker that invokes functions."""

import asyncio
import signal
import traceback
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from flowforge_server.config import get_settings
from flowforge_server.db import get_session_context
from flowforge_server.db.models import (
    Function,
    Run,
    RunStatus,
    Step,
    StepStatus,
    StepType,
    UsageRecord,
)
from flowforge_server.queue import FairQueue, Job
from flowforge_server.services import notifier as notifier_service
from flowforge_server.services.ai import AIService, get_ai_service
from flowforge_server.stream.pubsub import RunEventType, publish_run_event


def _parse_timeout_to_seconds(s: str | None) -> int | None:
    """Parse a duration string like '30s' / '5m' / '1h' to seconds.

    Returns None on failure. Mirrors inline_executor._parse_timeout but at
    module scope so executor's worker-mode path can resolve the same way.
    """
    if not s:
        return None
    try:
        s = str(s).strip()
        if s.endswith("h"):
            return int(s[:-1]) * 3600
        if s.endswith("m"):
            return int(s[:-1]) * 60
        if s.endswith("s"):
            return int(s[:-1])
        return int(s)
    except (ValueError, TypeError):
        return None


def _fire_run_failed_notification(run_id: Any) -> None:
    """Schedule a fire-and-forget notification dispatch.

    Wrapped so a missing event loop (e.g. during sync teardown) doesn't crash
    the executor. The notifier itself is exception-safe.
    """
    try:
        asyncio.create_task(notifier_service.notify_run_failed(run_id))
    except RuntimeError:
        # No running event loop — best-effort skip.
        pass

if TYPE_CHECKING:
    from flowforge_server.services.inline_executor import InlineExecutor
    from flowforge_server.stream import RedisEventStream


class Executor:
    """
    Executor service - processes jobs by invoking user functions.

    The Executor is responsible for:
    - Dequeuing jobs from the fair queue
    - Invoking user functions via HTTP
    - Processing step results
    - Handling retries and failures
    - Managing step state (sleep, wait_for_event, etc.)
    """

    def __init__(
        self,
        worker_id: str | None = None,
        concurrency: int = 10,
    ) -> None:
        """
        Initialize the Executor.

        Args:
            worker_id: Unique identifier for this worker.
            concurrency: Maximum concurrent job processing.
        """
        self.worker_id = worker_id or f"executor-{uuid.uuid4().hex[:8]}"
        self.concurrency = concurrency

        self.settings = get_settings()
        self.queue = FairQueue()

        self._running = False
        self._shutdown_event = asyncio.Event()
        self._active_jobs: set[str] = set()
        self._http_client: httpx.AsyncClient | None = None
        self._ai_service: AIService | None = None
        self._inline_executor: InlineExecutor | None = None
        self._event_stream: RedisEventStream | None = None
        # Short-TTL cache for per-function rate_limits config so long agent
        # runs (many AI steps on the same function) don't re-query Function
        # on every step. Keyed by function_id, value is
        # (expires_at_monotonic, rate_limits_cfg_or_None).
        self._rate_limits_cache: dict[str, tuple[float, list[dict[str, Any]] | None]] = {}
        self._rate_limits_cache_ttl: float = 30.0

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=300.0,  # 5 minutes for function execution
                    write=10.0,
                    pool=10.0,
                ),
            )
        return self._http_client

    def _get_ai_service(self) -> AIService:
        """Get or create AI service with provider registry."""
        if self._ai_service is None:
            self._ai_service = get_ai_service()
            # Attach provider registry so executor can look up tenant credentials
            if self._ai_service._provider_registry is None:
                from flowforge_server.services.providers import get_provider_registry
                self._ai_service.provider_registry = get_provider_registry()
        return self._ai_service

    def _get_inline_executor(self) -> "InlineExecutor":
        """Get or create inline executor for serverless functions."""
        if self._inline_executor is None:
            from flowforge_server.services.inline_executor import InlineExecutor
            self._inline_executor = InlineExecutor(self._get_ai_service())
        return self._inline_executor

    def _get_event_stream(self) -> "RedisEventStream":
        if self._event_stream is None:
            from flowforge_server.stream import RedisEventStream
            self._event_stream = RedisEventStream()
        return self._event_stream

    async def start(self) -> None:
        """Start the executor service."""
        print(f"[Executor] Starting {self.worker_id} with concurrency={self.concurrency}...")

        self._running = True

        # Recover orphaned runs stuck in "running" state (e.g. from executor restart)
        await self._recover_stuck_runs()

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        try:
            # Create worker tasks
            workers = [
                self._worker(i) for i in range(self.concurrency)
            ]
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            print("[Executor] Cancelled")
        finally:
            await self._cleanup()

    def _handle_shutdown(self) -> None:
        """Handle shutdown signals."""
        print("[Executor] Shutdown requested...")
        self._running = False
        self._shutdown_event.set()

    async def _cleanup(self) -> None:
        """Clean up resources."""
        print("[Executor] Cleaning up...")

        if self._http_client:
            await self._http_client.aclose()

        if self._inline_executor:
            await self._inline_executor.close()

        if self._ai_service:
            await self._ai_service.close()

        await self.queue.close()

    async def _recover_stuck_runs(self) -> None:
        """Re-enqueue runs stuck in 'running' or 'pending' status (orphaned by executor restart)."""
        try:
            async with get_session_context() as session:
                result = await session.execute(
                    select(Run).where(Run.status.in_([RunStatus.RUNNING, RunStatus.PENDING]))
                )
                stuck_runs = result.scalars().all()

                if not stuck_runs:
                    return

                print(f"[Executor] Recovering {len(stuck_runs)} stuck running runs...")

                for run in stuck_runs:
                    # Get the function
                    fn_result = await session.execute(
                        select(Function).where(Function.id == run.function_id)
                    )
                    fn = fn_result.scalar_one_or_none()
                    if not fn:
                        # No function found — mark as failed
                        run.status = RunStatus.FAILED
                        run.error = {"type": "RecoveryError", "message": "Function not found during recovery"}
                        run.ended_at = datetime.utcnow()
                        continue

                    # Re-enqueue the job
                    job = Job(
                        job_type="execute_run",
                        run_id=str(run.id),
                        function_id=fn.function_id,
                        tenant_id=str(run.tenant_id),
                        data={
                            "trigger_data": run.trigger_data or {},
                            "endpoint_url": fn.endpoint_url,
                        },
                        max_attempts=run.max_attempts,
                    )
                    await self.queue.enqueue(job)
                    print(f"[Executor] Re-enqueued stuck run {run.id} (function={fn.function_id})")

                await session.commit()

        except Exception as e:
            print(f"[Executor] Error recovering stuck runs: {e}")

    async def _worker(self, worker_num: int) -> None:
        """Individual worker loop."""
        print(f"[Executor] Worker {worker_num} started")

        while self._running:
            try:
                # Dequeue a job
                job = await self.queue.dequeue(timeout=5)

                if job is None:
                    continue

                self._active_jobs.add(job.id)

                try:
                    await self._process_job(job)
                finally:
                    self._active_jobs.discard(job.id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Executor] Worker {worker_num} error: {e}")
                await asyncio.sleep(1)

    async def _process_job(self, job: Job) -> None:
        """Process a single job."""
        print(f"[Executor] Processing job {job.id} (run={job.run_id})")

        try:
            if job.job_type == "execute_run":
                await self._execute_run(job)
            else:
                print(f"[Executor] Unknown job type: {job.job_type}")
                await self.queue.fail(job.id, f"Unknown job type: {job.job_type}", retry=False)

        except Exception as e:
            print(f"[Executor] Job {job.id} failed: {e}")
            traceback.print_exc()
            await self.queue.fail(job.id, str(e), retry=True)

    async def _execute_run(self, job: Job) -> None:
        """Execute a function run."""
        async with get_session_context() as session:
            # Get run
            run_result = await session.execute(
                select(Run)
                .where(Run.id == uuid.UUID(job.run_id))
                .options(selectinload(Run.steps))
            )
            run = run_result.scalar_one_or_none()

            if not run:
                print(f"[Executor] Run {job.run_id} not found")
                await self.queue.complete(job.id)
                return

            # Check if run is still in a valid state
            if run.status not in (RunStatus.PENDING, RunStatus.RUNNING):
                print(f"[Executor] Run {job.run_id} is {run.status}, skipping")
                await self.queue.complete(job.id)
                return

            # Get function to check if inline
            fn_result = await session.execute(
                select(Function).where(
                    Function.function_id == job.function_id,
                )
            )
            fn = fn_result.scalar_one_or_none()

            # Update run status
            if run.status == RunStatus.PENDING:
                run.status = RunStatus.RUNNING
                run.started_at = datetime.utcnow()
                await session.commit()

                # Publish run started event
                await publish_run_event(
                    str(run.id),
                    RunEventType.RUN_STARTED,
                    {
                        "run_id": str(run.id),
                        "function_id": str(run.function_id),
                        "status": run.status.value,
                        "started_at": run.started_at.isoformat(),
                    },
                )

            # Get trigger data
            trigger_data = job.data.get("trigger_data", {})
            event_data = trigger_data.get("event", {}).get("data", {})

            # Check if function is inline (serverless)
            if fn and fn.is_inline:
                print(f"[Executor] Running inline function {fn.function_id}")

                # Use inline executor
                inline_executor = self._get_inline_executor()
                result = await inline_executor.execute(
                    session=session,
                    fn=fn,
                    run=run,
                    event_data=event_data,
                )
            else:
                # Get completed steps for memoization
                completed_steps = {}
                for step in run.steps:
                    if step.status == StepStatus.COMPLETED and step.output is not None:
                        completed_steps[step.step_hash] = step.output

                # Invoke the function via HTTP (worker mode)
                endpoint_url = job.data.get("endpoint_url")

                # Resolve the step timeout for this invoke cycle:
                # function-level config wins; otherwise fall back to the workspace
                # default (default_step_timeout_s, injected by runner._enqueue_run).
                # Each /invoke call is bounded by one step yield, so this gives a
                # real per-step soft timeout for worker-mode functions.
                fn_cfg = job.data.get("config") or {}
                fn_timeout_str = fn_cfg.get("timeout") if isinstance(fn_cfg, dict) else None
                tenant_default_step_s = (
                    fn_cfg.get("default_step_timeout_s")
                    if isinstance(fn_cfg, dict)
                    else None
                )
                step_timeout_s = (
                    _parse_timeout_to_seconds(fn_timeout_str)
                    if fn_timeout_str
                    else (int(tenant_default_step_s) if tenant_default_step_s else None)
                )

                result = await self._invoke_function(
                    endpoint_url=endpoint_url,
                    function_id=job.function_id,
                    run_id=job.run_id,
                    event=trigger_data.get("event", {}),
                    completed_steps=completed_steps,
                    attempt=run.attempt,
                    step_timeout_s=step_timeout_s,
                )

            # Process result
            await self._handle_result(session, run, job, result)

    async def _invoke_function(
        self,
        endpoint_url: str,
        function_id: str,
        run_id: str,
        event: dict[str, Any],
        completed_steps: dict[str, Any],
        attempt: int,
        step_timeout_s: int | None = None,
    ) -> dict[str, Any]:
        """Invoke a user function via HTTP.

        When `step_timeout_s` is set, the per-invoke read timeout is overridden
        on this single call so a stuck step yields control instead of riding
        the long client-default. Also forwarded in the payload as a hint so
        SDKs can self-enforce.
        """
        client = await self._get_http_client()

        payload = {
            "function_id": function_id,
            "run_id": run_id,
            "event": event,
            "steps": completed_steps,
            "attempt": attempt,
        }
        if step_timeout_s is not None:
            payload["step_timeout_s"] = step_timeout_s

        # Per-call timeout override. Generous connect/write/pool, tight read.
        request_timeout: httpx.Timeout | None = None
        if step_timeout_s is not None and step_timeout_s > 0:
            request_timeout = httpx.Timeout(
                connect=10.0,
                read=float(step_timeout_s),
                write=10.0,
                pool=10.0,
            )

        try:
            response = await client.post(
                f"{endpoint_url}/invoke",
                json=payload,
                timeout=request_timeout if request_timeout is not None else httpx.USE_CLIENT_DEFAULT,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "error": {
                    "type": "HTTPError",
                    "message": f"HTTP {e.response.status_code}: {e.response.text}",
                    "retryable": e.response.status_code >= 500,
                },
            }
        except httpx.RequestError as e:
            return {
                "status": "error",
                "error": {
                    "type": "RequestError",
                    "message": str(e),
                    "retryable": True,
                },
            }

    async def _handle_result(
        self,
        session: AsyncSession,
        run: Run,
        job: Job,
        result: dict[str, Any],
    ) -> None:
        """Handle the result of a function invocation."""
        status = result.get("status")

        if status == "function_complete":
            # Function completed successfully
            run.status = RunStatus.COMPLETED
            run.output = result.get("output")
            run.ended_at = datetime.utcnow()

            await session.commit()
            await self.queue.complete(job.id)

            # Publish run completed event
            await publish_run_event(
                str(run.id),
                RunEventType.RUN_COMPLETED,
                {
                    "run_id": str(run.id),
                    "status": run.status.value,
                    "output": run.output,
                    "ended_at": run.ended_at.isoformat(),
                },
            )

            print(f"[Executor] Run {run.id} completed")

            # Sync linked task status
            await self._sync_task_on_run_end(session, run, success=True)

        elif status == "step_complete":
            # Step completed, process and continue
            step_id = result.get("step_id")
            step_hash = result.get("step_hash")
            step_result = result.get("step_result")
            step_started_at = result.get("started_at")  # ISO 8601 from SDK

            # Create or update step record
            step = await self._save_step(
                session,
                run,
                step_id,
                step_hash,
                step_result,
                started_at=step_started_at,
            )

            # Handle special step types
            if isinstance(step_result, dict) and "type" in step_result:
                handled = await self._handle_special_step(
                    session, run, job, step, step_result
                )
                if handled:
                    return

            # Re-enqueue to continue execution
            await session.commit()
            await self.queue.complete(job.id)

            # Create new job for continuation
            new_job = Job(
                job_type="execute_run",
                run_id=str(run.id),
                function_id=job.function_id,
                tenant_id=job.tenant_id,
                data=job.data,
                max_attempts=job.max_attempts,
            )
            await self.queue.enqueue(new_job)

            # Publish step completed event
            await publish_run_event(
                str(run.id),
                RunEventType.STEP_COMPLETED,
                {
                    "run_id": str(run.id),
                    "step_id": step_id,
                    "step_type": step.step_type.value if step.step_type else "run",
                    "output": step.output,
                },
            )

            print(f"[Executor] Run {run.id} step '{step_id}' completed, continuing")

        elif status == "error":
            # Error occurred
            error = result.get("error", {})
            retryable = error.get("retryable", False)

            if retryable and run.attempt < run.max_attempts:
                # Retry
                run.attempt += 1
                run.error = error
                await session.commit()

                await self.queue.fail(job.id, error.get("message", "Unknown error"), retry=True)
                print(f"[Executor] Run {run.id} failed, will retry (attempt {run.attempt})")
            else:
                # Permanent failure
                run.status = RunStatus.FAILED
                run.error = error
                run.ended_at = datetime.utcnow()
                await session.commit()

                await self.queue.fail(job.id, error.get("message", "Unknown error"), retry=False)

                # Publish run failed event
                await publish_run_event(
                    str(run.id),
                    RunEventType.RUN_FAILED,
                    {
                        "run_id": str(run.id),
                        "status": run.status.value,
                        "error": run.error,
                        "ended_at": run.ended_at.isoformat(),
                    },
                )

                # Fire workspace notifications (Slack / PagerDuty).
                # Fire-and-forget — must not block run completion.
                _fire_run_failed_notification(run.id)

                print(f"[Executor] Run {run.id} permanently failed")

                # Sync linked task status
                await self._sync_task_on_run_end(session, run, success=False)

        else:
            print(f"[Executor] Unknown result status: {status}")
            await self.queue.complete(job.id)

    async def _sync_task_on_run_end(
        self, session: AsyncSession, run: Run, *, success: bool
    ) -> None:
        """Update linked task when run completes or fails."""
        try:
            from flowforge_server.services.task_service import TaskService
            task_service = TaskService(event_stream=self._get_event_stream())
            if success:
                await task_service.on_run_completed(session, run)
            else:
                await task_service.on_run_failed(session, run)
        except Exception as e:
            print(f"[Executor] Task sync failed for run {run.id}: {e}")

    def _sanitize_output(self, value: Any) -> Any:
        """Recursively strip null bytes from strings so PostgreSQL JSONB accepts the value."""
        if isinstance(value, str):
            return value.replace("\x00", "")
        if isinstance(value, dict):
            return {k: self._sanitize_output(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._sanitize_output(v) for v in value]
        return value

    async def _save_step(
        self,
        session: AsyncSession,
        run: Run,
        step_id: str,
        step_hash: str,
        step_result: Any,
        started_at: str | None = None,
    ) -> Step:
        """Save a step result to the database.

        Args:
            started_at: ISO 8601 timestamp from the SDK indicating when the step
                        actually started executing on the worker. If provided, this
                        gives accurate step duration for the waterfall timeline.
        """
        step_result = self._sanitize_output(step_result)

        # Parse started_at from SDK if provided (ISO 8601 string)
        sdk_started_at = None
        if started_at:
            try:
                parsed = datetime.fromisoformat(started_at)
                # Strip timezone to match datetime.utcnow() (naive UTC)
                sdk_started_at = parsed.replace(tzinfo=None) if parsed.tzinfo is None else parsed.astimezone().replace(tzinfo=None)
            except (ValueError, TypeError):
                sdk_started_at = None

        now = datetime.utcnow()

        # Check if step exists
        existing = None
        for s in run.steps:
            if s.step_hash == step_hash:
                existing = s
                break

        if existing:
            existing.status = StepStatus.COMPLETED
            existing.output = step_result
            existing.ended_at = now
            # Update started_at if SDK provided a more accurate timestamp
            if sdk_started_at and (existing.started_at is None or existing.started_at == existing.ended_at):
                existing.started_at = sdk_started_at
            return existing
        else:
            # Determine step type
            step_type = StepType.RUN
            if isinstance(step_result, dict) and "type" in step_result:
                type_mapping = {
                    "sleep": StepType.SLEEP,
                    "ai": StepType.AI,
                    "wait_for_event": StepType.WAIT_FOR_EVENT,
                    "invoke": StepType.INVOKE,
                    "send_event": StepType.SEND_EVENT,
                }
                step_type = type_mapping.get(step_result["type"], StepType.RUN)

            step = Step(
                run_id=run.id,
                step_id=step_id,
                step_hash=step_hash,
                step_type=step_type,
                status=StepStatus.COMPLETED,
                output=step_result,
                started_at=sdk_started_at or now,
                ended_at=now,
            )
            session.add(step)
            run.steps.append(step)
            return step

    async def _get_rate_limits_cfg(
        self,
        session: AsyncSession,
        function_id_str: str,
        function_pk: Any,
    ) -> list[dict[str, Any]] | None:
        """
        Fetch the ``rate_limits`` block from a Function's config with a short
        TTL cache, so back-to-back AI steps on the same function don't
        re-query the DB. Cache TTL is ~30s (self._rate_limits_cache_ttl).

        ``function_id_str`` is the cache key (the user-facing string id);
        ``function_pk`` is the PK UUID used in the fallback SELECT.
        """
        now = asyncio.get_event_loop().time()
        cached = self._rate_limits_cache.get(function_id_str)
        if cached and cached[0] > now:
            return cached[1]

        cfg: list[dict[str, Any]] | None = None
        try:
            fn_row = await session.execute(
                select(Function).where(Function.id == function_pk)
            )
            fn_obj = fn_row.scalar_one_or_none()
            if fn_obj and isinstance(fn_obj.config, dict):
                cfg = fn_obj.config.get("rate_limits")
        except Exception:
            cfg = None

        self._rate_limits_cache[function_id_str] = (
            now + self._rate_limits_cache_ttl,
            cfg,
        )
        return cfg

    async def _handle_special_step(
        self,
        session: AsyncSession,
        run: Run,
        job: Job,
        step: Step,
        step_result: dict[str, Any],
    ) -> bool:
        """
        Handle special step types that affect execution flow.

        Returns True if the step was handled and execution should not continue.
        """
        step_type = step_result.get("type")

        if step_type == "sleep":
            # Schedule wake-up
            duration_seconds = step_result.get("duration_seconds", 0)
            resume_at = datetime.utcnow() + timedelta(seconds=duration_seconds)

            run.status = RunStatus.PAUSED
            run.resume_at = resume_at

            step.status = StepStatus.SLEEPING
            step.scheduled_at = resume_at

            await session.commit()
            await self.queue.complete(job.id)

            # Publish run paused event
            await publish_run_event(
                str(run.id),
                RunEventType.RUN_PAUSED,
                {
                    "run_id": str(run.id),
                    "step_id": step.step_id,
                    "reason": "sleep",
                    "duration_seconds": duration_seconds,
                    "resume_at": resume_at.isoformat(),
                },
            )

            print(f"[Executor] Run {run.id} sleeping for {duration_seconds}s")
            return True

        elif step_type == "wait_for_event":
            # Wait for external event
            event_name = step_result.get("event")
            match_expr = step_result.get("match")
            timeout_seconds = step_result.get("timeout_seconds")

            run.status = RunStatus.PAUSED
            if timeout_seconds:
                run.resume_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)

            step.status = StepStatus.WAITING
            step.wait_event_name = event_name
            step.wait_expression = match_expr
            if timeout_seconds:
                step.wait_timeout_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)

            await session.commit()
            await self.queue.complete(job.id)

            # Publish appropriate event based on event type
            if event_name and "approval" in event_name.lower():
                await publish_run_event(
                    str(run.id),
                    RunEventType.APPROVAL_REQUIRED,
                    {
                        "run_id": str(run.id),
                        "step_id": step.step_id,
                        "event_name": event_name,
                        "match_expression": match_expr,
                        "timeout_at": step.wait_timeout_at.isoformat() if step.wait_timeout_at else None,
                    },
                )
            else:
                await publish_run_event(
                    str(run.id),
                    RunEventType.RUN_PAUSED,
                    {
                        "run_id": str(run.id),
                        "step_id": step.step_id,
                        "reason": "wait_for_event",
                        "event_name": event_name,
                        "match_expression": match_expr,
                        "timeout_at": step.wait_timeout_at.isoformat() if step.wait_timeout_at else None,
                    },
                )

            print(f"[Executor] Run {run.id} waiting for event '{event_name}'")
            return True

        elif step_type == "ai":
            # AI step - execute LLM call via AIService
            model = step_result.get("model", "gpt-5.3")
            messages = step_result.get("messages", [])
            temperature = step_result.get("temperature", 0.7)
            max_tokens = step_result.get("max_tokens", 1000)
            use_cache = step_result.get("use_cache", True)
            tools = step_result.get("tools")
            # Only send tool_choice when tools are present — Anthropic rejects
            # tool_choice without a tools list (e.g. wrap-up step has no tools).
            tool_choice = step_result.get("tool_choice", "auto") if tools else None

            # Publish thinking event before LLM call
            await publish_run_event(
                str(run.id),
                RunEventType.THINKING,
                {
                    "run_id": str(run.id),
                    "step_id": step.step_id,
                    "model": model,
                    "status": "started",
                },
            )

            # Look up declarative TokenRateLimits on the function for pre-flight
            # token-bucket throttling. Reuses the Function.config JSONB blob.
            # Cached per-function with a short TTL so long agent runs (many
            # AI steps on the same function) don't hit the DB on every step.
            rate_limits_cfg = await self._get_rate_limits_cfg(
                session, job.function_id, run.function_id
            )

            # Resolve a soft step timeout for this AI call. Step-level value (if
            # the SDK passed one) wins; otherwise function-level `timeout`; final
            # fallback is the tenant default injected by runner._enqueue_run.
            step_level_timeout = step_result.get("timeout_seconds")
            fn_cfg_blob = job.data.get("config") or {}
            fn_timeout = (
                _parse_timeout_to_seconds(fn_cfg_blob.get("timeout"))
                if isinstance(fn_cfg_blob, dict)
                else None
            )
            tenant_default = (
                int(fn_cfg_blob.get("default_step_timeout_s"))
                if isinstance(fn_cfg_blob, dict) and fn_cfg_blob.get("default_step_timeout_s")
                else None
            )
            ai_step_timeout_s: int | None = (
                step_level_timeout if step_level_timeout else (fn_timeout or tenant_default)
            )

            try:
                # Execute the AI call via LiteLLM with tenant-specific credentials
                ai_service = self._get_ai_service()
                ai_call = ai_service.complete(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_cache=use_cache,
                    tools=tools,
                    tool_choice=tool_choice,
                    tenant_id=run.tenant_id,
                    session=session,
                    function_id=job.function_id,
                    rate_limits=rate_limits_cfg,
                )
                if ai_step_timeout_s and ai_step_timeout_s > 0:
                    response = await asyncio.wait_for(ai_call, timeout=ai_step_timeout_s)
                else:
                    response = await ai_call

                # Detect the structured rate-limit marker. AIService returns
                # this instead of raising on 429 so the SDK's step.ai loop can
                # durably sleep + retry via step.sleep (freeing the worker).
                raw = response.raw_response or {}
                if raw.get("__rate_limited"):
                    ai_response = {
                        "__rate_limited": True,
                        "__retry_after": raw.get("__retry_after"),
                        "__provider": raw.get("__provider") or response.provider,
                        "__model": raw.get("__model") or model,
                        "__error": raw.get("__error"),
                    }
                    # Track the retry for observability. The SDK loop will emit
                    # a step.sleep next, then re-attempt.
                    try:
                        from flowforge_server.telemetry.metrics import (
                            track_llm_retry,
                        )

                        track_llm_retry(
                            provider=ai_response["__provider"],
                            model=ai_response["__model"],
                            reason="rate_limit",
                        )
                    except Exception:
                        pass
                    print(
                        f"[Executor] AI step rate-limited: model={model} "
                        f"retry_after={ai_response['__retry_after']}s "
                        f"step_id={step.step_id}"
                    )
                    # Publish an SSE event so the live-activity panel reacts.
                    try:
                        await publish_run_event(
                            str(run.id),
                            RunEventType.THINKING,
                            {
                                "run_id": str(run.id),
                                "step_id": step.step_id,
                                "model": model,
                                "status": "rate_limited",
                                "retry_after": ai_response["__retry_after"],
                            },
                        )
                    except Exception:
                        pass
                    # Skip UsageRecord: no tokens consumed.
                else:
                    # Normal successful AI response.
                    ai_response = response.to_dict()

                    usage_record = UsageRecord(
                        tenant_id=run.tenant_id,
                        run_id=run.id,
                        model=response.usage.model or model,
                        provider=response.usage.provider or response.provider,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        cost_usd=response.usage.cost_usd,
                        latency_ms=response.usage.latency_ms,
                        request_type="completion" if not tools else "tool_call",
                        extra_data={
                            "step_id": step.step_id,
                            "tool_calls_count": len(response.tool_calls) if response.tool_calls else 0,
                        },
                    )
                    session.add(usage_record)

                    tool_calls_info = ""
                    if response.tool_calls:
                        tool_calls_info = f", tools_called={len(response.tool_calls)}"

                    print(
                        f"[Executor] AI step completed: model={model}, "
                        f"tokens={response.usage.total_tokens}, "
                        f"cost=${response.usage.cost_usd:.6f}, "
                        f"latency={response.usage.latency_ms}ms"
                        f"{tool_calls_info}"
                    )

            except ImportError as e:
                # LiteLLM not installed - fall back to simulated response
                print(f"[Executor] LiteLLM not available, simulating AI response: {e}")
                ai_response = {
                    "content": f"[Simulated response from {model} - install litellm for real LLM calls]",
                    "model": model,
                    "provider": "simulated",
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150,
                        "cost_usd": 0.0,
                        "latency_ms": 0,
                    },
                    "finish_reason": "stop",
                }

            except Exception as e:
                # LLM call failed - mark step as failed and retry
                print(f"[Executor] AI step failed: {e}")
                step.status = StepStatus.FAILED
                step.error = {"type": type(e).__name__, "message": str(e)}

                will_retry = await self.queue.fail(job.id, str(e), retry=True)

                if not will_retry:
                    # Job exhausted retries — mark the run as failed too
                    run.status = RunStatus.FAILED
                    run.error = {"type": type(e).__name__, "message": str(e)}
                    run.ended_at = datetime.utcnow()
                    print(f"[Executor] Run {run.id} failed permanently (AI step error, no retries left)")

                await session.commit()
                if not will_retry:
                    _fire_run_failed_notification(run.id)
                return True

            # Update step with actual result
            step.output = ai_response

            await session.commit()
            await self.queue.complete(job.id)

            # Publish AI step completed event
            await publish_run_event(
                str(run.id),
                RunEventType.STEP_COMPLETED,
                {
                    "run_id": str(run.id),
                    "step_id": step.step_id,
                    "step_type": "ai",
                    "model": model,
                    "content": ai_response.get("content"),
                    "tool_calls": ai_response.get("tool_calls"),
                    "usage": ai_response.get("usage"),
                },
            )

            # If there are tool calls, publish tool call events
            if ai_response.get("tool_calls"):
                for tc in ai_response["tool_calls"]:
                    await publish_run_event(
                        str(run.id),
                        RunEventType.TOOL_CALL_STARTED,
                        {
                            "run_id": str(run.id),
                            "step_id": step.step_id,
                            "tool_name": tc.get("function", {}).get("name"),
                            "tool_call_id": tc.get("id"),
                            "arguments": tc.get("function", {}).get("arguments"),
                        },
                    )

            # Continue execution
            new_job = Job(
                job_type="execute_run",
                run_id=str(run.id),
                function_id=job.function_id,
                tenant_id=job.tenant_id,
                data=job.data,
                max_attempts=job.max_attempts,
            )
            await self.queue.enqueue(new_job)

            print(f"[Executor] Run {run.id} AI step completed, continuing")
            return True

        elif step_type == "send_event":
            # Send event to trigger other functions
            event_name = step_result.get("name")
            event_data = step_result.get("data", {})

            # TODO: Publish to event stream
            event_id = str(uuid.uuid4())
            step.output = event_id

            print(f"[Executor] Run {run.id} sent event '{event_name}'")
            # Don't return True - let execution continue
            return False

        elif step_type == "agent":
            # Agent step type is handled like regular step results
            # The agent loop is implemented in the SDK, so the result
            # already contains the full AgentResult dictionary
            # We don't need special handling here
            print(f"[Executor] Run {run.id} agent step completed")
            return False

        return False


async def main() -> None:
    """Main entry point for the executor service."""
    settings = get_settings()
    executor = Executor(concurrency=settings.max_concurrent_jobs)
    await executor.start()


if __name__ == "__main__":
    asyncio.run(main())
