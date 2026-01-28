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
