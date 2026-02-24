"""Research agent for gathering and analyzing information."""

import sys
sys.path.insert(0, "/Users/hootan/Developer/Personal/Random/flowforge-demo")

from flowforge import FlowForge, Context, step
from tools import search_web, fetch_article, save_notes

flowforge = FlowForge(app_id="research-agent")


@flowforge.function(
    id="research-topic",
    trigger=flowforge.trigger.event("research/request"),
    retries=3,
    timeout="30m",
)
async def research_topic(ctx: Context) -> dict:
    """
    Research a topic and compile findings.

    Triggered by: research/request
    Payload: {"topic": "AI trends in 2024", "depth": "detailed"}
    """
    topic = ctx.event.data.get("topic", "")
    depth = ctx.event.data.get("depth", "summary")

    ctx.log(f"Starting research on: {topic}")

    # Use agent to research the topic
    result = await step.agent(
        "research-agent",
        task=f"""Research the following topic and provide a comprehensive analysis:

Topic: {topic}

Instructions:
1. Search for relevant information using the search_web tool
2. For detailed research, fetch full articles using fetch_article
3. Analyze the information and identify key insights
4. Save your findings using save_notes
5. Provide a final summary with key takeaways

Depth level: {depth}
""",
        model="claude-sonnet-4-6",
        system="""You are an expert research assistant. Your job is to:
- Gather accurate, up-to-date information
- Analyze sources critically
- Synthesize findings into clear insights
- Always cite your sources
- Be thorough but concise""",
        tools=[search_web, fetch_article, save_notes],
        max_iterations=15,
        temperature=0.7,
    )

    ctx.log(f"Research completed with {result.iterations} iterations")

    return {
        "topic": topic,
        "status": result.status,
        "summary": result.output,
        "iterations": result.iterations,
        "tool_calls": result.tool_calls_count,
        "tokens_used": result.tokens_used,
    }


if __name__ == "__main__":
    flowforge.serve(
        functions=[research_topic],
        port=8081,
    )
