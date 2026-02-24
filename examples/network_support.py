"""
Example: Customer Support Multi-Agent Network

This example demonstrates a customer support network with 3 agents:
- Classifier: Categorizes support tickets (technical, billing, general)
- Support: Provides technical support with KB search
- Escalation: Handles issues requiring human attention

The router uses code-based logic to direct tickets through the appropriate agents.
"""

import flowforge
from flowforge import tool, agent_def, network
from flowforge.router import code


# Define tools
@tool(name="classify_ticket", description="Classify support ticket")
async def classify_ticket(description: str) -> dict:
    """
    Classify a support ticket into categories.

    Args:
        description: The ticket description text

    Returns:
        Classification result with category and confidence
    """
    description_lower = description.lower()

    # Simulated classification logic
    if any(word in description_lower for word in ["password", "login", "access", "error"]):
        return {
            "category": "technical",
            "confidence": 0.9,
            "reasoning": "Contains technical keywords"
        }
    elif any(word in description_lower for word in ["refund", "billing", "charge", "payment"]):
        return {
            "category": "billing",
            "confidence": 0.85,
            "reasoning": "Contains billing keywords"
        }
    else:
        return {
            "category": "general",
            "confidence": 0.7,
            "reasoning": "General inquiry"
        }


@tool(name="search_kb", description="Search knowledge base")
async def search_kb(query: str) -> dict:
    """
    Search the knowledge base for solutions.

    Args:
        query: Search query string

    Returns:
        Relevant articles from knowledge base
    """
    # Simulated KB search
    return {
        "articles": [
            {
                "title": "How to reset password",
                "url": "https://help.example.com/reset-password",
                "excerpt": "Follow these steps to reset your password securely...",
                "relevance": 0.95
            },
            {
                "title": "Login troubleshooting guide",
                "url": "https://help.example.com/login-issues",
                "excerpt": "Common login issues and solutions...",
                "relevance": 0.82
            }
        ]
    }


@tool(name="escalate", description="Escalate to human")
async def escalate(reason: str) -> dict:
    """
    Escalate issue to human agent.

    Args:
        reason: Reason for escalation

    Returns:
        Handoff directive to escalation agent
    """
    return {
        "__handoff__": "escalation",
        "reason": reason,
        "timestamp": "2026-01-23T12:00:00Z"
    }


# Define agents
classifier = agent_def(
    name="classifier",
    system="""You classify support tickets. Use the classify_ticket tool to categorize the issue.
After classification, set the category in network state using state.set('category', <category>).
Return the classification results.""",
    tools=[classify_ticket],
    model="gpt-5-mini",
)

support = agent_def(
    name="support",
    system="""You provide technical support. Search the knowledge base for solutions and help the customer.
If you can resolve the issue, set state.set('resolved', True).
If the issue needs escalation, use the escalate tool.""",
    tools=[search_kb, escalate],
    model="claude-sonnet-4-6",
)

escalation = agent_def(
    name="escalation",
    system="""You handle escalated issues requiring human attention.
Provide instructions to the customer on next steps and timeline for human review.
Set state.set('resolved', True) when complete.""",
    tools=[],
    model="claude-sonnet-4-6",
)


# Router function
def support_router(ctx):
    """
    Route between agents based on classification and state.

    Args:
        ctx: RouterContext with iteration, state, last_result, etc.

    Returns:
        Next agent to execute, or None to complete network
    """
    # First iteration: start with classifier
    if ctx.iteration == 0:
        return "classifier"

    # Check if escalated
    if ctx.state.get("escalated"):
        return "escalation"

    # Check if resolved
    if ctx.state.get("resolved"):
        return None  # Network complete

    # Route based on classification result
    last_output = ctx.last_result.output if ctx.last_result else ""
    category = ctx.state.get("category")

    if category == "technical" or "technical" in last_output.lower():
        return "support"
    elif category == "billing" or "billing" in last_output.lower():
        return "support"  # In this example, support handles both

    # Default: end network
    return None


# Create the network
support_network = network(
    name="support",
    agents=[classifier, support, escalation],
    router=code(support_router),
    default_model="gpt-5-mini",
)


# FlowForge function using the network
@flowforge.function(
    name="handle-support-ticket",
    trigger=flowforge.trigger.event("support/ticket"),
)
async def handle_ticket(ctx, step) -> dict:
    """
    Handle a support ticket through the multi-agent network.

    Args:
        ctx: FlowForge context with event data
        step: Step manager for durable execution

    Returns:
        Ticket resolution result
    """
    ticket_data = ctx.event.data
    description = ticket_data.get("description", "")
    ticket_id = ticket_data.get("ticket_id", "unknown")

    # Execute the network
    result = await step.network(
        "support-flow",
        network=support_network,
        input=description,
        initial_state={"ticket_id": ticket_id},
        max_iterations=5,
    )

    # Log results
    print(f"Support network completed:")
    print(f"  Status: {result.status}")
    print(f"  Iterations: {result.iterations}")
    print(f"  Agents called: {len(result.agent_calls)}")
    print(f"  Total tokens: {result.total_tokens}")
    print(f"  Cost: ${result.total_cost_usd:.4f}")

    return {
        "ticket_id": ticket_id,
        "status": result.status,
        "resolution": result.output,
        "iterations": result.iterations,
        "final_state": result.state,
    }
