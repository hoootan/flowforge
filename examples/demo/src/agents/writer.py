"""Content writer agent for FlowForge demo."""

from flowforge import step
from tools import save_notes


async def run_writer_agent(topic: str, research_notes: str) -> dict:
    """
    Content writer agent that takes research and produces content.

    Args:
        topic: The topic to write about.
        research_notes: Notes from research phase.

    Returns:
        Dictionary with generated content and metadata.
    """
    result = await step.agent(
        "writer",
        task=f"""Write a compelling article about: {topic}

Use these research notes as your source:
{research_notes}

Create a well-structured article with:
- Engaging headline
- Clear introduction
- Main points with supporting details
- Actionable conclusion

Save your final article using the save_notes tool.""",
        model="claude-sonnet-4-6",
        system="""You are an expert content writer. You write clear, engaging,
and well-researched articles. Your writing is accessible yet authoritative.
Always cite sources when available.""",
        tools=[save_notes],
        max_iterations=5,
    )

    return {
        "content": result.output,
        "status": result.status,
        "iterations": result.iterations,
    }
