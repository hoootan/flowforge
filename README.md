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

## How It Works

FlowForge uses a **client-server architecture** where your workflow code runs on workers, while the central server handles orchestration.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Your Application                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
│  │  Next.js    │    │   FastAPI   │    │   Cron Job  │           │
│  │  Frontend   │    │   Backend   │    │             │           │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘           │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │ send events                         │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   FlowForge Server                          │ │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌───────────────┐  │ │
│  │  │   API   │  │  Queue  │  │  Runner  │  │   Executor    │  │ │
│  │  │ :8000   │  │ (Redis) │  │          │  │               │  │ │
│  │  └─────────┘  └─────────┘  └──────────┘  └───────┬───────┘  │ │
│  └──────────────────────────────────────────────────┼──────────┘ │
│                                                     │            │
│                              invoke function        │            │
│                                                     ▼            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   Your Worker(s)                            │ │
│  │  ┌─────────────────────────────────────────────────────┐    │ │
│  │  │  @flowforge.function("process-order")               │    │ │
│  │  │  async def process_order(ctx):                      │    │ │
│  │  │      await step.run("validate", ...)                │    │ │
│  │  │      await step.ai("fraud-check", ...)              │    │ │
│  │  └─────────────────────────────────────────────────────┘    │ │
│  │                         :8080                               │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

**The Flow:**

1. Your app sends an event → `client.sendEvent("order/created", {...})`
2. FlowForge Server receives it and matches to registered functions
3. Server calls your Worker's `/invoke` endpoint
4. Worker executes your Python code, step by step
5. Each step result is saved (durable execution)
6. If worker crashes, server retries from last checkpoint

## Quick Start

### Installation

```bash
pip install flowforge-sdk
```

### SDK Configuration

```python
from flowforge import FlowForge, Context, step

# Initialize with server connection
flowforge = FlowForge(
    app_id="my-app",                      # Your application identifier
    api_url="http://localhost:8000",      # FlowForge server URL
    api_key="ff_live_xxx",                # API key for authentication (optional)
    signing_key="sk_xxx",                 # Request signing key (optional)
)
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `app_id` | Unique identifier for your application | Required |
| `api_url` | URL of the FlowForge server | `FLOWFORGE_API_URL` env or `http://localhost:8000` |
| `api_key` | API key for authentication (ff_live_xxx) | `FLOWFORGE_API_KEY` env or `None` |
| `signing_key` | Key for HMAC request signing | `FLOWFORGE_SIGNING_KEY` env or `None` |

**Environment Variables:**

```bash
export FLOWFORGE_API_URL=http://localhost:8000
export FLOWFORGE_API_KEY=ff_live_xxx
export FLOWFORGE_SIGNING_KEY=sk_xxx

# For worker mode:
export FLOWFORGE_SERVER_URL=http://localhost:8000  # Alias for FLOWFORGE_API_URL
export FLOWFORGE_WORKER_URL=http://localhost:8080/api/flowforge
```

### Define a Workflow

```python
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

## Running Modes

### 1. Local Development (All-in-One)

For development, use the CLI to run everything locally:

```bash
# Install CLI
pip install flowforge-cli

# Start dev server (runs server + executes functions locally)
flowforge dev .

# Send a test event
flowforge send order/created -d '{"id": "123", "customer": "Alice"}'
```

### 2. Serverless Mode (No Worker Needed)

Create agent-based functions via API that run directly on the server:

```bash
# Create a serverless function via API
curl -X POST http://localhost:8000/api/v1/functions/inline \
  -H "Content-Type: application/json" \
  -d '{
    "function_id": "support-agent",
    "name": "Support Agent",
    "trigger_type": "event",
    "trigger_value": "ticket/created",
    "system_prompt": "You are a helpful support agent...",
    "tools": ["web_search", "send_email"],
    "agent_config": {
      "model": "gpt-4o",
      "max_iterations": 10
    }
  }'
```

No worker deployment needed — the server executes the agent internally using the configured tools.

### 3. Production (Separate Server + Workers)

In production, run the server separately and connect workers:

**Start the server:**

```bash
docker-compose up -d
```

**Run your worker:**

```python
# main.py
from flowforge import FlowForge, Context, step

flowforge = FlowForge(app_id="my-app")

