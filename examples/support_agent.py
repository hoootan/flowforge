"""
Example: Customer Support Agent with Human-in-the-Loop

This example demonstrates a customer support agent that can:
- Search knowledge base
- Check order status
- Process refunds (with approval)
- Escalate to human agent when needed
"""

import flowforge
from flowforge import tool, Context


# Knowledge base search tool
@tool(
    name="search_kb",
    description="Search the knowledge base for help articles and documentation",
)
async def search_knowledge_base(query: str, category: str = "all") -> dict:
    """
    Search the customer support knowledge base.

    Args:
        query: Search query (e.g., "how to reset password")
        category: Category filter ("billing", "technical", "shipping", "all")

    Returns:
        Relevant knowledge base articles
    """
    # Simulate KB search
    articles = {
        "password": {
            "title": "How to Reset Your Password",
            "category": "technical",
            "content": "1. Click 'Forgot Password' on login page\n2. Enter your email\n3. Check email for reset link\n4. Create new password",
            "helpful_count": 245
        },
        "refund": {
            "title": "Refund Policy",
            "category": "billing",
            "content": "We offer full refunds within 30 days of purchase. Contact support to initiate a refund.",
            "helpful_count": 189
        },
        "shipping": {
            "title": "Shipping Times and Tracking",
            "category": "shipping",
            "content": "Standard shipping: 5-7 business days\nExpress: 2-3 business days\nTrack orders in your account dashboard.",
            "helpful_count": 312
        },
    }

    # Simple keyword matching
    results = []
    for key, article in articles.items():
        if key in query.lower() or query.lower() in article["title"].lower():
            if category == "all" or article["category"] == category:
                results.append(article)

    return {
        "query": query,
        "category": category,
        "results": results,
        "total": len(results)
    }


# Order lookup tool
@tool(
    name="get_order",
    description="Look up order details by order ID or customer email",
)
async def get_order_details(order_id: str = None, email: str = None) -> dict:
    """
    Retrieve order information from the system.

    Args:
        order_id: Order ID (e.g., "ORD-12345")
        email: Customer email to find their orders

    Returns:
        Order details including status, items, and tracking
    """
    # Simulate order lookup
    if order_id:
        return {
            "order_id": order_id,
            "status": "shipped",
            "customer_email": "customer@example.com",
            "items": [
                {"name": "Product A", "quantity": 2, "price": 29.99},
                {"name": "Product B", "quantity": 1, "price": 49.99},
            ],
            "total": 109.97,
            "shipping_status": "In Transit",
            "tracking_number": "TRK123456789",
            "estimated_delivery": "2025-01-26",
        }
    elif email:
        return {
            "customer_email": email,
            "orders": [
                {"order_id": "ORD-12345", "status": "shipped", "total": 109.97},
                {"order_id": "ORD-12344", "status": "delivered", "total": 59.99},
            ]
        }
    else:
        return {"error": "Must provide either order_id or email"}


# Check inventory
@tool(
    name="check_inventory",
    description="Check product availability and stock levels",
)
async def check_inventory(product_id: str = None, product_name: str = None) -> dict:
    """
    Check if a product is in stock.

    Args:
        product_id: Product ID (e.g., "PROD-123")
        product_name: Product name to search

    Returns:
        Stock availability and estimated restock date if out of stock
    """
    return {
        "product_id": product_id or "PROD-123",
        "product_name": product_name or "Example Product",
        "in_stock": True,
        "quantity": 45,
        "warehouse_locations": ["NY", "CA"],
    }


# Process refund (requires approval)
@tool(
    name="process_refund",
    description="Process a refund for an order - requires manager approval",
    requires_approval=True,
    approval_timeout="30m",
)
async def process_refund(order_id: str, amount: float, reason: str) -> dict:
    """
    Process a customer refund (requires human approval).

    Args:
        order_id: Order ID to refund
        amount: Refund amount in USD
        reason: Reason for refund

    Returns:
        Refund confirmation details
    """
    return {
        "status": "processed",
        "order_id": order_id,
        "refund_amount": amount,
        "reason": reason,
        "refund_id": "REF-ABC123",
        "processing_time": "3-5 business days",
    }


