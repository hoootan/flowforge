"""Search tools for FlowForge agents."""

from flowforge import tool


@tool(
    name="search_web",
    description="Search the web for information on a topic",
)
async def search_web(query: str, max_results: int = 5) -> dict:
    """
    Search the web and return relevant results.

    Args:
        query: The search query
        max_results: Maximum number of results to return

    Returns:
        Dictionary with search results
    """
    # Simulated search results for demo
    results = [
        {
            "title": f"Result about {query}",
            "url": f"https://example.com/article-{i}",
            "snippet": f"This article discusses {query} in detail...",
        }
        for i in range(min(max_results, 3))
    ]

    return {
        "query": query,
        "results": results,
        "total_found": len(results),
    }


@tool(
    name="fetch_article",
    description="Fetch the full content of an article from a URL",
)
async def fetch_article(url: str) -> dict:
    """
    Fetch article content from a URL.

    Args:
        url: The URL to fetch

    Returns:
        Dictionary with article content
    """
    # Simulated article content for demo
    return {
        "url": url,
        "title": "Sample Article Title",
        "content": """
        This is the full article content. In a real implementation,
        this would fetch and parse the actual web page content.

        The article discusses various topics related to the search query
        and provides detailed information that the agent can use to
        complete its task.
        """,
        "word_count": 150,
    }


@tool(
    name="search_knowledge_base",
    description="Search the internal knowledge base for support articles",
)
async def search_knowledge_base(query: str, category: str | None = None) -> dict:
    """
    Search internal knowledge base.

    Args:
        query: Search query
        category: Optional category filter (technical, billing, general)

    Returns:
        Matching knowledge base articles
    """
    # Simulated KB results
    articles = {
        "password": [
            {"id": "kb-001", "title": "How to Reset Your Password", "solution": "Go to Settings > Security > Reset Password"},
            {"id": "kb-002", "title": "Password Requirements", "solution": "Passwords must be 8+ characters with numbers"},
        ],
        "billing": [
            {"id": "kb-010", "title": "How to Request a Refund", "solution": "Contact support with order number"},
            {"id": "kb-011", "title": "Understanding Your Invoice", "solution": "Invoices are sent monthly on the 1st"},
        ],
        "default": [
            {"id": "kb-100", "title": "Getting Started Guide", "solution": "Welcome to our platform!"},
        ],
    }

    # Simple keyword matching for demo
    for keyword, results in articles.items():
        if keyword in query.lower():
            return {"query": query, "articles": results, "category": category}

    return {"query": query, "articles": articles["default"], "category": category}
