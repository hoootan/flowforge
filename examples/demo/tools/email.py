"""Email tools for FlowForge agents with HITL support."""

from flowforge import tool


@tool(
    name="send_email",
    description="Send an email to a customer. Requires human approval before sending.",
    requires_approval=True,
    approval_timeout="1h",
)
async def send_email(to: str, subject: str, body: str) -> dict:
    """
    Send an email to a customer.

    This tool requires human approval before execution to prevent
    accidental or inappropriate emails being sent.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content

    Returns:
        Email send confirmation
    """
    # In a real implementation, this would send via SMTP/API
    print(f"[EMAIL] Sending to: {to}")
    print(f"[EMAIL] Subject: {subject}")
    print(f"[EMAIL] Body: {body[:100]}...")

    return {
        "sent": True,
        "to": to,
        "subject": subject,
        "message_id": f"msg_{hash(to + subject) % 100000:05d}",
    }


@tool(
    name="draft_email",
    description="Draft an email without sending (no approval required)",
)
async def draft_email(to: str, subject: str, body: str) -> dict:
    """
    Draft an email for review.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content

    Returns:
        Draft email information
    """
    return {
        "draft": True,
        "to": to,
        "subject": subject,
        "body": body,
        "draft_id": f"draft_{hash(to + subject) % 100000:05d}",
    }


@tool(
    name="process_refund",
    description="Process a refund for an order. Requires human approval.",
    requires_approval=True,
    approval_timeout="4h",
)
async def process_refund(order_id: str, amount: float, reason: str) -> dict:
    """
    Process a refund for an order.

    This is a sensitive financial operation that requires human approval.

    Args:
        order_id: Order ID to refund
        amount: Refund amount in USD
        reason: Reason for refund

    Returns:
        Refund confirmation
    """
    print(f"[REFUND] Processing refund for order: {order_id}")
    print(f"[REFUND] Amount: ${amount:.2f}")
    print(f"[REFUND] Reason: {reason}")

    return {
        "processed": True,
        "order_id": order_id,
        "amount": amount,
        "refund_id": f"ref_{hash(order_id) % 100000:05d}",
    }


@tool(
    name="escalate_to_human",
    description="Escalate the issue to a human agent",
)
async def escalate_to_human(reason: str, context: str, priority: str = "medium") -> dict:
    """
    Escalate issue to human agent.

    Use this when the AI cannot resolve the issue or when
    human judgment is required.

    Args:
        reason: Why escalation is needed
        context: Relevant context for the human agent
        priority: Escalation priority (low, medium, high, urgent)

    Returns:
        Escalation confirmation with handoff directive
    """
    return {
        "__handoff__": "human_escalation",
        "reason": reason,
        "context": context,
        "priority": priority,
        "escalation_id": f"esc_{hash(reason) % 100000:05d}",
    }
