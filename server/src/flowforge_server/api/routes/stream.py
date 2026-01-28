"""SSE streaming endpoint for real-time run progress."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db import get_session_context
from flowforge_server.db.models import Run, RunStatus, Step, StepStatus
from flowforge_server.stream.pubsub import (
    RunEvent,
    RunEventType,
    get_pubsub,
)

router = APIRouter(prefix="/runs", tags=["streaming"])


@router.get("/test-stream")
async def test_stream() -> StreamingResponse:
    """
    Test endpoint to verify SSE streaming is working.

    Streams 10 numbered events with 500ms delay between each.
    Use this to verify streaming works before testing real runs.
    """
    async def generate_test_events() -> AsyncGenerator[str, None]:
        yield ": connected\n\n"
        for i in range(10):
            event_data = {
                "count": i + 1,
                "message": f"Test event {i + 1} of 10",
                "timestamp": datetime.utcnow().isoformat(),
            }
            yield f"event: test\ndata: {json.dumps(event_data)}\n\n"
            await asyncio.sleep(0.5)  # 500ms between events
        yield f"event: done\ndata: {json.dumps({'message': 'Stream complete'})}\n\n"

    return StreamingResponse(
        generate_test_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _get_status_value(status) -> str:
    """Get string value from status, handling both enum and string cases."""
    if hasattr(status, 'value'):
        return status.value
    return str(status)


async def generate_sse_events(
    run_id: str,
    include_history: bool = True,
    timeout_seconds: float = 300.0,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a run.

    Args:
        run_id: The run ID to stream events for.
        include_history: Whether to send existing steps first.
        timeout_seconds: Maximum time to stream before disconnecting.
    """
    # Send initial comment immediately to establish connection
    yield ": connected\n\n"

    pubsub = get_pubsub()

    # Track run status for later terminal check
    run_is_terminal = False
    run_terminal_data: dict | None = None

    # First, send existing state if requested
    if include_history:
        async with get_session_context() as session:
            result = await session.execute(
                select(Run).where(Run.id == uuid.UUID(run_id))
            )
            run = result.scalar_one_or_none()

            if run:
                # Send run status
                yield _format_sse_event(
                    RunEventType.RUN_STARTED,
                    {
                        "run_id": str(run.id),
                        "status": _get_status_value(run.status),
                        "function_id": str(run.function_id),
                        "started_at": run.started_at.isoformat() if run.started_at else None,
                    },
                )

                # Send existing steps
                for step in run.steps:
                    step_data = {
                        "step_id": step.step_id,
                        "step_type": _get_status_value(step.step_type) if step.step_type else "run",
                        "status": _get_status_value(step.status),
                        "output": step.output,
                    }

                    status_str = _get_status_value(step.status)
                    if status_str == "completed":
                        yield _format_sse_event(RunEventType.STEP_COMPLETED, step_data)
                    elif status_str == "waiting":
                        yield _format_sse_event(
                            RunEventType.APPROVAL_REQUIRED,
                            {
                                **step_data,
                                "wait_event_name": step.wait_event_name,
                            },
                        )
                    elif status_str == "sleeping":
                        yield _format_sse_event(
                            RunEventType.RUN_PAUSED,
                            {
                                **step_data,
                                "resume_at": step.scheduled_at.isoformat() if step.scheduled_at else None,
                            },
                        )

                # Check if already terminal - but don't return yet
                # We need to send buffered events first (thinking chunks, etc.)
                run_status_str = _get_status_value(run.status)
                if run_status_str in ("completed", "failed", "cancelled"):
                    run_is_terminal = True
                    run_terminal_data = {
                        "run_id": str(run.id),
                        "status": run_status_str,
                        "output": run.output,
                        "error": run.error,
                        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
                    }

    # IMPORTANT: Subscribe to Redis pub/sub FIRST, before getting buffered events.
    # This prevents a race condition where events published between getting
    # the buffer and subscribing would be lost.
    client = await pubsub._get_client()
    ps = client.pubsub()
    channel = pubsub._channel_name(run_id)
    await ps.subscribe(channel)

    # Now get buffered events (any events published after subscribe will be caught live)
    # This includes thinking chunks that were published during execution
    last_buffered_timestamp: datetime | None = None
    buffered_events = await pubsub.get_buffered_events(run_id, clear=False)
    for event in buffered_events:
        yield event.to_sse()
        last_buffered_timestamp = event.timestamp
        # Add small delay for thinking_chunk events to simulate real-time streaming
        # when replaying buffered events for late-connecting clients
        if event.event_type == RunEventType.THINKING_CHUNK:
            await asyncio.sleep(0.02)  # 20ms delay between chunks

    # Now check if run was terminal - after sending buffered events
    if run_is_terminal and run_terminal_data:
        event_type = (
            RunEventType.RUN_COMPLETED
            if run_terminal_data["status"] == "completed"
            else RunEventType.RUN_FAILED
        )
        yield _format_sse_event(event_type, run_terminal_data)
        # Clean up subscription before returning
        await ps.unsubscribe(channel)
        await ps.close()
        return

    # Listen for live events with keepalive
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    keepalive_interval = 15.0  # Send keepalive every 15 seconds
    last_keepalive = asyncio.get_event_loop().time()

    try:
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break

            # Check if we need to send a keepalive
            now = asyncio.get_event_loop().time()
            if now - last_keepalive >= keepalive_interval:
                yield ": keepalive\n\n"
                last_keepalive = now

            try:
                message = await asyncio.wait_for(
                    ps.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=min(remaining, keepalive_interval, 5.0),
                )

                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        event = RunEvent.from_dict(data)

                        # Skip events that were already sent from buffer
                        if last_buffered_timestamp and event.timestamp <= last_buffered_timestamp:
                            continue

                        yield event.to_sse()

                        # Stop if run completed or failed
                        if event.event_type in (
                            RunEventType.RUN_COMPLETED,
                            RunEventType.RUN_FAILED,
                        ):
                            return
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

            except asyncio.TimeoutError:
                # Send keepalive on timeout
                yield ": keepalive\n\n"
                last_keepalive = asyncio.get_event_loop().time()
                continue
    except asyncio.CancelledError:
        # Client disconnected
        pass
    finally:
        await ps.unsubscribe(channel)
        await ps.close()


