"""Customer support agent for handling support tickets."""

import sys
sys.path.insert(0, "/Users/hootan/Developer/Personal/Random/flowforge-demo")

from flowforge import FlowForge, Context, step
from tools import (
    search_knowledge_base,
    get_customer,
    get_customer_orders,
    create_ticket,
    update_ticket_status,
    draft_email,
    send_email,
    escalate_to_human,
)

flowforge = FlowForge(app_id="support-agent")


@flowforge.function(
    id="handle-support-ticket",
    trigger=flowforge.trigger.event("support/ticket"),
    retries=3,
    timeout="30m",
)
async def handle_support_ticket(ctx: Context) -> dict:
    """
    Handle a customer support ticket.

    Triggered by: support/ticket
    Payload: {
        "customer_id": "c_123",
        "description": "I cannot reset my password",
        "priority": "medium"
    }
    """
    customer_id = ctx.event.data.get("customer_id", "unknown")
    description = ctx.event.data.get("description", "")
    priority = ctx.event.data.get("priority", "medium")

    ctx.log(f"Handling support ticket for customer: {customer_id}")
    ctx.log(f"Issue: {description}")

    # Use agent to handle the support ticket
    result = await step.agent(
        "support-agent",
        task=f"""Handle this customer support ticket:

Customer ID: {customer_id}
Issue Description: {description}
Priority: {priority}

Instructions:
1. First, look up the customer information using get_customer
2. Search the knowledge base for relevant solutions
3. Create a ticket to track this issue
4. If you can resolve the issue, draft a response email
5. If you need to send the email, use send_email (requires approval)
6. If you cannot resolve, escalate to human agent
7. Update the ticket status when resolved

Be helpful, empathetic, and professional.
""",
        model="claude-sonnet-4-20250514",
        system="""You are a friendly and helpful customer support agent. Your goals are:
- Understand the customer's issue completely
- Find the best solution from the knowledge base
- Communicate clearly and empathetically
- Escalate when necessary rather than guessing
- Always create a ticket for tracking
- Document your resolution""",
        tools=[
            search_knowledge_base,
            get_customer,
            get_customer_orders,
            create_ticket,
            update_ticket_status,
            draft_email,
            send_email,
            escalate_to_human,
        ],
        max_iterations=20,
        temperature=0.5,
    )

    ctx.log(f"Support ticket handled: {result.status}")

    return {
        "customer_id": customer_id,
        "status": result.status,
        "resolution": result.output,
        "iterations": result.iterations,
        "tool_calls": result.tool_calls_count,
    }


if __name__ == "__main__":
    flowforge.serve(
        functions=[handle_support_ticket],
        port=8082,
    )
