"""Social Creator Workflow - AI-powered social media post generation."""

import asyncio
from typing import Any

from flowforge import FlowForge, Context, step

from .prompts import SOCIAL_CREATOR_SYSTEM_PROMPT
from .tools import (
    web_search,
    generate_image,
    post_to_twitter,
    post_to_linkedin,
    post_to_instagram,
    request_content_review,
)


# Initialize FlowForge client
flowforge = FlowForge(app_id="social-creator")


@flowforge.function(
    id="create-social-post",
    trigger=flowforge.trigger.event("social/create-post"),
    retries=3,
    timeout="30m",
)
async def create_social_post(ctx: Context) -> dict[str, Any]:
    """
    Main workflow for creating social media posts.

    This workflow:
    1. Receives a user prompt
    2. Uses an AI agent with tools to research, generate content, and create images
    3. Requests user approval for each post
    4. Posts to approved platforms

    The agent has access to:
    - web_search: Research topics and find current information
    - generate_image: Create visuals for posts
    - request_content_review: Get user approval on content
    - post_to_twitter: Post to Twitter/X
    - post_to_linkedin: Post to LinkedIn
    - post_to_instagram: Post to Instagram
    """
    data = ctx.event.data
    prompt = data.get("prompt", "")

    if not prompt:
        return {
            "status": "error",
            "error": "No prompt provided",
        }

    # Run the social creator agent
    result = await step.agent(
        "social-creator-agent",
        task=prompt,
        model="claude-sonnet-4-20250514",  # Or "gpt-4o" for OpenAI
        system=SOCIAL_CREATOR_SYSTEM_PROMPT,
        tools=[
            web_search,
            generate_image,
            request_content_review,
            post_to_twitter,
            post_to_linkedin,
            post_to_instagram,
        ],
        max_iterations=30,
        max_tool_calls=50,
    )

    return {
        "status": result.status,
        "output": result.output,
        "tool_calls": result.tool_calls_count,
        "tokens_used": result.tokens_used,
    }


# Development server
if __name__ == "__main__":
    flowforge.serve(
        functions=[create_social_post],
        host="0.0.0.0",
        port=8080,
    )
