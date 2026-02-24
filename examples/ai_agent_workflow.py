"""
AI Agent workflow example.

This example demonstrates building an AI-powered workflow that:
- Uses multiple AI calls with different models
- Handles human-in-the-loop approval
- Chains multiple steps together

Run with:
    cd examples
    flowforge dev .

Send an event:
    flowforge send support/ticket-created -d '{"ticket_id": "T123", "subject": "Help with billing", "body": "I was charged twice for my subscription"}'
"""

from flowforge import FlowForge, Context, step

flowforge = FlowForge(app_id="ai-agent-example")


@flowforge.function(
    id="process-support-ticket",
    trigger=flowforge.trigger.event("support/ticket-created"),
    retries=3,
    timeout="30m",
    concurrency=flowforge.concurrency(limit=5),  # Max 5 concurrent tickets
)
async def process_support_ticket(ctx: Context) -> dict:
    """
    AI-powered support ticket processor.

    1. Categorize the ticket using AI
    2. Generate a draft response
    3. Wait for human approval (if high priority)
    4. Send the response
    """
    ticket = ctx.event.data
    ctx.log(f"Processing ticket {ticket.get('ticket_id')}")

    # Step 1: Categorize the ticket
    categorization = await step.ai(
        "categorize-ticket",
        model="gpt-5-mini",  # Fast model for categorization
        prompt=f"""Categorize this support ticket:

Subject: {ticket.get('subject')}
Body: {ticket.get('body')}

Respond with JSON:
{{
    "category": "billing" | "technical" | "account" | "other",
    "priority": "low" | "medium" | "high",
    "sentiment": "positive" | "neutral" | "negative"
}}""",
        temperature=0.3,  # Low temperature for consistent categorization
    )
    ctx.log(f"Categorization: {categorization}")

    # Step 2: Generate draft response using a more capable model
    draft_response = await step.ai(
        "generate-response",
        model="claude-sonnet-4-6",  # Use Claude for better writing
        messages=[
            {
                "role": "system",
                "content": """You are a helpful customer support agent.
                Write empathetic, clear responses. Be concise but thorough."""
            },
            {
                "role": "user",
                "content": f"""Generate a response for this ticket:

Subject: {ticket.get('subject')}
Body: {ticket.get('body')}
Category: {categorization.get('content', {}).get('category', 'unknown')}

Write a professional, helpful response."""
            }
        ],
        max_tokens=500,
    )
    ctx.log(f"Draft response generated")

    # Step 3: If high priority or negative sentiment, wait for human approval
    priority = categorization.get("content", {}).get("priority", "low")
    sentiment = categorization.get("content", {}).get("sentiment", "neutral")

    needs_approval = priority == "high" or sentiment == "negative"

    if needs_approval:
        ctx.log("Waiting for human approval...")

        # Wait for approval event (or timeout after 4 hours)
        approval = await step.wait_for_event(
            "wait-for-approval",
            event="support/response-approved",
            match=f"data.ticket_id == '{ticket.get('ticket_id')}'",
            timeout="4h",
        )

        if approval is None:
            # Timed out waiting for approval
            ctx.log("Approval timed out, escalating ticket")
            return {
                "status": "escalated",
                "ticket_id": ticket.get("ticket_id"),
                "reason": "approval_timeout",
            }

        if not approval.get("data", {}).get("approved"):
            ctx.log("Response rejected, needs manual handling")
            return {
                "status": "rejected",
                "ticket_id": ticket.get("ticket_id"),
            }

    # Step 4: Send the response (simulated)
    async def send_response(ticket_id: str, response: str) -> dict:
        print(f"  Sending response for ticket {ticket_id}")
        return {"sent": True, "ticket_id": ticket_id}

    send_result = await step.run(
        "send-response",
        send_response,
        ticket.get("ticket_id"),
        draft_response.get("content", ""),
    )

    # Step 5: Notify about completion
    await step.send_event(
        "notify-completion",
        name="support/ticket-resolved",
        data={
            "ticket_id": ticket.get("ticket_id"),
            "category": categorization.get("content", {}).get("category"),
            "required_approval": needs_approval,
        },
    )

    return {
        "status": "completed",
        "ticket_id": ticket.get("ticket_id"),
        "category": categorization.get("content", {}).get("category"),
        "priority": priority,
    }


@flowforge.function(
    id="notify-team",
    trigger=flowforge.trigger.event("support/ticket-resolved"),
)
async def notify_team(ctx: Context) -> dict:
    """Notify the team when a ticket is resolved."""
    data = ctx.event.data

    ctx.log(f"Ticket {data.get('ticket_id')} resolved!")

    return {"notified": True}


if __name__ == "__main__":
    flowforge.serve(
        functions=[process_support_ticket, notify_team],
        port=8080,
    )
