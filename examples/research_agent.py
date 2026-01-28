"""
Example: Research Agent

A simple research agent that searches for information on a topic
and compiles a comprehensive summary with citations.
"""

import flowforge
from flowforge import tool, Context
from typing import Literal


# Web search tool
@tool(
    name="web_search",
    description="Search the web for information on any topic",
)
async def web_search(query: str, num_results: int = 5) -> dict:
    """
    Search the web and return relevant results.

    Args:
        query: Search query
        num_results: Number of results to return (1-10)

    Returns:
        Search results with titles, snippets, and URLs
    """
    # Simulate web search API
    results = []
    for i in range(min(num_results, 5)):
        results.append({
            "title": f"Result {i+1}: {query}",
            "snippet": f"Comprehensive information about {query}. This article covers key aspects and recent developments...",
            "url": f"https://example.com/article{i+1}",
            "date": "2025-01-20",
        })

    return {
        "query": query,
        "results": results,
        "total_found": num_results,
    }


# Academic paper search
@tool(
    name="search_papers",
    description="Search academic papers and research publications",
)
async def search_academic_papers(query: str, year_from: int = 2020) -> dict:
    """
    Search academic databases for research papers.

    Args:
        query: Research topic or keywords
        year_from: Only include papers from this year onward

    Returns:
        Academic papers with titles, abstracts, and citations
    """
    # Simulate academic search
    return {
        "query": query,
        "papers": [
            {
                "title": f"Recent Advances in {query}",
                "authors": ["Dr. Smith, J.", "Dr. Johnson, A."],
                "year": 2024,
                "abstract": f"This paper presents novel approaches to {query}...",
                "citations": 45,
                "url": "https://papers.example.com/paper1",
            },
            {
                "title": f"A Comprehensive Survey of {query}",
                "authors": ["Dr. Lee, K.", "Dr. Wang, L."],
                "year": 2023,
                "abstract": f"We survey the current state of research in {query}...",
                "citations": 128,
                "url": "https://papers.example.com/paper2",
            },
        ],
        "count": 2,
    }


# Wikipedia lookup
@tool(
    name="get_wikipedia",
    description="Get Wikipedia article summary for a topic",
)
async def get_wikipedia_summary(topic: str) -> dict:
    """
    Retrieve Wikipedia article summary.

    Args:
        topic: Topic to look up on Wikipedia

    Returns:
        Wikipedia summary and key facts
    """
    return {
        "topic": topic,
        "summary": f"{topic} is an important subject in modern science. It has applications in various fields and has been studied extensively since the early 2000s.",
        "url": f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}",
        "categories": ["Science", "Technology", "Research"],
    }


# Save research notes
@tool(
    name="save_notes",
    description="Save important findings and notes from research",
)
async def save_research_notes(topic: str, notes: str, category: Literal["finding", "citation", "question"] = "finding") -> dict:
    """
    Save research notes for later reference.

    Args:
        topic: Research topic
        notes: Content to save
        category: Type of note (finding, citation, or question)

    Returns:
        Confirmation of saved note
    """
    return {
        "status": "saved",
        "topic": topic,
        "category": category,
        "note_id": f"note_{category}_123",
        "timestamp": "2025-01-23T10:00:00Z",
    }


