"""
FlowForge Demo Application

A comprehensive demo showcasing FlowForge's AI agent capabilities:
- Single agents with tool calling
- Multi-agent networks with routing
- Human-in-the-loop approvals

Run with:
    cd src
    flowforge dev .

Test with:
    # Research agent
    flowforge send research/request -d '{"topic": "AI trends 2024"}'

    # Support agent
    flowforge send support/ticket -d '{"customer_id": "c_123", "description": "Cannot reset password"}'

    # Multi-agent network
    flowforge send support/complex -d '{"customer_id": "c_123", "description": "Double charged, need refund"}'
"""

import sys
from pathlib import Path

# Add project root to path for tools import
sys.path.insert(0, str(Path(__file__).parent.parent))

from flowforge import FlowForge, Context, step
from tools import (
    # Search tools
    search_web,
    fetch_article,
    search_knowledge_base,
    # Database tools
    get_customer,
    get_customer_orders,
    get_order,
    create_ticket,
    update_ticket_status,
    save_notes,
    # Email tools (some with HITL)
    send_email,
    draft_email,
    process_refund,
    escalate_to_human,
)

# Import network components
from flowforge import network, agent_def
from flowforge.router import code

flowforge = FlowForge(app_id="flowforge-demo")


# =============================================================================
# Single Agent Workflows
# =============================================================================

@flowforge.function(
    id="research-topic",
    trigger=flowforge.trigger.event("research/request"),
    retries=3,
    timeout="30m",
)
async def research_topic(ctx: Context) -> dict:
    """
    Research a topic using a single AI agent.

    Example:
        flowforge send research/request -d '{"topic": "quantum computing advances"}'
    """
    topic = ctx.event.data.get("topic", "")

    ctx.log(f"Researching: {topic}")

    result = await step.agent(
        "research",
        task=f"Research and summarize: {topic}. Use search tools to find information, then save your findings.",
        model="claude-sonnet-4-6",
        system="You are a research assistant. Be thorough and cite sources.",
        tools=[search_web, fetch_article, save_notes],
        max_iterations=10,
    )

    return {
        "topic": topic,
        "summary": result.output,
        "status": result.status,
        "iterations": result.iterations,
    }


@flowforge.function(
    id="handle-support",
    trigger=flowforge.trigger.event("support/ticket"),
    retries=3,
    timeout="30m",
)
async def handle_support(ctx: Context) -> dict:
    """
    Handle a support ticket with a single agent.

    Example:
        flowforge send support/ticket -d '{"customer_id": "c_123", "description": "Cannot login"}'
    """
    customer_id = ctx.event.data.get("customer_id", "")
    description = ctx.event.data.get("description", "")

    ctx.log(f"Support ticket from {customer_id}: {description}")

    result = await step.agent(
        "support",
        task=f"""Handle support request from customer {customer_id}:

{description}

Look up the customer, search the knowledge base, create a ticket, and resolve if possible.
If you need to send an email, it will require approval.""",
        model="claude-sonnet-4-6",
        system="You are a helpful customer support agent. Be empathetic and thorough.",
        tools=[
            get_customer,
            get_customer_orders,
            search_knowledge_base,
            create_ticket,
            update_ticket_status,
            draft_email,
            send_email,
            escalate_to_human,
        ],
        max_iterations=15,
    )

    return {
        "customer_id": customer_id,
        "resolution": result.output,
        "status": result.status,
    }


# =============================================================================
# Multi-Agent Network Workflows
# =============================================================================

# Define specialized agents
classifier = agent_def(
    name="classifier",
    system="Classify support tickets by category (technical, billing, general) and priority.",
    tools=[get_customer],
)

technical_support = agent_def(
    name="technical",
    system="Handle technical issues: passwords, logins, errors. Search KB for solutions.",
    tools=[search_knowledge_base, create_ticket, update_ticket_status, draft_email],
)

billing_support = agent_def(
    name="billing",
    system="Handle billing: payments, refunds, invoices. Can process refunds with approval.",
    tools=[get_order, create_ticket, process_refund, draft_email, send_email],
)


def ticket_router(ctx):
    """Route tickets based on classification."""
    if ctx.state.get("resolved"):
        return None

    if ctx.iteration == 0:
        return "classifier"

    # Route based on category from classification
    output = ctx.last_result.output.lower() if ctx.last_result else ""

    if "billing" in output or "refund" in output:
        return "billing"
    elif "technical" in output or "password" in output:
        return "technical"

    return None  # Done if can't determine


support_network = network(
    name="support-net",
    agents=[classifier, technical_support, billing_support],
    router=code(ticket_router),
    default_model="claude-sonnet-4-6",
)


@flowforge.function(
    id="handle-complex-support",
    trigger=flowforge.trigger.event("support/complex"),
    retries=2,
    timeout="45m",
)
async def handle_complex_support(ctx: Context) -> dict:
    """
    Handle complex support with multi-agent network.

    Example:
        flowforge send support/complex -d '{"customer_id": "c_123", "description": "Double charge, need refund"}'
    """
    customer_id = ctx.event.data.get("customer_id", "")
    description = ctx.event.data.get("description", "")

    ctx.log(f"Complex support from {customer_id}")

    result = await step.network(
        "complex-support",
        network=support_network,
        input=f"Customer {customer_id}: {description}",
        initial_state={"customer_id": customer_id, "resolved": False},
        max_iterations=6,
    )

    return {
        "customer_id": customer_id,
        "resolution": result.output,
        "status": result.status,
        "agents_used": [c["agent"] for c in result.agent_calls],
        "iterations": result.iterations,
    }


# =============================================================================
# Health Check
# =============================================================================

@flowforge.function(
    id="health-check",
    trigger=flowforge.trigger.event("system/health"),
)
async def health_check(ctx: Context) -> dict:
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "app_id": "flowforge-demo",
        "features": [
            "single-agent",
            "multi-agent-network",
            "tool-calling",
            "hitl-approvals",
        ],
    }


# =============================================================================
# Main Entry Point
# =============================================================================

FUNCTIONS = [
    research_topic,
    handle_support,
    handle_complex_support,
    health_check,
]


def main():
    """Run the FlowForge demo application."""
    import os

    print("Starting FlowForge Demo Application")
    print("=" * 50)
    print("Available workflows:")
    print("  - research/request     : Research a topic")
    print("  - support/ticket       : Handle support ticket")
    print("  - support/complex      : Multi-agent support")
    print("  - system/health        : Health check")
    print("=" * 50)

    # Check if we should run as worker (connected to central server)
    server_url = os.environ.get("FLOWFORGE_SERVER_URL")
    worker_url = os.environ.get("FLOWFORGE_WORKER_URL")
    port = int(os.environ.get("FLOWFORGE_PORT", "8080"))

    if server_url:
        # Worker mode - connect to central server
        print(f"\nRunning as WORKER connected to: {server_url}")
        flowforge.work(
            functions=FUNCTIONS,
            server_url=server_url,
            worker_url=worker_url,
            port=port,
        )
    else:
        # Dev mode - standalone server
        print("\nRunning in DEV mode (standalone)")
        flowforge.serve(
            functions=FUNCTIONS,
            port=port,
        )


if __name__ == "__main__":
    main()
