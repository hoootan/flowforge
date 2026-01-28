"""Database tools for FlowForge agents."""

from flowforge import tool


# Simulated database for demo
_CUSTOMERS = {
    "c_123": {
        "id": "c_123",
        "name": "John Doe",
        "email": "john@example.com",
        "tier": "premium",
        "created_at": "2023-01-15",
    },
    "c_456": {
        "id": "c_456",
        "name": "Jane Smith",
        "email": "jane@example.com",
        "tier": "basic",
        "created_at": "2024-03-20",
    },
}

_ORDERS = {
    "ord_001": {
        "id": "ord_001",
        "customer_id": "c_123",
        "total": 99.99,
        "status": "completed",
        "items": ["Product A", "Product B"],
        "created_at": "2024-06-15",
    },
    "ord_002": {
        "id": "ord_002",
        "customer_id": "c_456",
        "total": 49.99,
        "status": "pending",
        "items": ["Product C"],
        "created_at": "2024-07-01",
    },
}

_TICKETS = {}


@tool(
    name="get_customer",
    description="Get customer information by ID or email",
)
async def get_customer(customer_id: str | None = None, email: str | None = None) -> dict:
    """
    Retrieve customer information.

    Args:
        customer_id: Customer ID to look up
        email: Customer email to look up

    Returns:
        Customer information or error
    """
    if customer_id and customer_id in _CUSTOMERS:
        return {"found": True, "customer": _CUSTOMERS[customer_id]}

    if email:
        for cust in _CUSTOMERS.values():
            if cust["email"] == email:
                return {"found": True, "customer": cust}

    return {"found": False, "error": "Customer not found"}


@tool(
    name="get_customer_orders",
    description="Get all orders for a customer",
)
async def get_customer_orders(customer_id: str) -> dict:
    """
    Get orders for a customer.

    Args:
        customer_id: Customer ID

    Returns:
        List of customer orders
    """
    orders = [o for o in _ORDERS.values() if o["customer_id"] == customer_id]
    return {
        "customer_id": customer_id,
        "orders": orders,
        "total_orders": len(orders),
    }


@tool(
    name="get_order",
    description="Get order details by order ID",
)
async def get_order(order_id: str) -> dict:
    """
    Get order details.

    Args:
        order_id: Order ID

    Returns:
        Order details or error
    """
    if order_id in _ORDERS:
        return {"found": True, "order": _ORDERS[order_id]}
    return {"found": False, "error": "Order not found"}


@tool(
    name="create_ticket",
    description="Create a support ticket",
)
async def create_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
) -> dict:
    """
    Create a support ticket.

    Args:
        customer_id: Customer ID
        subject: Ticket subject
        description: Ticket description
        priority: Priority level (low, medium, high)

    Returns:
        Created ticket information
    """
    ticket_id = f"tkt_{len(_TICKETS) + 1:04d}"
    ticket = {
        "id": ticket_id,
        "customer_id": customer_id,
        "subject": subject,
        "description": description,
        "priority": priority,
        "status": "open",
    }
    _TICKETS[ticket_id] = ticket

    return {"created": True, "ticket": ticket}


@tool(
    name="update_ticket_status",
    description="Update the status of a support ticket",
)
async def update_ticket_status(ticket_id: str, status: str, resolution: str | None = None) -> dict:
    """
    Update ticket status.

    Args:
        ticket_id: Ticket ID
        status: New status (open, in_progress, resolved, closed)
        resolution: Resolution notes (required when closing)

    Returns:
        Updated ticket
    """
    if ticket_id not in _TICKETS:
        return {"success": False, "error": "Ticket not found"}

    _TICKETS[ticket_id]["status"] = status
    if resolution:
        _TICKETS[ticket_id]["resolution"] = resolution

    return {"success": True, "ticket": _TICKETS[ticket_id]}


@tool(
    name="save_notes",
    description="Save research notes or findings",
)
async def save_notes(title: str, content: str, tags: list[str] | None = None) -> dict:
    """
    Save notes or findings.

    Args:
        title: Note title
        content: Note content
        tags: Optional tags for organization

    Returns:
        Saved note information
    """
    note_id = f"note_{hash(title) % 10000:04d}"
    return {
        "saved": True,
        "note": {
            "id": note_id,
            "title": title,
            "content": content,
            "tags": tags or [],
        },
    }
