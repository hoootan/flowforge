#!/usr/bin/env python3
"""Register the Social Creator as an inline/serverless function.

This registers the function directly with FlowForge server,
enabling token-by-token streaming in the UI.

Usage:
    python examples/social_creator/register_inline.py
"""

import httpx
import asyncio

# FlowForge API configuration
FLOWFORGE_API = "http://localhost:8000/api/v1"

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
5. Present the posts to the user (they will be posted after approval)

## Important

- Always adapt content for each platform's unique style and limitations
- The posting tools require user approval before executing
- If unsure about the user's intent, provide your best interpretation
- Be creative but stay authentic
- After creating content, summarize what you created for the user"""


async def register_function():
    """Register the social-creator function as inline/serverless."""

    async with httpx.AsyncClient() as client:
        # Create the serverless function with correct schema
        payload = {
            "id": "create-social-post",
            "name": "Social Creator",
            "trigger": {
                "type": "event",
                "value": "social/create-post",
            },
            "system_prompt": SOCIAL_CREATOR_SYSTEM_PROMPT,
            "tools": [
                "web_search",
                "generate_image",
                "post_to_twitter",
                "post_to_linkedin",
                "post_to_instagram",
            ],
            "agent_config": {
                "model": "claude-sonnet-4-20250514",
                "max_iterations": 30,
                "max_tool_calls": 50,
            },
            "config": {
                "retries": 3,
                "timeout": "30m",
            },
        }

        try:
            response = await client.post(
                f"{FLOWFORGE_API}/functions/serverless",
                json=payload,
                timeout=30.0,
            )

            if response.status_code == 201:
                data = response.json()
                print("Function registered successfully!")
                print(f"  ID: {data['id']}")
                print(f"  Function ID: {data['function_id']}")
                print(f"  Is Inline: {data['is_inline']}")
                print(f"  Trigger: {data['trigger_type']}:{data['trigger_value']}")
            elif response.status_code == 409:
                print("Function already exists. Updating...")
                # Delete and recreate
                await client.delete(f"{FLOWFORGE_API}/functions/create-social-post")
                response = await client.post(
                    f"{FLOWFORGE_API}/functions/serverless",
                    json=payload,
                    timeout=30.0,
                )
                if response.status_code == 201:
                    data = response.json()
                    print("Function updated successfully!")
                    print(f"  ID: {data['id']}")
                    print(f"  Is Inline: {data['is_inline']}")
                else:
                    print(f"Failed to update: {response.status_code}")
                    print(response.text)
            else:
                print(f"Failed to register: {response.status_code}")
                print(response.text)

        except httpx.ConnectError:
            print("Error: Cannot connect to FlowForge server.")
            print(f"Make sure the server is running at {FLOWFORGE_API}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Registering Social Creator as Inline Function")
    print("=" * 60)
    asyncio.run(register_function())
