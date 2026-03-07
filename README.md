# FlowForge

A production-ready AI workflow orchestration platform. Build durable, event-driven workflows with automatic retries, step memoization, and LLM integration.

## Features

- **Durable Execution**: Steps are memoized and checkpointed. If a workflow fails and restarts, completed steps won't re-execute.
- **Event-Driven**: Trigger workflows from events, webhooks, or cron schedules.
- **AI-Native**: Built-in `step.ai()` for LLM calls with automatic retries and model routing via LiteLLM.
- **Flow Control**: Concurrency limiting, rate limiting, throttling, and debouncing.
- **Executable Tools**: Three tool types — code (sandboxed Python with `httpx`), webhook (no-code HTTP config), and built-in (`http_request`, `web_search`, etc.).
- **Credentials System**: Encrypted credential storage with `{{credential:name}}` placeholders for secure API key injection into tools.
- **Multi-Tenant**: Fair queue with tenant isolation for SaaS workloads.
- **Role-Based Access**: Admin, Member, and Viewer roles with granular permissions.
- **Developer Experience**: CLI for local development with hot reload and event simulation.

## Dashboard

| Overview | Tools | Settings |
|---|---|---|
| ![Overview](docs/screenshots/dashboard-overview.png) | ![Tools](docs/screenshots/dashboard-tools.png) | ![Settings](docs/screenshots/dashboard-settings.png) |

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

### Tools

FlowForge supports three types of tools that agents can use:

#### Built-in Tools

Pre-configured tools that ship with FlowForge:

| Tool | Description |
|------|-------------|
| `http_request` | General-purpose HTTP client (GET/POST/PUT/PATCH/DELETE) with SSRF protection |
| `web_search` | Web search via Tavily API |
| `generate_image` | Image generation via Google Gemini |
| `ask_user` | Human-in-the-loop question/response (requires approval) |

#### Webhook Tools (No-Code)

Configure HTTP endpoints as tools without writing code. Supports `{{credential:name}}` and `{{env:VAR}}` placeholders for secure credential injection:

```bash
curl -X POST http://localhost:8000/api/v1/tools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_brands",
    "description": "Fetch brands from Supabase",
    "tool_type": "webhook",
    "webhook_url": "https://xyz.supabase.co/rest/v1/brands",
    "webhook_method": "GET",
    "webhook_headers": {
      "apikey": "{{credential:supabase_key}}",
      "Authorization": "Bearer {{credential:supabase_key}}"
    },
    "parameters": {
      "type": "object",
      "properties": {
        "select": { "type": "string", "description": "Columns to select" }
      }
    }
  }'
```

#### Code Tools (Sandboxed Python)

Custom Python code executed in a restricted sandbox. The sandbox allows `httpx` for HTTP requests and read-only `os.environ` access:

```bash
curl -X POST http://localhost:8000/api/v1/tools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "lookup_user",
    "description": "Look up a user by email",
    "tool_type": "custom",
    "parameters": {
      "type": "object",
      "properties": {
        "email": { "type": "string" }
      },
      "required": ["email"]
    },
    "code": "def execute(email):\n    import httpx\n    api_key = os.environ.get(\"MY_API_KEY\")\n    resp = httpx.get(f\"https://api.example.com/users?email={email}\", headers={\"Authorization\": f\"Bearer {api_key}\"})\n    return resp.json()"
  }'
```

### Credentials

Store encrypted secrets in FlowForge and reference them in webhook tool configurations:

```bash
# Create a credential
curl -X POST http://localhost:8000/api/v1/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "name": "supabase_key",
    "credential_type": "api_key",
    "value": "eyJhbGciOiJIUzI1NiIs...",
    "description": "Supabase project API key"
  }'

# List credentials (values are never returned, only masked prefixes)
curl http://localhost:8000/api/v1/credentials
```

Credentials are encrypted at rest using Fernet (AES-128-CBC) and can be managed via the dashboard under **Settings > Credentials**.

Placeholder syntax:
- `{{credential:name}}` — resolves to the decrypted credential value
- `{{env:VAR_NAME}}` — resolves to the environment variable value

### 3. Production (Separate Server + Workers)

In production, run the server separately and connect workers:

**Start the server:**

```bash
docker-compose up -d
```

### 4. Kubernetes (Production Cluster)

Raw Kubernetes manifests are provided in `deploy/kubernetes/` for cluster deployments. They mirror the docker-compose topology with health probes, autoscaling, and zero-downtime rollouts.

