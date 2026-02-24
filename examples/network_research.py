"""
Example: Research Network with LLM Router

This example demonstrates using an LLM-based router for dynamic agent selection.
The network includes:
- Researcher: Gathers information from multiple sources
- Analyst: Analyzes and synthesizes findings
- Writer: Creates polished final output

The LLM router intelligently decides which agent should handle each step.
"""

import flowforge
from flowforge import tool, agent_def, network
from flowforge.router import llm


# Define tools
@tool(name="web_search", description="Search the web for information")
async def web_search(query: str, num_results: int = 5) -> dict:
    """
    Search the web for information.

    Args:
        query: Search query string
        num_results: Number of results to return

    Returns:
        Search results with URLs and snippets
    """
    # Simulated web search
    return {
        "results": [
            {
                "title": f"Result for: {query}",
                "url": "https://example.com/result1",
                "snippet": "Relevant information about the query...",
                "date": "2026-01-20"
            },
            {
                "title": f"More about {query}",
                "url": "https://example.com/result2",
                "snippet": "Additional details and context...",
                "date": "2026-01-18"
            }
        ],
        "total": num_results
    }


@tool(name="fetch_article", description="Fetch full article content")
async def fetch_article(url: str) -> dict:
    """
    Fetch the full content of an article.

    Args:
        url: Article URL to fetch

    Returns:
        Full article content
    """
    # Simulated article fetch
    return {
        "url": url,
        "title": "Article Title",
        "content": "Full article content with detailed information...",
        "author": "Jane Doe",
        "published": "2026-01-15"
    }


@tool(name="analyze_data", description="Analyze data for patterns and insights")
async def analyze_data(data: dict, focus: str = "trends") -> dict:
    """
    Analyze data for patterns and insights.

    Args:
        data: Data to analyze
        focus: Analysis focus (trends, patterns, correlations)

    Returns:
        Analysis results with insights
    """
    # Simulated data analysis
    return {
        "insights": [
            "Key trend: Growing adoption over past 6 months",
            "Pattern identified: Usage peaks on weekdays",
            "Correlation: User satisfaction correlates with feature X"
        ],
        "confidence": 0.87,
        "focus": focus
    }


@tool(name="save_findings", description="Save research findings to state")
async def save_findings(findings: dict) -> dict:
    """
    Save research findings to network state.

    Args:
        findings: Findings to save

    Returns:
        Confirmation
    """
    return {
        "saved": True,
        "findings_count": len(findings.get("items", [])),
        "timestamp": "2026-01-23T12:00:00Z"
    }


# Define agents
researcher = agent_def(
    name="researcher",
    system="""You are a research specialist. Your job is to gather comprehensive information.
Use web_search to find relevant sources, then fetch_article to get detailed content.
Save your findings to state so other agents can use them.
When you have enough information, indicate that research is complete.""",
    tools=[web_search, fetch_article, save_findings],
    model="claude-sonnet-4-6",
)

analyst = agent_def(
    name="analyst",
    system="""You are an analytical expert. Review the research findings from state.
Use analyze_data to identify patterns, trends, and key insights.
Synthesize the information into clear, actionable insights.
Store your analysis results in state for the writer.""",
    tools=[analyze_data, save_findings],
    model="claude-sonnet-4-6",
)

writer = agent_def(
    name="writer",
    system="""You are a professional writer. Take the research and analysis from state.
Create a polished, well-structured final report or article.
Include an executive summary, key findings, and recommendations.
Set state.set('complete', True) when done.""",
    tools=[],
    model="gpt-5",
)


# Create network with LLM router
# The LLM router will intelligently decide which agent should handle each step
research_network = network(
    name="research",
    agents=[researcher, analyst, writer],
    router=llm(
        model="gpt-5-mini",
        prompt="""You are routing a research workflow. Based on the current state and progress:
- If initial research is needed, route to 'researcher'
- If data needs analysis, route to 'analyst'
- If a final report is needed, route to 'writer'
- If work is complete, respond 'DONE'

Available agents: {agents}
Current state: {state}
Last result: {last_result}

Respond with ONLY the agent name or DONE.""",
        temperature=0.3,
    ),
    default_model="claude-sonnet-4-6",
)


# FlowForge function using the network
@flowforge.function(
    name="research-task",
    trigger=flowforge.trigger.event("research/request"),
)
async def handle_research(ctx, step) -> dict:
    """
    Handle a research request through the multi-agent network.

    Args:
        ctx: FlowForge context with event data
        step: Step manager for durable execution

    Returns:
        Research results
    """
    request_data = ctx.event.data
    topic = request_data.get("topic", "")
    depth = request_data.get("depth", "standard")  # standard, deep, quick

    # Execute the network with LLM-based routing
    result = await step.network(
        "research-network",
        network=research_network,
        input=f"Research topic: {topic}. Depth: {depth}",
        initial_state={
            "topic": topic,
            "depth": depth,
            "findings": [],
            "complete": False,
        },
        max_iterations=10,
    )

    # Log results
    print(f"Research network completed:")
    print(f"  Status: {result.status}")
    print(f"  Iterations: {result.iterations}")
    print(f"  Agents used: {[call['agent'] for call in result.agent_calls]}")
    print(f"  Total tokens: {result.total_tokens}")
    print(f"  Cost: ${result.total_cost_usd:.4f}")

    return {
        "topic": topic,
        "status": result.status,
        "report": result.output,
        "iterations": result.iterations,
        "agent_sequence": [call["agent"] for call in result.agent_calls],
        "final_state": result.state,
        "metrics": {
            "tokens": result.total_tokens,
            "cost_usd": result.total_cost_usd,
        }
    }
