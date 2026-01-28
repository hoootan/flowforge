# FlowForge

A production-ready AI workflow orchestration platform. Build durable, event-driven workflows with automatic retries, step memoization, and LLM integration.

## Features

- **Durable Execution**: Steps are memoized and checkpointed. If a workflow fails and restarts, completed steps won't re-execute.
- **Event-Driven**: Trigger workflows from events, webhooks, or cron schedules.
- **AI-Native**: Built-in `step.ai()` for LLM calls with automatic retries and model routing via LiteLLM.
- **Flow Control**: Concurrency limiting, rate limiting, throttling, and debouncing.
- **Multi-Tenant**: Fair queue with tenant isolation for SaaS workloads.
- **Role-Based Access**: Admin, Member, and Viewer roles with granular permissions.
- **Developer Experience**: CLI for local development with hot reload and event simulation.

## Quick Start

### Installation

```bash
pip install flowforge-sdk
```

### Define a Workflow

```python
from flowforge import FlowForge, Context, step

flowforge = FlowForge(app_id="my-app")

@flowforge.function(
    id="process-order",
    trigger=flowforge.trigger.event("order/created"),
    retries=3,
)
async def process_order(ctx: Context) -> dict:
    order = ctx.event.data

    # Step 1: Validate (memoized)
    validation = await step.run("validate", validate_order, order)

    # Step 2: AI fraud check
    fraud_check = await step.ai(
        "fraud-check",
        model="gpt-4o",
        prompt=f"Check order {order['id']} for fraud..."
    )

    # Step 3: Process payment
    payment = await step.run("payment", process_payment, order)

    # Step 4: Wait before confirmation
    await step.sleep("delay", "30s")

    # Step 5: Send email
    await step.run("confirm", send_email, order)

    return {"status": "completed", "order_id": order["id"]}
```

### Run Locally

```bash
# Install CLI
pip install flowforge-cli

# Start dev server
cd examples
flowforge dev .

# Send a test event
flowforge send order/created -d '{"id": "123", "customer": "Alice", "total": 99.99}'
```

## Step Primitives

| Step | Description |
|------|-------------|
| `step.run(id, fn, *args)` | Execute a function with memoization |
| `step.sleep(id, duration)` | Pause execution ("5s", "1h", "30m") |
| `step.ai(id, model=, prompt=)` | LLM call with retry |
| `step.wait_for_event(id, event=, match=)` | Pause until a matching event arrives |
| `step.invoke(id, function_id=, data=)` | Call another FlowForge function |
| `step.send_event(id, name=, data=)` | Emit an event |

## TypeScript/Node.js Client

Trigger workflows from your Next.js or Node.js app:

```bash
npm install flowforge-client
```

```typescript
import { FlowForge } from 'flowforge-client';

const client = new FlowForge('http://localhost:8000');

// Send an event to trigger a workflow
const result = await client.sendEvent('order/created', {
  order_id: '123',
  customer: 'Alice',
});

// Wait for completion
const run = await client.waitForRun(result.runs[0].id);
console.log('Output:', run.output);
```

See [`packages/flowforge-client-ts`](./packages/flowforge-client-ts) for full documentation.

## Authentication

FlowForge supports two authentication methods:

### Dashboard Users (for humans)

Access the dashboard with email/password. Three roles are available:

| Role | Permissions |
|------|-------------|
| **Admin** | Full access: manage users, API keys, functions, tools, everything |
| **Member** | Create/edit functions, tools, send events, view runs, manage approvals |
| **Viewer** | Read-only: view runs, events, functions, tools (no create/edit/delete) |

**Create the first admin:**

```bash
# Using Docker (recommended)
docker exec flowforge-server flowforge-create-admin -e admin@example.com -p 'your-secure-password' -n 'Admin User'

# Using the server CLI (local development)
flowforge-server create-admin --email admin@example.com --password secret123

# Or the standalone command
flowforge-create-admin -e admin@example.com -p secret123 -n "Admin User"
```

### API Keys (for applications)

For SDK and server-to-server authentication:

```bash
# Key format: ff_{type}_{random}
# Types: live (production), test (development), ro (read-only)

# Example: ff_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

Create API keys via the dashboard (Settings → API Keys) or API.

## Project Structure

```
flowforge/
├── packages/
│   ├── flowforge-sdk/       # Python SDK
│   ├── flowforge-cli/       # CLI tool
│   └── flowforge-client-ts/ # TypeScript client
├── server/                  # Orchestration server (FastAPI)
├── dashboard/               # Admin dashboard (Next.js)
├── examples/                # Example workflows
└── tests/                   # Test suites
```

## Development

### Prerequisites

- Python 3.11+
- Node.js 18+ (for dashboard)
- Docker (for PostgreSQL and Redis)

### Setup

```bash
# Start infrastructure
docker-compose up -d

# Install SDK in development mode
pip install -e "packages/flowforge-sdk[all]"
pip install -e packages/flowforge-cli
pip install -e server

# Run tests
pytest

# Start dashboard
cd dashboard && pnpm install && pnpm dev
```

### Environment Variables

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://flowforge:flowforge@localhost:5432/flowforge

# Redis
REDIS_URL=redis://localhost:6379

# AI (for step.ai)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Architecture

1. **Event arrives** at the server API
2. **Server matches** the event to registered functions by trigger
3. **Job is enqueued** to the fair queue (Redis-backed)
4. **Executor dequeues** and invokes the user function
5. **Function executes** until a `step.*` call
6. **Step result is saved**, function re-enqueues for continuation
7. **Repeat** until function returns or fails

Steps raise control flow exceptions (`StepCompleted`) to yield control back to the server, enabling durable execution across restarts.

## License

MIT