def _format_sse_event(event_type: RunEventType, data: dict) -> str:
    """Format data as an SSE event string."""
    event = RunEvent(
        run_id=data.get("run_id", ""),
        event_type=event_type,
        data=data,
    )
    return event.to_sse()


@router.get("/{run_id}/stream")
async def stream_run_progress(
    run_id: str,
    include_history: bool = Query(True, description="Include existing steps in stream"),
    timeout: float = Query(300.0, description="Stream timeout in seconds", le=600.0),
) -> StreamingResponse:
    """
    Stream real-time progress events for a run using Server-Sent Events (SSE).

    This endpoint provides live updates as a workflow executes, including:
    - Step started/completed events
    - AI thinking state updates
    - Tool call notifications
    - Approval required events (HITL)
    - Run completion/failure

    The stream automatically closes when the run reaches a terminal state
    (completed, failed, or cancelled) or when the timeout is reached.

    **Event Types:**
    - `step_started` - A new step has begun execution
    - `step_completed` - A step has finished with a result
    - `step_failed` - A step has failed
    - `thinking` - AI is processing (may include partial content)
    - `tool_call_started` - A tool is being invoked
    - `tool_call_completed` - A tool has returned a result
    - `approval_required` - Workflow is waiting for human approval
    - `approval_resolved` - Approval has been granted/rejected
    - `run_started` - Workflow execution has begun
    - `run_paused` - Workflow is paused (sleeping or waiting)
    - `run_resumed` - Workflow has resumed execution
    - `run_completed` - Workflow finished successfully
    - `run_failed` - Workflow failed with an error

    **Example usage (JavaScript):**
    ```javascript
    const es = new EventSource('/api/v1/runs/{run_id}/stream');

    es.addEventListener('step_completed', (e) => {
        const data = JSON.parse(e.data);
        console.log('Step completed:', data);
    });

    es.addEventListener('thinking', (e) => {
        const data = JSON.parse(e.data);
        console.log('AI thinking:', data);
    });

    es.addEventListener('run_completed', (e) => {
        const data = JSON.parse(e.data);
        console.log('Run finished:', data);
        es.close();
    });
    ```
    """
    # Validate run exists
    async with get_session_context() as session:
        result = await session.execute(
            select(Run).where(Run.id == uuid.UUID(run_id))
        )
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return StreamingResponse(
        generate_sse_events(run_id, include_history, timeout),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "X-Content-Type-Options": "nosniff",
            "Transfer-Encoding": "chunked",
        },
    )


@router.get("/{run_id}/progress")
async def get_run_progress(
    run_id: str,
    since_step: int = Query(0, description="Get steps since this index"),
) -> dict:
    """
    Get current run progress with incremental step updates.

    This is a polling-friendly endpoint for clients that can't use SSE.
    Use `since_step` to only get new steps since last poll.
    """
    async with get_session_context() as session:
        result = await session.execute(
            select(Run).where(Run.id == uuid.UUID(run_id))
        )
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        # Get steps after the index
        all_steps = sorted(run.steps, key=lambda s: s.created_at)
        new_steps = all_steps[since_step:]

        run_status_str = _get_status_value(run.status)
        return {
            "run": {
                "id": str(run.id),
                "status": run_status_str,
                "function_id": str(run.function_id),
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "ended_at": run.ended_at.isoformat() if run.ended_at else None,
                "output": run.output,
                "error": run.error,
            },
            "total_steps": len(all_steps),
            "new_steps": [
                {
                    "step_id": step.step_id,
                    "step_type": _get_status_value(step.step_type) if step.step_type else "run",
                    "status": _get_status_value(step.status),
                    "output": step.output,
                    "created_at": step.created_at.isoformat() if step.created_at else None,
                }
                for step in new_steps
            ],
            "is_terminal": run_status_str in ("completed", "failed", "cancelled"),
        }