**Prerequisites:** Metrics Server + NGINX Ingress Controller installed in your cluster.

**Quick deploy:**

```bash
# 1. Fill in secrets (never commit real values)
cp deploy/kubernetes/02-secret.yaml deploy/kubernetes/02-secret.local.yaml
# Edit 02-secret.local.yaml and replace all CHANGE_ME values

# 2. Update the host in deploy/kubernetes/40-ingress.yaml
#    Replace flowforge.example.com with your domain

# 3. Apply all manifests in order
kubectl apply -f deploy/kubernetes/

# 4. Watch rollout
kubectl rollout status deployment/server -n flowforge
kubectl rollout status deployment/executor -n flowforge

# 5. Create the first admin user
kubectl exec -it deployment/server -n flowforge -- \
  flowforge-server create-admin --email admin@example.com --password secret123
```

**What's deployed:**

| Workload | Kind | Replicas | Notes |
|---|---|---|---|
| `postgres` | StatefulSet | 1 | 20Gi PVC, AOF-style persistence |
| `redis` | StatefulSet | 1 | 5Gi PVC, AOF persistence |
| `server` | Deployment | 2 (min) | Runs Alembic migrations on startup |
| `runner` | Deployment | 1 | `Recreate` strategy (Redis consumer group safety) |
| `executor` | Deployment | 2 (min) | 120s termination grace for in-flight LLM steps |
| `dashboard` | Deployment | 2 (min) | Requires image built with `NEXT_PUBLIC_API_URL=/api/v1` |

**Autoscaling (HPA):**

| Target | Min | Max | CPU Threshold | ScaleDown Stabilization |
|---|---|---|---|---|
| `server` | 2 | 8 | 70% | 5 min |
| `executor` | 2 | 20 | 60% | 10 min |

**Ingress routing** (via NGINX, path-based):

```
/api/*  →  server:8000    (preserves full path, 300s timeout for SSE)
/       →  dashboard:3000
```

**Build the dashboard image** (required for API calls to work via Ingress):

```bash
docker build --build-arg NEXT_PUBLIC_API_URL=/api/v1 \
  -t ghcr.io/flowforge/flowforge-dashboard:latest ./dashboard
```

**Secrets management** — the provided `02-secret.yaml` contains only `CHANGE_ME` placeholders. For production, use [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) or [External Secrets Operator](https://external-secrets.io/) pointing to AWS Secrets Manager or HashiCorp Vault.

**Manifest files:**

```
deploy/kubernetes/
├── 00-namespace.yaml          # flowforge namespace
├── 01-configmap.yaml          # Non-sensitive shared config
├── 02-secret.yaml             # Secret template (replace CHANGE_ME values)
├── 10-postgres-statefulset.yaml
├── 11-redis-statefulset.yaml
├── 20-server-deployment.yaml
├── 21-runner-deployment.yaml
├── 22-executor-deployment.yaml
├── 23-dashboard-deployment.yaml
├── 30-hpa.yaml                # Autoscaling for server + executor
└── 40-ingress.yaml            # NGINX Ingress with TLS
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

## Sub-Agents

Sub-agents enable dynamic delegation where a parent agent spawns specialist sub-agents at runtime. Each sub-agent has its own system prompt, tools, and iteration limits.

### SDK Usage

```python
from flowforge import agent_def, sub_agent, step, tool, trigger

# Define tools for specialists
@tool(name="web_search", description="Search the web")
async def web_search(query: str) -> dict:
    return {"results": [...]}

# Define specialist agents
researcher = agent_def(
    name="researcher",
    system="You are a research specialist. Search and synthesize findings.",
    tools=[web_search],
    model="claude-sonnet-4-6",
)

# Wrap as sub-agent tool
research_tool = sub_agent(
    researcher,
    description="Delegate research tasks to a specialist.",
    max_iterations=10,
    max_tool_calls=20,
)

# Use in a parent agent
@flowforge.function(id="manager", trigger=trigger.event("project/plan"))
async def manager(ctx):
    result = await step.agent(
        "manager",
        task=ctx.event.data["goal"],
        model="claude-opus-4-6",
        system="Break work into tasks and delegate to specialists.",
        tools=[research_tool, send_email],
    )
    return result.output
```

### `sub_agent()` Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `agent` | required | `AgentDefinition` from `agent_def()` |
| `description` | auto | Tool description for the parent agent |
| `max_iterations` | 20 | Max LLM round-trips for the sub-agent |
| `max_tool_calls` | 50 | Max tool calls for the sub-agent |
| `temperature` | 0.7 | LLM temperature |
| `context_mode` | `"task_only"` | How much parent context to share: `task_only`, `summary`, `full_history` |

### Server-Side (Inline Functions)

Configure sub-agents in `agent_config` when creating inline functions:

```bash
curl -X POST http://localhost:8000/api/v1/functions/inline \
  -H "Content-Type: application/json" \
  -d '{
    "function_id": "project-manager",
    "name": "Project Manager",
    "trigger_type": "event",
    "trigger_value": "project/plan",
    "system_prompt": "Break work into research and writing tasks...",
    "tools": ["send_email"],
    "agent_config": {
      "model": "claude-opus-4-6",
      "sub_agents": {
        "researcher": {
          "system_prompt": "You are a research specialist...",
          "model": "claude-sonnet-4-6",
          "tools": ["web_search"],
          "max_iterations": 15,
          "description": "Delegate research to a specialist."
        }
      }
    }
  }'
