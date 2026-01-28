"""Tools for FlowForge demo agents."""

from tools.search import (
    search_web,
    fetch_article,
    search_knowledge_base,
)
from tools.database import (
    get_customer,
    get_customer_orders,
    get_order,
    create_ticket,
    update_ticket_status,
    save_notes,
)
from tools.email import (
    send_email,
    draft_email,
    process_refund,
    escalate_to_human,
)

__all__ = [
    # Search tools
    "search_web",
    "fetch_article",
    "search_knowledge_base",
    # Database tools
    "get_customer",
    "get_customer_orders",
    "get_order",
    "create_ticket",
    "update_ticket_status",
    "save_notes",
    # Email tools
    "send_email",
    "draft_email",
    "process_refund",
    "escalate_to_human",
]