# Escalate to human
@tool(
    name="escalate_to_human",
    description="Escalate the conversation to a human support agent for complex issues",
)
async def escalate_to_human(reason: str, priority: str = "normal") -> dict:
    """
    Create an escalation ticket for human agent.

    Args:
        reason: Why this needs human attention
        priority: Urgency level ("low", "normal", "high", "urgent")

    Returns:
        Escalation ticket details
    """
    return {
        "status": "escalated",
        "ticket_id": "ESCALATE-789",
        "priority": priority,
        "reason": reason,
        "estimated_response": "30 minutes",
        "message": "A human agent will reach out to you shortly.",
    }


# Main support agent function
@flowforge.function(
    id="support-agent",
    name="Customer Support Agent",
    trigger=flowforge.trigger.event("support/request"),
)
async def customer_support_agent(ctx: Context) -> dict:
    """
    AI-powered customer support agent with HITL for sensitive operations.

    This agent can:
    - Answer questions using knowledge base
    - Look up order information
    - Check product availability
    - Process refunds (with manager approval)
    - Escalate complex issues to human agents

    Event payload:
        - customer_email: Customer's email
        - message: Customer's support request
        - order_id: Optional order ID if inquiry is order-specific
    """
    customer_email = ctx.event.data.get("customer_email", "customer@example.com")
    customer_message = ctx.event.data.get("message", "I need help with my order")
    order_id = ctx.event.data.get("order_id")

    # Build context for the agent
    context_info = f"Customer: {customer_email}\n"
    if order_id:
        context_info += f"Order ID: {order_id}\n"

    # Execute support agent
    result = await flowforge.step.agent(
        "support-agent",
        task=f"{context_info}\nCustomer Message: {customer_message}\n\nPlease help the customer resolve their issue.",
        model="claude-sonnet-4-6",
        system=(
            "You are a friendly and helpful customer support agent. Your goals are:\n"
            "1. Understand the customer's issue clearly\n"
            "2. Use available tools to find information and resolve issues\n"
            "3. Be empathetic and professional\n"
            "4. For refunds, explain the policy and process the refund if warranted\n"
            "5. Escalate to human agent if the issue is too complex or emotionally charged\n"
            "6. Always provide clear next steps\n\n"
            "Remember: Refunds require manager approval. The approval process may take a few minutes."
        ),
        tools=[
            search_knowledge_base,
            get_order_details,
            check_inventory,
            process_refund,
            escalate_to_human,
        ],
        max_iterations=15,
        max_tool_calls=30,
        temperature=0.7,
    )

    return {
        "customer_email": customer_email,
        "response": result.output,
        "status": result.status,
        "resolution_metrics": {
            "iterations": result.iterations,
            "tool_calls": result.tool_calls_count,
            "tokens_used": result.tokens_used,
        },
        "actions_taken": [
            {
                "tool": tc["tool"],
                "status": tc.get("status", "unknown"),
            }
            for tc in result.tool_calls
        ],
    }


# Simpler FAQ bot example
@flowforge.function(
    id="faq-bot",
    name="FAQ Bot",
    trigger=flowforge.trigger.event("support/faq"),
)
async def faq_bot(ctx: Context) -> dict:
    """
    Simple FAQ bot that only searches knowledge base.

    Useful for quick questions that don't require order lookup or other actions.
    """
    question = ctx.event.data.get("question", "")

    result = await flowforge.step.agent(
        "faq-search",
        task=f"Answer this question using the knowledge base: {question}",
        model="gpt-5-mini",
        system="You are a helpful FAQ bot. Search the knowledge base and provide a clear, concise answer.",
        tools=[search_knowledge_base],
        max_iterations=5,
    )

    return {
        "question": question,
        "answer": result.output,
        "source": "knowledge_base",
    }


if __name__ == "__main__":
    # Test the support agent locally
    import asyncio

    async def test_support_agent():
        """Test the customer support agent."""
        event = flowforge.Event(
            name="support/request",
            data={
                "customer_email": "jane@example.com",
                "message": "I ordered a product 2 weeks ago but it still hasn't arrived. Order ID: ORD-12345",
                "order_id": "ORD-12345"
            },
        )
        ctx = Context(event=event, run_id="test-support-123")

        try:
            result = await customer_support_agent(ctx)
            print("Support Agent Response:")
            print(f"Customer: {result['customer_email']}")
            print(f"\nResponse:\n{result['response']}")
            print(f"\nMetrics: {result['resolution_metrics']}")
            print(f"\nActions Taken: {result['actions_taken']}")
        except flowforge.StepCompleted as e:
            print(f"Step completed (expected in test): {e.step_id}")

    asyncio.run(test_support_agent())
