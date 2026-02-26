# FlowForge SDK

Python SDK for FlowForge - AI workflow orchestration with durable execution.

## Installation

```bash
pip install flowforge-sdk
```

## Quick Start

```python
from flowforge import FlowForge, Context, step

flowforge = FlowForge(app_id="my-app")

@flowforge.function(
    id="my-workflow",
    trigger=flowforge.trigger.event("my/event"),
)
async def my_workflow(ctx: Context) -> dict:
    result = await step.run("process", lambda: "Hello, World!")
    return {"message": result}
```

## Features

- Durable execution with automatic checkpointing
- AI agent support with tool calling
- Multi-agent networks with routing
- Human-in-the-loop approvals

## Step Primitives

Inside a `@flowforge.function`, use the global `step` object:

```python
from flowforge import step

# Run any function with memoization (won't re-run on replay)
result = await step.run("validate", validate_order, order)

# Pause until an event arrives
event = await step.wait_for_event("wait-payment", event="payment/received", match="data.order_id == 'abc'")

# Sleep for a duration
await step.sleep("wait-1h", "1h")

# LLM call with automatic retry
reply = await step.ai("summarize", model="gpt-4o", prompt="Summarize: ...")

# AI agent loop with tool calling
result = await step.agent(
    "research-agent",
    model="claude-sonnet-4-6",
    system="You are a research assistant.",
    messages=[{"role": "user", "content": "Research this topic..."}],
    tools=[...],
    max_tokens=4096,
    max_tool_calls=20,
)
```

## Sending Events

```python
# Send a single event
event_id = await flowforge.send("order/created", data={"order_id": "123"})

# Send multiple events
event_ids = await flowforge.send_many([
    {"name": "user/signup", "data": {"user_id": "1"}},
    {"name": "user/signup", "data": {"user_id": "2"}},
])
```

## Run Management

```python
# Get run details (status, steps, output)
run = await flowforge.get_run("761c0321-...")

# Retry a failed run in-place — keeps all memoized (completed) steps,
# only re-executes from the point of failure
result = await flowforge.retry_run("761c0321-...")

# Cancel a running or pending run
result = await flowforge.cancel_run("761c0321-...")
```

`retry_run` is different from replaying: it preserves the memoized results of
all completed steps so execution resumes from where it failed rather than
starting over from scratch.
