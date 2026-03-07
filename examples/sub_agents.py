"""
Example: Sub-Agent Delegation

This example demonstrates the sub-agent feature where a "manager" agent
dynamically delegates tasks to specialist sub-agents. Sub-agents are
exposed as tools — when the parent agent calls them, a nested agent loop
runs and returns the result.

Key concepts:
  - `agent_def()` defines a specialist agent with its own system prompt and tools
  - `sub_agent()` wraps an AgentDefinition as a Tool the parent can call
  - The parent agent decides at runtime which sub-agents to invoke
  - Each sub-agent has independent iteration/tool call limits
  - Nesting is capped at 3 levels by default
"""

import flowforge
from flowforge import agent_def, sub_agent, step, tool, trigger


# ── Tools for the researcher sub-agent ──────────────────────────────────


@tool(
    name="web_search",
    description="Search the web for information",
)
async def web_search(query: str) -> dict:
    """
    Simulate a web search.

    Args:
        query: The search query
    """
    return {
        "results": [
            {"title": f"Result for: {query}", "url": "https://example.com/1"},
            {"title": f"Deep dive: {query}", "url": "https://example.com/2"},
        ],
        "summary": f"Found 2 results for '{query}'",
    }


@tool(
    name="read_url",
    description="Read the contents of a URL",
)
async def read_url(url: str) -> dict:
    """
    Simulate reading a web page.

    Args:
        url: The URL to read
    """
    return {"content": f"Contents of {url}: Lorem ipsum dolor sit amet..."}


# ── Tools for the writer sub-agent ──────────────────────────────────────


@tool(
    name="format_markdown",
    description="Format text as clean Markdown with headings and bullet points",
)
async def format_markdown(text: str, title: str = "Document") -> dict:
    """
    Format text as Markdown.

    Args:
        text: Raw text to format
        title: Document title
    """
    return {"markdown": f"# {title}\n\n{text}"}


# ── Tools for the manager ──────────────────────────────────────────────


@tool(
    name="send_email",
    description="Send an email with a subject and body",
)
async def send_email(to: str, subject: str, body: str) -> dict:
    """
    Simulate sending an email.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
    """
    return {"status": "sent", "to": to, "subject": subject}


# ── Define specialist agents ───────────────────────────────────────────

researcher = agent_def(
    name="researcher",
    system=(
        "You are a research specialist. Use web_search and read_url to "
        "gather information on the topic. Synthesize your findings into "
        "a clear summary."
    ),
    tools=[web_search, read_url],
    model="claude-sonnet-4-6",
)

writer = agent_def(
    name="writer",
    system=(
        "You are a technical writer. Take research findings and produce "
        "a well-structured document using format_markdown."
    ),
    tools=[format_markdown],
    model="claude-sonnet-4-6",
)


# ── Wrap as sub-agent tools ────────────────────────────────────────────

research_tool = sub_agent(
    researcher,
    description="Delegate research tasks to a specialist who can search the web.",
    max_iterations=10,
    max_tool_calls=20,
)

writing_tool = sub_agent(
    writer,
    description="Delegate writing tasks to a specialist who produces formatted documents.",
    max_iterations=5,
    max_tool_calls=10,
)


# ── Manager function ──────────────────────────────────────────────────


@flowforge.function(
    id="project-manager",
    trigger=trigger.event("project/plan"),
)
async def project_manager(ctx):
    """
    A manager agent that breaks work into research and writing tasks,
    delegating each to the appropriate specialist sub-agent.
    """
    result = await step.agent(
        "manager",
        task=ctx.event.data.get("goal", "Write a report"),
        model="claude-opus-4-6",
        system=(
            "You are a project manager. Break the user's goal into "
            "research and writing tasks. Use the 'researcher' tool to "
            "gather information and the 'writer' tool to produce the "
            "final document. Use 'send_email' to deliver the result. "
            "Coordinate the work efficiently."
        ),
        tools=[research_tool, writing_tool, send_email],
        max_iterations=15,
        max_tool_calls=30,
    )
    return {"output": result.output, "iterations": result.iterations}