@flowforge.function(id="process-order", ...)
async def process_order(ctx: Context):
    ...

# Start as a worker - connects to the server
if __name__ == "__main__":
    flowforge.work(
        server_url="http://flowforge-server:8000",  # Central server
        host="0.0.0.0",
        port=8080,                                   # Worker listens here
        worker_url="http://my-worker:8080/api/flowforge",  # How server reaches us
    )
```

**What `work()` does:**

1. Starts a FastAPI server on your machine (port 8080)
2. Registers your functions with the central server
3. Exposes `/api/flowforge/invoke` for the server to call
4. Handles function execution when invoked

**Environment variables for workers:**

```bash
export FLOWFORGE_SERVER_URL=http://flowforge-server:8000
export FLOWFORGE_WORKER_URL=http://my-worker:8080/api/flowforge
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
import { createClient } from 'flowforge-client';

// Create client (Supabase-style API)
const ff = createClient('http://localhost:8000', {
  apiKey: 'ff_live_xxx',  // Optional: API key for authentication
});

// Send an event to trigger a workflow
const { data, error } = await ff.events.send('order/created', {
  order_id: '123',
  customer: 'Alice',
});

if (error) {
  console.error('Failed:', error.message);
} else {
  console.log('Triggered runs:', data.runs);
}

// Wait for a run to complete
const { data: run } = await ff.runs.waitFor(data.runs[0].id, {
  timeout: 60000
});
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

### Two-Factor Authentication (2FA)

Users can optionally enable two-factor authentication for added security:

1. Go to **Settings → Security** in the dashboard
2. Click **Enable 2FA**
3. Scan the QR code with an authenticator app (Google Authenticator, Authy, 1Password, etc.)
4. Enter the 6-digit verification code
5. Save your backup codes in a safe place

When 2FA is enabled, users must enter a verification code from their authenticator app after their password during login. Backup codes can be used for recovery if access to the authenticator is lost.

**Requirements:** 2FA requires the `FLOWFORGE_ENCRYPTION_KEY` environment variable to be set for encrypting TOTP secrets.

### API Keys (for applications)

For SDK and server-to-server authentication:

```bash
# Key format: ff_{type}_{random}
# Types: live (production), test (development), ro (read-only)

# Example: ff_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

Create API keys via the dashboard (Settings → API Keys) or API.

**Using API keys in the SDK:**

```python
# Python SDK
flowforge = FlowForge(
    app_id="my-app",
    api_url="http://localhost:8000",
    api_key="ff_live_xxx",  # For authentication
)

# Requests are sent with the key in the header:
# X-FlowForge-API-Key: ff_live_xxx
```

```typescript
// TypeScript client
const ff = createClient('http://localhost:8000', {
  apiKey: 'ff_live_xxx',
});
```

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

# Authentication & Security
FLOWFORGE_JWT_SECRET=your-jwt-secret-change-in-production
FLOWFORGE_ENCRYPTION_KEY=your-encryption-key  # Required for 2FA and storing AI provider keys

# SDK/Worker configuration
FLOWFORGE_SERVER_URL=http://localhost:8000
FLOWFORGE_EVENT_KEY=ff_live_xxx
FLOWFORGE_SIGNING_KEY=sk_xxx
FLOWFORGE_WORKER_URL=http://localhost:8080/api/flowforge
```

**Generate an encryption key:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FlowForge Server                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Event arrives at /api/v1/events                         │
│                    │                                        │
│                    ▼                                        │
│  2. Server matches event to registered functions            │
│                    │                                        │
│                    ▼                                        │
│  3. Job enqueued to fair queue (Redis)                      │
│                    │                                        │
│                    ▼                                        │
│  4. Executor dequeues and calls worker's /invoke endpoint   │
│                    │                                        │
└────────────────────┼────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Your Worker                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  5. Worker executes your function                           │
│                    │                                        │
│                    ▼                                        │
│  6. On step.* call → returns control to server              │
│     (raises StepCompleted exception)                        │
│                    │                                        │
│                    ▼                                        │
│  7. Step result saved, function re-enqueued                 │
│                    │                                        │
│                    ▼                                        │
│  8. Repeat until function returns or fails                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Steps raise control flow exceptions (`StepCompleted`) to yield control back to the server, enabling durable execution across restarts.

## License

MIT
