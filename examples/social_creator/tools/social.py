"""Social media posting tools (simulated for MVP)."""

import uuid
from datetime import datetime
from typing import Any

from flowforge import tool


# In-memory storage for simulated posts (for demo purposes)
_SIMULATED_POSTS: dict[str, dict[str, Any]] = {}


@tool(
    name="request_content_review",
    description="Request user review and approval of generated content before posting. Use this to let the user edit or approve the content.",
    requires_approval=True,
    approval_timeout="30m",
)
async def request_content_review(
    content: str,
    platform: str,
    content_type: str = "post",
) -> dict[str, Any]:
    """
    Request user review of generated content.

    Args:
        content: The generated content to review.
        platform: Target platform (twitter, linkedin, instagram).
        content_type: Type of content (post, caption, thread).

    Returns:
        Dict with review status and approved content.
    """
    return {
        "status": "approved",
        "content": content,
        "platform": platform,
        "content_type": content_type,
        "reviewed_at": datetime.utcnow().isoformat(),
    }


@tool(
    name="post_to_twitter",
    description="Post content to Twitter/X. Requires user approval before posting.",
    requires_approval=True,
    approval_timeout="1h",
)
async def post_to_twitter(
    content: str,
    image_url: str | None = None,
    thread: bool = False,
) -> dict[str, Any]:
    """
    Post content to Twitter/X (simulated).

    Args:
        content: The tweet content (max 280 characters).
        image_url: Optional URL of image to attach.
        thread: Whether this is part of a thread.

    Returns:
        Dict with post details and simulated post ID.
    """
    # Validate content length
    if len(content) > 280:
        return {
            "status": "error",
            "error": f"Content exceeds 280 characters ({len(content)} chars)",
            "platform": "twitter",
        }

    post_id = f"tweet_{uuid.uuid4().hex[:12]}"
    post_data = {
        "id": post_id,
        "platform": "twitter",
        "content": content,
        "image_url": image_url,
        "thread": thread,
        "posted_at": datetime.utcnow().isoformat(),
        "url": f"https://twitter.com/user/status/{post_id}",
        "simulated": True,
    }

    _SIMULATED_POSTS[post_id] = post_data

    return {
        "status": "posted",
        "post_id": post_id,
        "platform": "twitter",
        "url": post_data["url"],
        "content": content,
        "simulated": True,
        "message": "Post simulated - set TWITTER_BEARER_TOKEN for real posting",
    }


@tool(
    name="post_to_linkedin",
    description="Post content to LinkedIn. Requires user approval before posting.",
    requires_approval=True,
    approval_timeout="1h",
)
async def post_to_linkedin(
    content: str,
    image_url: str | None = None,
    article_url: str | None = None,
) -> dict[str, Any]:
    """
    Post content to LinkedIn (simulated).

    Args:
        content: The post content (max 3000 characters).
        image_url: Optional URL of image to attach.
        article_url: Optional URL of article to share.

    Returns:
        Dict with post details and simulated post ID.
    """
    # Validate content length
    if len(content) > 3000:
        return {
            "status": "error",
            "error": f"Content exceeds 3000 characters ({len(content)} chars)",
            "platform": "linkedin",
        }

    post_id = f"li_{uuid.uuid4().hex[:12]}"
    post_data = {
        "id": post_id,
        "platform": "linkedin",
        "content": content,
        "image_url": image_url,
        "article_url": article_url,
        "posted_at": datetime.utcnow().isoformat(),
        "url": f"https://linkedin.com/feed/update/urn:li:share:{post_id}",
        "simulated": True,
    }

    _SIMULATED_POSTS[post_id] = post_data

    return {
        "status": "posted",
        "post_id": post_id,
        "platform": "linkedin",
        "url": post_data["url"],
        "content": content,
        "simulated": True,
        "message": "Post simulated - set LINKEDIN_ACCESS_TOKEN for real posting",
    }


@tool(
    name="post_to_instagram",
    description="Post content to Instagram. Requires an image and user approval before posting.",
    requires_approval=True,
    approval_timeout="1h",
)
async def post_to_instagram(
    content: str,
    image_url: str,
    location: str | None = None,
) -> dict[str, Any]:
    """
    Post content to Instagram (simulated).

    Args:
        content: The caption (max 2200 characters).
        image_url: URL of image to post (required for Instagram).
        location: Optional location tag.

    Returns:
        Dict with post details and simulated post ID.
    """
    # Validate content length
    if len(content) > 2200:
        return {
            "status": "error",
            "error": f"Caption exceeds 2200 characters ({len(content)} chars)",
            "platform": "instagram",
        }

    if not image_url:
        return {
            "status": "error",
            "error": "Instagram requires an image",
            "platform": "instagram",
        }

    post_id = f"ig_{uuid.uuid4().hex[:12]}"
    post_data = {
        "id": post_id,
        "platform": "instagram",
        "content": content,
        "image_url": image_url,
        "location": location,
        "posted_at": datetime.utcnow().isoformat(),
        "url": f"https://instagram.com/p/{post_id}",
        "simulated": True,
    }

    _SIMULATED_POSTS[post_id] = post_data

    return {
        "status": "posted",
        "post_id": post_id,
        "platform": "instagram",
        "url": post_data["url"],
        "content": content,
        "simulated": True,
        "message": "Post simulated - set INSTAGRAM_ACCESS_TOKEN for real posting",
    }
