"""Multi-agent support network for complex customer issues."""

import sys
sys.path.insert(0, "/Users/hootan/Developer/Personal/Random/flowforge-demo")

from flowforge import FlowForge, Context, step, network, agent_def
from flowforge.router import code, llm
from tools import (
    search_knowledge_base,
    get_customer,
    get_customer_orders,
    get_order,
    create_ticket,
    update_ticket_status,
    draft_email,
    send_email,
    process_refund,
    escalate_to_human,
)

flowforge = FlowForge(app_id="support-network")


# =============================================================================
# Agent Definitions
# =============================================================================

classifier_agent = agent_def(
    name="classifier",
    system="""You are a ticket classification agent. Your job is to:
1. Analyze the customer's issue
2. Determine the category (technical, billing, general)
3. Assess the priority and complexity
4. Look up the customer to get context

Output a clear classification that helps route to the right specialist.""",
    tools=[get_customer, get_customer_orders],
)

technical_agent = agent_def(
    name="technical",
    system="""You are a technical support specialist. Your expertise includes:
- Password and account issues
- Login problems
- Technical errors and bugs
- Feature usage questions

Use the knowledge base to find solutions. Be patient and thorough.""",
    tools=[search_knowledge_base, create_ticket, update_ticket_status, draft_email],
)

billing_agent = agent_def(
    name="billing",
    system="""You are a billing specialist. You handle:
- Payment issues
- Refund requests
- Invoice questions
- Subscription changes

For refunds, you can process them (requires approval). Be fair but follow policy.""",
    tools=[
        get_customer,
        get_customer_orders,
        get_order,
        create_ticket,
        update_ticket_status,
        process_refund,
        draft_email,
        send_email,
    ],
)

escalation_agent = agent_def(
    name="escalation",
    system="""You are the escalation handler. You receive cases that:
- Cannot be resolved by other agents
- Require special attention
- Need human judgment

Document the case thoroughly and prepare it for human review.""",
    tools=[create_ticket, update_ticket_status, escalate_to_human],
)


# =============================================================================
# Router Functions
# =============================================================================

def support_router(ctx):
    """
    Route tickets based on classification and state.

    Routing logic:
    1. First iteration -> classifier
    2. After classification -> appropriate specialist
    3. If state.escalated -> escalation
    4. If state.resolved -> None (done)
    """
    # Check terminal conditions
    if ctx.state.get("resolved"):
        return None

    if ctx.state.get("escalated"):
        return "escalation"

    # First iteration: classify
    if ctx.iteration == 0:
        return "classifier"

    # Get classification from state or last result
    category = ctx.state.get("category")

    if not category and ctx.last_result:
        # Try to extract category from classifier output
        output = ctx.last_result.output.lower() if ctx.last_result.output else ""
        if "technical" in output or "password" in output or "login" in output:
            category = "technical"
        elif "billing" in output or "refund" in output or "payment" in output:
            category = "billing"
        else:
            category = "technical"  # default

        ctx.state.set("category", category)

    # Route to specialist
    if category == "billing":
        return "billing"
    elif category == "technical":
        return "technical"
    else:
        return "technical"  # default


# =============================================================================
# Network Definition
# =============================================================================

support_net = network(
    name="support-network",
    agents=[classifier_agent, technical_agent, billing_agent, escalation_agent],
    router=code(support_router),
    default_model="claude-sonnet-4-20250514",
)

# Alternative: LLM-based routing
support_net_llm = network(
    name="support-network-llm",
    agents=[classifier_agent, technical_agent, billing_agent, escalation_agent],
    router=llm(
        model="gpt-4o-mini",
        prompt="""You are routing a customer support ticket to the appropriate agent.

Available agents: {agents}

Current state: {state}
Last agent result: {last_result}

Routing rules:
- Start with 'classifier' to categorize the issue
- Route technical issues (password, login, errors) to 'technical'
- Route billing issues (payments, refunds, invoices) to 'billing'
- Route escalated or unresolvable issues to 'escalation'
- Return 'DONE' when the issue is resolved

Which agent should handle this next? Reply with just the agent name or 'DONE'.""",
        temperature=0.2,
    ),
    default_model="claude-sonnet-4-20250514",
)


# =============================================================================
# Workflow Functions
# =============================================================================

@flowforge.function(
    id="handle-complex-support",
    trigger=flowforge.trigger.event("support/complex"),
    retries=2,
    timeout="45m",
)
async def handle_complex_support(ctx: Context) -> dict:
    """
    Handle complex support tickets using multi-agent network.

    Triggered by: support/complex
    Payload: {
        "customer_id": "c_123",
        "description": "Billing issue with double charge, need refund",
        "priority": "high"
    }
    """
    customer_id = ctx.event.data.get("customer_id", "unknown")
    description = ctx.event.data.get("description", "")
    priority = ctx.event.data.get("priority", "medium")

    ctx.log(f"Starting multi-agent support for customer: {customer_id}")

    # Execute the support network
    result = await step.network(
        "support-network-execution",
        network=support_net,
        input=f"""Customer Support Request:

Customer ID: {customer_id}
Priority: {priority}

Issue Description:
{description}

Please classify this issue, route to the appropriate specialist, and resolve it.
If you cannot resolve it, escalate to human support.
""",
        initial_state={
            "customer_id": customer_id,
            "priority": priority,
            "resolved": False,
            "escalated": False,
        },
        max_iterations=8,
    )

    ctx.log(f"Network completed: {result.status}")
    ctx.log(f"Agents involved: {[c['agent'] for c in result.agent_calls]}")

    return {
        "customer_id": customer_id,
        "status": result.status,
        "resolution": result.output,
        "agents_used": [c["agent"] for c in result.agent_calls],
        "iterations": result.iterations,
        "final_state": result.state,
        "total_tokens": result.total_tokens,
        "estimated_cost": f"${result.total_cost_usd:.4f}",
    }


@flowforge.function(
    id="handle-support-llm-router",
    trigger=flowforge.trigger.event("support/complex-llm"),
    retries=2,
    timeout="45m",
)
async def handle_support_llm_router(ctx: Context) -> dict:
    """
    Handle complex support using LLM-based routing.

    Same as above but uses AI to decide routing instead of code.

    Triggered by: support/complex-llm
    """
    customer_id = ctx.event.data.get("customer_id", "unknown")
    description = ctx.event.data.get("description", "")

    ctx.log(f"Starting LLM-routed support for customer: {customer_id}")

    result = await step.network(
        "support-network-llm",
        network=support_net_llm,
        input=f"Customer {customer_id}: {description}",
        initial_state={"customer_id": customer_id},
        max_iterations=8,
    )

    return {
        "customer_id": customer_id,
        "status": result.status,
        "resolution": result.output,
        "agents_used": [c["agent"] for c in result.agent_calls],
        "routing": "llm-based",
    }


if __name__ == "__main__":
    flowforge.serve(
        functions=[handle_complex_support, handle_support_llm_router],
        port=8083,
    )
