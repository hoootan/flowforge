"""
Example: Multi-Agent Network Execution

This example demonstrates FlowForge's step.network() primitive for orchestrating
multiple agents with shared state and intelligent routing.

Scenario: Customer support network
- Classifier: Determines if issue is technical or billing
- Technical Support: Handles technical issues
- Billing Support: Handles billing issues
- Router: Decides which agent to invoke based on classification
"""

import flowforge
from flowforge import tool, agent_def, network
from flowforge.router import code


# Define tools for agents
@tool(
    name="classify_issue",
    description="Classify a customer issue as 'technical' or 'billing'"
)
async def classify_issue(issue_description: str) -> dict:
    """
    Classify the customer issue.

    In a real implementation, this might call an ML model or rule engine.
    For this example, we use simple keyword matching.
    """
    issue_lower = issue_description.lower()

    if any(word in issue_lower for word in ["password", "login", "error", "crash", "bug"]):
        return {
            "category": "technical",
            "confidence": 0.9,
            "reasoning": "Issue contains technical keywords"
        }
    elif any(word in issue_lower for word in ["refund", "charge", "payment", "bill", "invoice"]):
        return {
            "category": "billing",
            "confidence": 0.85,
            "reasoning": "Issue contains billing keywords"
        }
    else:
        return {
            "category": "general",
            "confidence": 0.5,
            "reasoning": "Unable to clearly categorize"
        }


@tool(
    name="search_knowledge_base",
    description="Search technical knowledge base for solutions"
)
async def search_knowledge_base(query: str) -> dict:
    """Search the knowledge base for technical solutions."""
    # Simulated KB search
    return {
        "results": [
            {
                "title": "Password Reset Guide",
                "content": "To reset your password, go to Settings > Security > Reset Password",
                "relevance": 0.95
            }
        ]
    }


@tool(
    name="check_billing_history",
    description="Check customer's billing history and charges"
)
async def check_billing_history(customer_id: str) -> dict:
    """Check customer billing history."""
    # Simulated billing lookup
    return {
        "customer_id": customer_id,
        "recent_charges": [
            {"date": "2026-01-15", "amount": 29.99, "description": "Monthly subscription"},
            {"date": "2026-01-01", "amount": 9.99, "description": "Add-on feature"}
        ],
        "total_owed": 0.00
    }


@tool(
    name="handoff_to_agent",
    description="Handoff to another agent in the network"
)
async def handoff_to_agent(agent_name: str, reason: str) -> dict:
    """Handoff to another specialized agent."""
    return {
        "__handoff__": agent_name,
        "reason": reason
    }


# Define agents in the network
classifier = agent_def(
    name="classifier",
    system="""You are a customer service classifier. Your job is to:
1. Analyze the customer's issue
2. Use the classify_issue tool to categorize it
3. Store the category in network state
4. Handoff to the appropriate specialist agent

Always use the classify_issue tool first, then use handoff_to_agent to route to either 'technical_support' or 'billing_support'.""",
    tools=[classify_issue, handoff_to_agent],
    model="gpt-5-mini",
)

technical_support = agent_def(
    name="technical_support",
    system="""You are a technical support specialist. Your job is to:
1. Search the knowledge base for solutions
2. Provide clear technical guidance
3. Ask follow-up questions if needed
4. Mark issue as resolved in state when complete

Use search_knowledge_base to find solutions. When the issue is resolved, set state['resolved'] = True.""",
    tools=[search_knowledge_base],
    model="claude-sonnet-4-6",
)

billing_support = agent_def(
    name="billing_support",
    system="""You are a billing support specialist. Your job is to:
1. Check customer billing history
2. Explain charges clearly
3. Process refunds if appropriate
4. Mark issue as resolved in state when complete

Use check_billing_history to investigate. When resolved, set state['resolved'] = True.""",
    tools=[check_billing_history],
    model="claude-sonnet-4-6",
)


# Define routing logic
def support_router(ctx):
    """
    Route between agents based on network state and iteration.

    Flow:
    1. Start with classifier (iteration 0)
    2. After classification, route to appropriate specialist
    3. Continue until issue is resolved or max iterations
    """
    # First iteration: always start with classifier
    if ctx.iteration == 0:
        return ctx.agents["classifier"]

    # Check if issue is resolved
    if ctx.state.get("resolved"):
        return None  # Network complete

    # Route based on classification
    category = ctx.state.get("category")

    if category == "technical":
        return ctx.agents["technical_support"]
    elif category == "billing":
        return ctx.agents["billing_support"]
    else:
        # Unknown category - end network
        return None


# Create the network
support_network = network(
    name="customer-support",
    agents=[classifier, technical_support, billing_support],
    router=code(support_router),
    default_model="gpt-5-mini",
)


# FlowForge function that uses the network
@flowforge.function(
    name="handle-support-ticket",
    trigger=flowforge.trigger.event("support/ticket/created"),
)
async def handle_support_ticket(ctx, step):
    """
    Handle a customer support ticket using the multi-agent network.

    The network will:
    1. Classify the issue
    2. Route to the appropriate specialist
    3. Resolve the issue
    4. Return the final resolution
    """
    # Extract ticket data
    ticket = ctx.event.data
    customer_issue = ticket.get("description", "")
    customer_id = ticket.get("customer_id", "unknown")

    # Execute the multi-agent network
    result = await step.network(
        "support-network-execution",
        network=support_network,
        input=f"Customer issue: {customer_issue}",
        initial_state={
            "customer_id": customer_id,
            "ticket_id": ticket.get("id"),
            "resolved": False,
        },
        max_iterations=10,
    )

    # Log network execution metrics
    print(f"Network completed with status: {result.status}")
    print(f"Total iterations: {result.iterations}")
    print(f"Agents invoked: {len(result.agent_calls)}")
    print(f"Total tokens used: {result.total_tokens}")
    print(f"Estimated cost: ${result.total_cost_usd:.4f}")

    # Extract final resolution
    resolution = result.output

    # Send resolution notification
    await step.send_event(
        "send-resolution-email",
        name="support/ticket/resolved",
        data={
            "ticket_id": ticket.get("id"),
            "customer_id": customer_id,
            "resolution": resolution,
            "agent_calls": result.agent_calls,
            "status": result.status,
        }
    )

    return {
        "ticket_id": ticket.get("id"),
        "status": "resolved" if result.status == "completed" else "escalated",
        "resolution": resolution,
        "iterations": result.iterations,
        "final_state": result.state,
    }