```

### Safety Guards

- **Max nesting depth**: 3 levels (configurable). Prevents infinite sub-agent recursion.
- **Independent limits**: Each sub-agent has its own `max_iterations` and `max_tool_calls`.
- **Step memoization**: Sub-agent steps are checkpointed — if the parent crashes mid-sub-agent, it resumes from the last completed step.

See [`examples/sub_agents.py`](./examples/sub_agents.py) for a complete example.

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

## MCP Server (Claude Integration)

Connect Claude to your FlowForge workflows via the Model Context Protocol. Exposes 25 tools for managing events, functions, runs, tools, approvals, and health checks.

```bash
npm install -g flowforge-mcp-server
# or run directly
npx flowforge-mcp-server --server-url http://localhost:8000 --api-key ff_live_xxx
```

### SSE Mode (recommended)

Start the MCP server as a standalone service:

```bash
npx flowforge-mcp-server --server-url http://localhost:8000 --api-key ff_live_xxx --port 3100
```

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "flowforge": {
      "type": "sse",
      "url": "http://localhost:3100/sse"
    }
  }
}
```

### Stdio Mode (auto-managed by Claude Code)

Add to `.mcp.json` — Claude Code launches and manages the process:

```json
{
  "mcpServers": {
    "flowforge": {
      "type": "stdio",
      "command": "npx",
      "args": ["flowforge-mcp-server", "--transport", "stdio"],
      "env": {
        "FLOWFORGE_SERVER_URL": "http://localhost:8000",
        "FLOWFORGE_API_KEY": "ff_live_xxx"
      }
    }
  }
}
```

### Available Tools

| Category | Tools |
|----------|-------|
| **Events** | `flowforge_send_event`, `flowforge_list_events`, `flowforge_get_event` |
| **Functions** | `flowforge_list_functions`, `flowforge_get_function`, `flowforge_create_function`, `flowforge_update_function`, `flowforge_delete_function` |
| **Runs** | `flowforge_list_runs`, `flowforge_get_run`, `flowforge_cancel_run`, `flowforge_retry_run`, `flowforge_replay_run`, `flowforge_get_run_steps`, `flowforge_get_run_tool_calls` |
| **Tools** | `flowforge_list_tools`, `flowforge_get_tool`, `flowforge_create_tool`, `flowforge_update_tool`, `flowforge_delete_tool` |
| **Approvals** | `flowforge_list_approvals`, `flowforge_approve_tool_call`, `flowforge_reject_tool_call` |
| **Health** | `flowforge_health_check`, `flowforge_get_stats` |

Verify with `/mcp` inside Claude Code to see all connected tools.

See [`packages/flowforge-mcp-server`](./packages/flowforge-mcp-server) for more details.

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
│   ├── flowforge-client-ts/ # TypeScript client
│   └── flowforge-mcp-server/       # MCP server (Claude integration)
├── server/                  # Orchestration server (FastAPI)
├── dashboard/               # Admin dashboard (Next.js)
├── deploy/
│   └── kubernetes/          # Raw K8s manifests (namespace → HPA → Ingress)
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
FLOWFORGE_ENCRYPTION_KEY=your-encryption-key  # Required for 2FA, AI provider keys, and credentials

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
