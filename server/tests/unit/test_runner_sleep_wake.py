"""Regression test for Runner._process_scheduled_runs_once.

Reproduces the bug where a durable sleep step (emitted by the SDK's 429
retry loop in PR #32) kept its run stuck in an infinite
runner-re-enqueue / executor-skip loop because the runner woke the run
without marking the sleep step COMPLETED.

Covers the two regressions that caused the loop:
    1. Step row is driven to COMPLETED with ended_at set — otherwise the
       executor's completed_steps filter drops it, the SDK replays the
       sleep, and the run re-enters PAUSED.
    2. DB state is committed before the continuation job is enqueued —
       otherwise the executor dequeues fast, reads stale PAUSED, logs
       "is paused, skipping", and the job is dropped.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from flowforge.exceptions import StepCompleted
from flowforge.steps import StepManager, _hash_step_id
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from flowforge_server.db.models import Function, Run, RunStatus, Step, StepStatus, Tenant
from flowforge_server.db.models.step import StepType
from flowforge_server.services.runner import Runner


@pytest_asyncio.fixture
async def session_factory(test_engine, test_db):
    """Bind a session factory to the test engine so we can open fresh sessions.

    A second independent session is needed to verify that `commit()` landed
    before the runner enqueued the job (bug #2).
    """
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def sleeping_run(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, uuid.UUID]:
    """Create a Tenant + Function + Run(PAUSED) + Step(SLEEPING, due)."""
    now = datetime.now(UTC)
    tenant_id = uuid.uuid4()
    fn_id = uuid.uuid4()
    run_id = uuid.uuid4()
    step_id = uuid.uuid4()

    async with session_factory() as s:
        tenant = Tenant(
            id=tenant_id,
            name="Runner Test Tenant",
            slug="runner-test",
            api_key_hash="x" * 64,
            signing_key_hash="y" * 64,
            settings={},
        )
        fn = Function(
            id=fn_id,
            tenant_id=tenant_id,
            function_id="runner-test-fn",
            name="Runner Test Fn",
            slug="runner-test-fn",
            trigger_type="event",
            trigger_value="test/sleep",
            endpoint_url="http://worker.test/fn",
            config={},
            is_active=True,
        )
        run = Run(
            id=run_id,
            tenant_id=tenant_id,
            function_id=fn_id,
            status=RunStatus.PAUSED,
            trigger_type="event",
            trigger_data={"event": {"name": "test/sleep", "data": {}}},
            resume_at=now - timedelta(seconds=1),  # already due
        )
        step = Step(
            id=step_id,
            run_id=run_id,
            step_id="think/retry-sleep-1",
            step_hash="deadbeefdeadbeef",
            step_type=StepType.SLEEP,
            status=StepStatus.SLEEPING,
            scheduled_at=now - timedelta(seconds=1),  # already due
            started_at=now - timedelta(seconds=2),
            output={"type": "sleep", "duration_seconds": 1},
        )
        s.add_all([tenant, fn, run, step])
        await s.commit()

    return {"run_id": run_id, "step_id": step_id, "fn_id": fn_id}


@pytest.mark.asyncio
async def test_sleep_wake_marks_step_completed_and_commits_before_enqueue(
    session_factory: async_sessionmaker[AsyncSession],
    sleeping_run: dict[str, uuid.UUID],
) -> None:
    """Single pass: sleep step → COMPLETED, run → RUNNING, job enqueued exactly once,
    and the commit lands BEFORE the enqueue (checked via a fresh session)."""
    runner = Runner()
    enqueue_mock = AsyncMock()
    captured_states: list[tuple[RunStatus, uuid.UUID | None]] = []

    async def record_then_enqueue(run: Run, fn: Function) -> None:
        # When the runner calls enqueue, a separate session should already
        # see the committed RUNNING status. Record what an independent
        # reader sees at this exact moment.
        async with session_factory() as fresh:
            row = (
                await fresh.execute(select(Run).where(Run.id == run.id))
            ).scalar_one()
            captured_states.append((row.status, row.resume_at))

    enqueue_mock.side_effect = record_then_enqueue
    # Drive _enqueue_run via its only side effect (self.queue.enqueue) — but
    # _enqueue_run constructs the Job from scratch, so just patch the method.
    runner._enqueue_run = enqueue_mock  # type: ignore[method-assign]

    async with session_factory() as session:
        enqueued = await runner._process_scheduled_runs_once(session)

    assert enqueued == 1
    assert enqueue_mock.await_count == 1

    # Commit-before-enqueue: the independent reader saw RUNNING, not PAUSED.
    assert len(captured_states) == 1
    status_at_enqueue, resume_at_at_enqueue = captured_states[0]
    assert status_at_enqueue == RunStatus.RUNNING
    assert resume_at_at_enqueue is None

    # Durable state: re-read run + step from a brand new session.
    async with session_factory() as verify:
        run = (
            await verify.execute(
                select(Run).where(Run.id == sleeping_run["run_id"])
            )
        ).scalar_one()
        step = (
            await verify.execute(
                select(Step).where(Step.id == sleeping_run["step_id"])
            )
        ).scalar_one()

    assert run.status == RunStatus.RUNNING
    assert run.resume_at is None
    assert step.status == StepStatus.COMPLETED
    assert step.ended_at is not None


@pytest.mark.asyncio
async def test_sleep_wake_does_not_re_enqueue_on_second_pass(
    session_factory: async_sessionmaker[AsyncSession],
    sleeping_run: dict[str, uuid.UUID],
) -> None:
    """After waking once, a second pass must not find the run again — this is
    what prevents the hundreds-of-resumes loop reported in production."""
    runner = Runner()
    enqueue_mock = AsyncMock()
    runner._enqueue_run = enqueue_mock  # type: ignore[method-assign]

    # First pass wakes the run.
    async with session_factory() as session:
        enqueued_first = await runner._process_scheduled_runs_once(session)

    # Second pass must be a no-op (run is RUNNING, step is COMPLETED).
    async with session_factory() as session:
        enqueued_second = await runner._process_scheduled_runs_once(session)

    assert enqueued_first == 1
    assert enqueued_second == 0
    assert enqueue_mock.await_count == 1


@pytest.mark.asyncio
async def test_full_retry_chain_progresses_to_attempt_2_after_wake(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """End-to-end proof: after the runner's fix, the SDK-side retry loop
    progresses past retry-sleep-1 to attempt-2. This is the user-visible
    regression that #32 shipped and this patch repairs.

    We simulate the server state just after the executor handled the first
    429 (rate-limit payload stored for ``think``, sleep step SLEEPING with
    scheduled_at in the past). The runner wakes the run. We then build the
    executor's completed_steps dict exactly the way executor.py:314-318 does
    (status==COMPLETED, output IS NOT NULL) and feed it to the SDK. If the
    runner hadn't marked the sleep step COMPLETED, the SDK would re-emit the
    sleep — loop forever. With the fix, the SDK yields attempt-2.
    """
    now = datetime.now(UTC)
    tenant_id = uuid.uuid4()
    fn_id = uuid.uuid4()
    run_id = uuid.uuid4()

    think_hash = _hash_step_id("think")
    sleep_hash = _hash_step_id("think/retry-sleep-1")

    rate_limited_payload = {
        "__rate_limited": True,
        "__retry_after": 1.0,
        "__provider": "anthropic",
        "__model": "claude-sonnet-4-6",
        "__error": "test 429",
    }

    # Seed: state of the world just after executor processed the first 429.
    # - think step: COMPLETED, output = rate-limited signal (executor stored it).
    # - retry-sleep-1 step: SLEEPING, scheduled_at already due.
    # - run: PAUSED, resume_at already due.
    async with session_factory() as s:
        s.add_all(
            [
                Tenant(
                    id=tenant_id,
                    name="Chain Test",
                    slug="chain-test",
                    api_key_hash="c" * 64,
                    signing_key_hash="d" * 64,
                    settings={},
                ),
                Function(
                    id=fn_id,
                    tenant_id=tenant_id,
                    function_id="chain-fn",
                    name="Chain Fn",
                    slug="chain-fn",
                    trigger_type="event",
                    trigger_value="t/c",
                    endpoint_url="http://w/c",
                    config={},
                    is_active=True,
                ),
                Run(
                    id=run_id,
                    tenant_id=tenant_id,
                    function_id=fn_id,
                    status=RunStatus.PAUSED,
                    trigger_type="event",
                    trigger_data={},
                    resume_at=now - timedelta(seconds=1),
                ),
                Step(
                    run_id=run_id,
                    step_id="think",
                    step_hash=think_hash,
                    step_type=StepType.AI,
                    status=StepStatus.COMPLETED,
                    started_at=now - timedelta(seconds=3),
                    ended_at=now - timedelta(seconds=2),
                    output=rate_limited_payload,
                ),
                Step(
                    run_id=run_id,
                    step_id="think/retry-sleep-1",
                    step_hash=sleep_hash,
                    step_type=StepType.SLEEP,
                    status=StepStatus.SLEEPING,
                    started_at=now - timedelta(seconds=2),
                    scheduled_at=now - timedelta(seconds=1),
                    output={"type": "sleep", "duration_seconds": 1},
                ),
            ]
        )
        await s.commit()

    # Wake the run.
    runner = Runner()
    runner._enqueue_run = AsyncMock()  # type: ignore[method-assign]

    async with session_factory() as session:
        enqueued = await runner._process_scheduled_runs_once(session)

    assert enqueued == 1

    # Simulate the executor rebuilding completed_steps from run.steps the
    # exact way executor.py:314-318 does.
    async with session_factory() as verify:
        steps = (
            await verify.execute(select(Step).where(Step.run_id == run_id))
        ).scalars().all()

    completed_steps = {
        s.step_hash: s.output
        for s in steps
        if s.status == StepStatus.COMPLETED and s.output is not None
    }

    # Both steps must be in the dict now — this is what unlocks progression.
    assert think_hash in completed_steps
    assert sleep_hash in completed_steps, (
        "runner must mark retry-sleep-1 COMPLETED so the SDK memoises it"
    )

    # Drive the SDK's retry loop with the executor's completed_steps view.
    # It must yield attempt-2 (not re-emit retry-sleep-1).
    mgr = StepManager(run_id=str(run_id), completed_steps=completed_steps)

    with pytest.raises(StepCompleted) as exc:
        await mgr.ai("think", model="claude-sonnet-4-6", prompt="hi", num_retries=3)

    assert exc.value.step_id == "think/attempt-2"
    assert exc.value.result["type"] == "ai"


@pytest.mark.asyncio
async def test_sleep_wake_skips_steps_not_yet_due(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Sleep steps with scheduled_at in the future are not woken."""
    now = datetime.now(UTC)
    tenant_id = uuid.uuid4()
    fn_id = uuid.uuid4()
    run_id = uuid.uuid4()

    async with session_factory() as s:
        s.add_all(
            [
                Tenant(
                    id=tenant_id,
                    name="Future Test",
                    slug="future-test",
                    api_key_hash="a" * 64,
                    signing_key_hash="b" * 64,
                    settings={},
                ),
                Function(
                    id=fn_id,
                    tenant_id=tenant_id,
                    function_id="future-fn",
                    name="Future Fn",
                    slug="future-fn",
                    trigger_type="event",
                    trigger_value="t/f",
                    endpoint_url="http://w/f",
                    config={},
                    is_active=True,
                ),
                Run(
                    id=run_id,
                    tenant_id=tenant_id,
                    function_id=fn_id,
                    status=RunStatus.PAUSED,
                    trigger_type="event",
                    trigger_data={},
                    resume_at=now + timedelta(seconds=60),
                ),
                Step(
                    run_id=run_id,
                    step_id="future-sleep",
                    step_hash="futurehash12345",
                    step_type=StepType.SLEEP,
                    status=StepStatus.SLEEPING,
                    scheduled_at=now + timedelta(seconds=60),
                    output={"type": "sleep", "duration_seconds": 60},
                ),
            ]
        )
        await s.commit()

    runner = Runner()
    runner._enqueue_run = AsyncMock()  # type: ignore[method-assign]

    async with session_factory() as session:
        enqueued = await runner._process_scheduled_runs_once(session)

    assert enqueued == 0
    runner._enqueue_run.assert_not_awaited()  # type: ignore[attr-defined]