# Main research agent
@flowforge.function(
    id="research-agent",
    name="Research Agent",
    trigger=flowforge.trigger.event("research/topic"),
)
async def research_agent(ctx: Context) -> dict:
    """
    Autonomous research agent that investigates a topic and compiles findings.

    This agent will:
    1. Search the web for general information
    2. Look up academic papers for scholarly perspective
    3. Check Wikipedia for background
    4. Compile a comprehensive summary with citations

    Event payload:
        - topic: Research topic (required)
        - depth: Research depth ("quick", "standard", "comprehensive")
        - include_papers: Whether to search academic papers (default: true)
    """
    topic = ctx.event.data.get("topic", "Artificial Intelligence")
    depth = ctx.event.data.get("depth", "standard")
    include_papers = ctx.event.data.get("include_papers", True)

    # Adjust parameters based on depth
    depth_config = {
        "quick": {"iterations": 5, "sources": 2},
        "standard": {"iterations": 10, "sources": 3},
        "comprehensive": {"iterations": 20, "sources": 5},
    }
    config = depth_config.get(depth, depth_config["standard"])

    # Build task description
    task = f"Research the topic: {topic}\n\n"
    task += "Please:\n"
    task += "1. Search the web for recent information and developments\n"
    task += "2. Get Wikipedia summary for background context\n"

    if include_papers:
        task += "3. Search academic papers for scholarly perspective\n"
        task += "4. Compile a comprehensive summary with key findings\n"
        task += "5. Include proper citations for all sources\n"
    else:
        task += "3. Compile a comprehensive summary with key findings\n"
        task += "4. Include proper citations for all sources\n"

    # Select tools based on configuration
    tools = [web_search, get_wikipedia_summary, save_research_notes]
    if include_papers:
        tools.insert(1, search_academic_papers)

    # Execute research agent
    result = await flowforge.step.agent(
        "research-topic",
        task=task,
        model="claude-sonnet-4-20250514",
        system=(
            "You are a research assistant helping to compile comprehensive, well-sourced information on topics. "
            "Your research should be:\n"
            "- Thorough: Cover multiple perspectives and sources\n"
            "- Accurate: Only include information from your searches, don't make assumptions\n"
            "- Well-cited: Include source URLs for all claims\n"
            "- Organized: Present information in a clear, logical structure\n"
            "- Objective: Present facts without bias\n\n"
            "Use save_notes to track important findings as you research."
        ),
        tools=tools,
        max_iterations=config["iterations"],
        max_tool_calls=config["iterations"] * 3,
        temperature=0.5,  # Lower temperature for more factual research
    )

    return {
        "topic": topic,
        "depth": depth,
        "research_summary": result.output,
        "metadata": {
            "status": result.status,
            "iterations": result.iterations,
            "sources_checked": result.tool_calls_count,
            "tokens_used": result.tokens_used,
        },
        "search_history": [
            {
                "iteration": tc["iteration"],
                "tool": tc["tool"],
                "status": tc.get("status", "unknown"),
            }
            for tc in result.tool_calls
        ],
    }


# Comparative research agent
@flowforge.function(
    id="comparative-research",
    name="Comparative Research Agent",
    trigger=flowforge.trigger.event("research/compare"),
)
async def comparative_research(ctx: Context) -> dict:
    """
    Compare multiple topics or approaches side-by-side.

    Event payload:
        - topics: List of topics to compare (2-4 topics)
        - comparison_criteria: What aspects to compare
    """
    topics = ctx.event.data.get("topics", ["Topic A", "Topic B"])
    criteria = ctx.event.data.get("comparison_criteria", "general comparison")

    topics_str = " vs ".join(topics)

    result = await flowforge.step.agent(
        "compare-topics",
        task=(
            f"Research and compare: {topics_str}\n\n"
            f"Comparison criteria: {criteria}\n\n"
            f"For each topic:\n"
            f"1. Search for current information\n"
            f"2. Identify key characteristics\n"
            f"3. Note strengths and weaknesses\n"
            f"4. Provide a side-by-side comparison table\n"
            f"5. Conclude with recommendations based on different use cases"
        ),
        model="gpt-4o",
        system="You are a research analyst specializing in comparative analysis. Provide balanced, objective comparisons.",
        tools=[web_search, search_academic_papers, get_wikipedia_summary],
        max_iterations=15,
    )

    return {
        "topics": topics,
        "criteria": criteria,
        "comparison": result.output,
        "stats": {
            "iterations": result.iterations,
            "tool_calls": result.tool_calls_count,
        },
    }


if __name__ == "__main__":
    # Test the research agent locally
    import asyncio

    async def test_research():
        """Test the research agent."""
        event = flowforge.Event(
            name="research/topic",
            data={
                "topic": "Quantum Computing Applications",
                "depth": "standard",
                "include_papers": True,
            },
        )
        ctx = Context(event=event, run_id="test-research-123")

        try:
            result = await research_agent(ctx)
            print("Research Agent Results:")
            print(f"Topic: {result['topic']}")
            print(f"Depth: {result['depth']}")
            print(f"\nSummary:\n{result['research_summary']}")
            print(f"\nMetadata: {result['metadata']}")
        except flowforge.StepCompleted as e:
            print(f"Step completed (expected in test): {e.step_id}")

    async def test_comparative():
        """Test comparative research."""
        event = flowforge.Event(
            name="research/compare",
            data={
                "topics": ["Python", "JavaScript", "Go"],
                "comparison_criteria": "backend development performance and ecosystem",
            },
        )
        ctx = Context(event=event, run_id="test-compare-123")

        try:
            result = await comparative_research(ctx)
            print("\nComparative Research Results:")
            print(f"Topics: {result['topics']}")
            print(f"\nComparison:\n{result['comparison']}")
        except flowforge.StepCompleted as e:
            print(f"Step completed (expected in test): {e.step_id}")

    # Run tests
    asyncio.run(test_research())
    print("\n" + "="*80 + "\n")
    asyncio.run(test_comparative())
