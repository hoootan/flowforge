# FlowForge Demo - AI Agent Workflows

A sample project demonstrating FlowForge's AI agent capabilities including:

- **Tool Calling**: Define tools that LLMs can use
- **Single Agents**: Autonomous agents with `step.agent()`
- **Multi-Agent Networks**: Collaborative agents with `step.network()`
- **Human-in-the-Loop**: Approval workflows for sensitive operations

## Project Structure

```
flowforge-demo/
├── src/
│   ├── app.py              # Main FlowForge application
│   ├── agents/
│   │   ├── research.py     # Research agent
│   │   ├── support.py      # Customer support agent
│   │   └── writer.py       # Content writer agent
│   └── networks/
│       └── support_network.py  # Multi-agent support network
├── tools/
│   ├── search.py           # Web search tools
│   ├── database.py         # Database tools
│   └── email.py            # Email tools (with HITL)
├── pyproject.toml
└── README.md
```

## Setup

```bash
# Install dependencies
pip install -e ../flowforge/packages/flowforge-sdk

# Or if flowforge is published
pip install flowforge
```

## Running

```bash
# Start the development server
cd src
flowforge dev .

# In another terminal, send test events:

# Test single agent
flowforge send research/request -d '{"topic": "AI trends in 2024"}'

# Test support agent
flowforge send support/ticket -d '{"description": "Cannot reset my password"}'

# Test multi-agent network
flowforge send support/complex -d '{"description": "Billing issue with refund request"}'
```

## Features Demonstrated

### 1. Tool Definition

```python
from flowforge import tool

@tool(name="search_web", description="Search the web for information")
async def search_web(query: str, max_results: int = 5) -> dict:
    # Tool implementation
    return {"results": [...]}
```

### 2. Single Agent

```python
result = await step.agent(
    "research-task",
    task="Research AI trends",
    model="claude-sonnet-4-20250514",
    system="You are a research assistant",
    tools=[search_web, save_notes],
    max_iterations=10,
)
```

### 3. Multi-Agent Network

```python
from flowforge import network, agent_def
from flowforge.router import code

support_network = network(
    name="support",
    agents=[classifier, support, billing],
    router=code(my_router),
)

result = await step.network(
    "support-flow",
    network=support_network,
    input="Customer complaint...",
)
```

### 4. Human-in-the-Loop

```python
@tool(
    name="send_email",
    description="Send email to customer",
    requires_approval=True,  # Pauses for human approval
    approval_timeout="1h",
)
async def send_email(to: str, subject: str, body: str) -> dict:
    return {"sent": True}
```

## Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
FLOWFORGE_HOST=0.0.0.0
FLOWFORGE_PORT=8080
```

## API Endpoints

When running, the following endpoints are available:

- `POST /api/v1/events` - Send events to trigger workflows
- `GET /api/v1/runs` - List workflow runs
- `GET /api/v1/runs/{id}` - Get run details
- `GET /api/v1/approvals` - List pending approvals
- `POST /api/v1/approvals/{id}/approve` - Approve a tool call
- `POST /api/v1/approvals/{id}/reject` - Reject a tool call
