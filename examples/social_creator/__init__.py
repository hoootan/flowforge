"""Social Creator - AI-powered social media post generation.

This example demonstrates:
- Agentic workflow with multiple tools
- Human-in-the-loop (HITL) approvals
- Web search integration (Perplexity)
- Image generation (Nano Banana/Gemini)
- Multi-platform social posting
"""

from .workflow import create_social_post, flowforge
from .prompts import SOCIAL_CREATOR_SYSTEM_PROMPT
from .tools import (
    web_search,
    generate_image,
    post_to_twitter,
    post_to_linkedin,
    post_to_instagram,
    request_content_review,
)

__all__ = [
    "create_social_post",
    "flowforge",
    "SOCIAL_CREATOR_SYSTEM_PROMPT",
    "web_search",
    "generate_image",
    "post_to_twitter",
    "post_to_linkedin",
    "post_to_instagram",
    "request_content_review",
]
