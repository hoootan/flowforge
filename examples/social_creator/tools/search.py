"""Web search tool using Perplexity API."""

import os
from typing import Any

import httpx

from flowforge import tool


PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


@tool(
    name="web_search",
    description="Search the web for current information, news, trends, or facts. Use this to research topics before creating social media posts.",
)
async def web_search(query: str, num_results: int = 5) -> dict[str, Any]:
    """
    Search the web for information using Perplexity API.

    Args:
        query: The search query to find information about.
        num_results: Maximum number of results to return (default: 5).

    Returns:
        Dict containing search results with answer and citations.
    """
    if not PERPLEXITY_API_KEY:
        # Return simulated results if no API key
        return {
            "query": query,
            "answer": f"[Simulated search result for: {query}] Based on recent information, here are the key points about this topic. This is placeholder content - set PERPLEXITY_API_KEY for real results.",
            "citations": [
                {"title": "Example Source 1", "url": "https://example.com/1"},
                {"title": "Example Source 2", "url": "https://example.com/2"},
            ],
            "simulated": True,
        }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                PERPLEXITY_API_URL,
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a research assistant. Provide concise, factual information based on current web sources. Focus on key facts, statistics, and recent developments.",
                        },
                        {
                            "role": "user",
                            "content": query,
                        },
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.2,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "query": query,
                "answer": data["choices"][0]["message"]["content"],
                "citations": data.get("citations", []),
                "model": data.get("model"),
                "simulated": False,
            }

        except httpx.HTTPStatusError as e:
            return {
                "query": query,
                "error": f"Search failed: {e.response.status_code}",
                "answer": None,
                "citations": [],
            }
        except Exception as e:
            return {
                "query": query,
                "error": f"Search failed: {str(e)}",
                "answer": None,
                "citations": [],
            }
