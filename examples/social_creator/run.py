#!/usr/bin/env python3
"""Run the Social Creator workflow as a standalone worker.

Usage:
    cd flowforge/examples
    python -m social_creator.run

    OR from flowforge root:
    PYTHONPATH=packages/flowforge-sdk/src python examples/social_creator/run.py
"""

import sys
import os
from typing import Any

# Ensure the SDK is importable
sdk_path = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "packages", "flowforge-sdk", "src"
)
sys.path.insert(0, os.path.abspath(sdk_path))

from flowforge import FlowForge, Context, step, tool

# ============================================================================
# PROMPTS
# ============================================================================

SOCIAL_CREATOR_SYSTEM_PROMPT = """You are a social media content strategist and copywriter. Your role is to help users create engaging, platform-specific social media posts.

## Your Capabilities

1. **Research**: Use web_search to find current information, trends, statistics, and facts to make content more credible and timely.

2. **Image Generation**: Use generate_image to create visuals for posts when appropriate.

3. **Content Creation**: Create tailored content for each platform:
   - **Twitter/X**: Concise, punchy (max 280 chars), use hooks, hashtags sparingly
   - **LinkedIn**: Professional tone, longer form (up to 3000 chars), use line breaks for readability
   - **Instagram**: Visual-first, engaging caption (up to 2200 chars), use emojis and hashtags

4. **Review & Post**: Request user approval using the posting tools, which require approval before executing.

## Content Guidelines

- Write in a conversational, authentic tone
- Avoid generic, corporate-speak
- Include specific details and examples
- Use formatting (line breaks, emojis) appropriately per platform
- Add relevant hashtags where appropriate

## Workflow

1. Understand the user's goal and target audience
2. Research if needed (for facts, trends, or inspiration)
3. Generate an image if the content would benefit from visuals
4. Create platform-specific versions of the content
5. Post to platforms (user will approve each one)

## Important

- Always adapt content for each platform's unique style and limitations
- The posting tools require user approval before executing
- If unsure about the user's intent, provide your best interpretation
- Be creative but stay authentic"""


# ============================================================================
# TOOLS
# ============================================================================

@tool(
    name="web_search",
    description="Search the web for current information, news, trends, or facts. Use this to research topics before creating social media posts.",
)
async def web_search(query: str) -> dict[str, Any]:
    """Search the web for information (simulated)."""
    return {
        "query": query,
        "answer": f"Here are the key findings about '{query}': This topic is trending with significant interest. Recent developments show growing engagement. Key statistics indicate strong market potential. Experts recommend focusing on authenticity and value.",
        "citations": [
            {"title": "Industry Report 2024", "url": "https://example.com/report"},
            {"title": "Market Analysis", "url": "https://example.com/analysis"},
        ],
        "simulated": True,
    }


@tool(
    name="generate_image",
    description="Generate an image for social media posts using AI. Creates high-quality visuals based on text descriptions.",
)
async def generate_image(prompt: str, style: str = "professional") -> dict[str, Any]:
    """Generate an image (simulated with placeholder)."""
    return {
        "prompt": prompt,
        "style": style,
        "url": f"https://placehold.co/1200x630/1a1a2e/eaeaea?text={prompt[:20].replace(' ', '+')}",
        "simulated": True,
        "message": "Using placeholder image. Set GOOGLE_API_KEY for real Nano Banana generation.",
    }


@tool(
    name="post_to_twitter",
    description="Post content to Twitter/X. Requires user approval before posting.",
    requires_approval=True,
    approval_timeout="1h",
)
async def post_to_twitter(content: str, image_url: str | None = None) -> dict[str, Any]:
    """Post to Twitter (simulated)."""
    if len(content) > 280:
        return {"status": "error", "error": f"Content exceeds 280 chars ({len(content)})"}

    return {
        "status": "posted",
        "platform": "twitter",
        "content": content,
        "image_url": image_url,
        "post_url": "https://twitter.com/user/status/simulated123",
        "simulated": True,
    }


@tool(
    name="post_to_linkedin",
    description="Post content to LinkedIn. Requires user approval before posting.",
    requires_approval=True,
    approval_timeout="1h",
)
async def post_to_linkedin(content: str, image_url: str | None = None) -> dict[str, Any]:
    """Post to LinkedIn (simulated)."""
    if len(content) > 3000:
        return {"status": "error", "error": f"Content exceeds 3000 chars ({len(content)})"}

    return {
        "status": "posted",
        "platform": "linkedin",
        "content": content,
        "image_url": image_url,
        "post_url": "https://linkedin.com/feed/update/simulated456",
        "simulated": True,
    }


@tool(
    name="post_to_instagram",
    description="Post content to Instagram. Requires an image and user approval before posting.",
    requires_approval=True,
    approval_timeout="1h",
)
async def post_to_instagram(content: str, image_url: str) -> dict[str, Any]:
    """Post to Instagram (simulated)."""
    if len(content) > 2200:
        return {"status": "error", "error": f"Caption exceeds 2200 chars ({len(content)})"}

    if not image_url:
        return {"status": "error", "error": "Instagram requires an image"}

    return {
        "status": "posted",
        "platform": "instagram",
        "content": content,
        "image_url": image_url,
        "post_url": "https://instagram.com/p/simulated789",
        "simulated": True,
    }


# ============================================================================
# WORKFLOW
# ============================================================================

# Initialize FlowForge client
flowforge = FlowForge(app_id="social-creator")


@flowforge.function(
    id="create-social-post",
    trigger=flowforge.trigger.event("social/create-post"),
    retries=3,
    timeout="30m",
)
async def create_social_post(ctx: Context) -> dict[str, Any]:
    """Main workflow for creating social media posts."""
    data = ctx.event.data
    prompt = data.get("prompt", "")

    if not prompt:
        return {"status": "error", "error": "No prompt provided"}

    # Run the social creator agent
    result = await step.agent(
        "social-creator-agent",
        task=prompt,
        model="claude-sonnet-4-6",
        system=SOCIAL_CREATOR_SYSTEM_PROMPT,
        tools=[
            web_search,
            generate_image,
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


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Social Creator Worker")
    print("=" * 60)
    print(f"Function: create-social-post")
    print(f"Trigger:  social/create-post")
    print(f"Port:     8081")
    print("=" * 60)

    flowforge.serve(
        functions=[create_social_post],
        host="0.0.0.0",
        port=8081,
    )
