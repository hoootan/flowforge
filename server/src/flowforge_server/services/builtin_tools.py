"""Built-in tools that ship with FlowForge.

These tools are automatically seeded into the database on startup.
Users can reference them by name in their inline functions.
"""

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class BuiltinToolDefinition:
    """Definition of a built-in tool."""
    name: str
    description: str
    parameters: dict[str, Any]
    requires_approval: bool = False
    approval_timeout: str | None = None


# =============================================================================
# BUILT-IN TOOL DEFINITIONS
# =============================================================================

BUILTIN_TOOLS: list[BuiltinToolDefinition] = [
    # Research Tools
    BuiltinToolDefinition(
        name="web_search",
        description="Search the web for current information, news, trends, or facts. Use this to research topics before creating content or answering questions that need up-to-date information.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    ),

    # Content Generation Tools
    BuiltinToolDefinition(
        name="generate_image",
        description="Generate an image using AI based on a text description. Creates high-quality visuals for social media posts, presentations, or other content.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the image to generate",
                },
                "style": {
                    "type": "string",
                    "description": "Style of the image (e.g., 'professional', 'artistic', 'minimalist')",
                    "default": "professional",
                },
            },
            "required": ["prompt"],
        },
    ),

    # User Interaction Tools
    BuiltinToolDefinition(
        name="ask_user",
        description="Ask the user a question and wait for their response. Use this when you need clarification, preferences, or additional information from the user to proceed. The user can provide a text response.",
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user",
                },
                "context": {
                    "type": "string",
                    "description": "Optional context or explanation for why you're asking",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of suggested options for the user to choose from",
                },
            },
            "required": ["question"],
        },
        requires_approval=True,
        approval_timeout="24h",  # Give users more time to respond to questions
    ),
]


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

async def execute_web_search(query: str, num_results: int = 10, **kwargs) -> dict[str, Any]:
    """Execute web search using Tavily API if available, otherwise simulate."""
    api_key = os.environ.get("TAVILY_API_KEY")

    if api_key:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": num_results,
                    "include_answer": True,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "query": query,
                "answer": data.get("answer", ""),
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                    }
                    for r in data.get("results", [])
                ],
                "simulated": False,
            }
    else:
        # Simulated response
        return {
            "query": query,
            "answer": f"Here are the key findings about '{query}': This topic is trending with significant interest. Recent developments show growing engagement. Key statistics indicate strong market potential. Experts recommend focusing on authenticity and value.",
            "results": [
                {"title": "Industry Report 2024", "url": "https://example.com/report", "content": "Sample result content."},
                {"title": "Market Analysis", "url": "https://example.com/analysis", "content": "Sample analysis content."},
            ],
            "simulated": True,
        }


async def execute_generate_image(prompt: str, style: str = "professional", **kwargs) -> dict[str, Any]:
    """Execute image generation using Google Gemini (Nano Banana) if available, otherwise return placeholder."""
    api_key = os.environ.get("GOOGLE_API_KEY")

    if api_key:
        # Real implementation using Google Gemini
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={api_key}",
                json={
                    "instances": [{"prompt": f"{prompt}, {style} style"}],
                    "parameters": {"sampleCount": 1},
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            # Extract image URL from response
            image_data = data.get("predictions", [{}])[0]
            image_url = image_data.get("bytesBase64Encoded")

            if image_url:
                return {
                    "prompt": prompt,
                    "style": style,
                    "url": f"data:image/png;base64,{image_url}",
                    "simulated": False,
                }

    # Fallback to placeholder
    safe_prompt = prompt[:20].replace(" ", "+").replace("'", "").replace('"', "")
    return {
        "prompt": prompt,
        "style": style,
        "url": f"https://placehold.co/1200x630/1a1a2e/eaeaea?text={safe_prompt}",
        "simulated": True,
        "message": "Using placeholder image. Set GOOGLE_API_KEY for real image generation.",
    }


async def execute_ask_user(question: str, context: str | None = None, options: list[str] | None = None, **kwargs) -> dict[str, Any]:
    """
    Execute ask_user tool.

    This tool requires approval. The user's response comes through the approval
    modified_arguments field, which gets passed here as kwargs.
    """
    # The user's response is passed through the approval system
    # When approved, the modified_arguments (if any) are merged into kwargs
    user_response = kwargs.get("user_response") or kwargs.get("response")

    return {
        "question": question,
        "context": context,
        "options": options,
        "user_response": user_response,
        "answered": user_response is not None,
    }


# =============================================================================
# TOOL REGISTRY
# =============================================================================

TOOL_EXECUTORS: dict[str, callable] = {
    "web_search": execute_web_search,
    "generate_image": execute_generate_image,
    "ask_user": execute_ask_user,
}


async def execute_builtin_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a built-in tool by name with the given arguments."""
    executor = TOOL_EXECUTORS.get(name)
    if not executor:
        raise ValueError(f"Unknown built-in tool: {name}")
    return await executor(**arguments)


def get_builtin_tool_definitions() -> list[BuiltinToolDefinition]:
    """Get all built-in tool definitions."""
    return BUILTIN_TOOLS


def get_builtin_tool_names() -> list[str]:
    """Get names of all built-in tools."""
    return list(TOOL_EXECUTORS.keys())
