"""Image generation tool using Nano Banana (Google Gemini)."""

import os
import base64
from typing import Any, Literal

import httpx

from flowforge import tool


GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_IMAGE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"


ImageStyle = Literal[
    "professional",
    "creative",
    "minimalist",
    "vibrant",
    "corporate",
    "casual",
]


@tool(
    name="generate_image",
    description="Generate an image for social media posts using AI. Creates high-quality visuals based on text descriptions.",
)
async def generate_image(
    prompt: str,
    style: ImageStyle = "professional",
    aspect_ratio: str = "16:9",
) -> dict[str, Any]:
    """
    Generate an image using Google's Gemini/Nano Banana image generation.

    Args:
        prompt: Description of the image to generate.
        style: Visual style for the image (professional, creative, minimalist, etc.).
        aspect_ratio: Aspect ratio for the image (16:9, 1:1, 4:5, 9:16).

    Returns:
        Dict containing image URL or base64 data.
    """
    # Enhance prompt with style
    style_modifiers = {
        "professional": "professional, clean, modern, high-quality, suitable for business",
        "creative": "creative, artistic, unique, eye-catching, innovative design",
        "minimalist": "minimalist, simple, clean lines, lots of white space, elegant",
        "vibrant": "vibrant colors, energetic, bold, dynamic, attention-grabbing",
        "corporate": "corporate, formal, trustworthy, business-appropriate, polished",
        "casual": "casual, friendly, approachable, warm, relatable",
    }

    enhanced_prompt = f"{prompt}. Style: {style_modifiers.get(style, style)}. High quality, suitable for social media."

    if not GOOGLE_API_KEY:
        # Return placeholder image URL if no API key
        # Using placeholder.com for demo purposes
        width, height = _parse_aspect_ratio(aspect_ratio)
        placeholder_url = f"https://placehold.co/{width}x{height}/1a1a2e/eaeaea?text=AI+Generated+Image"

        return {
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "url": placeholder_url,
            "style": style,
            "aspect_ratio": aspect_ratio,
            "simulated": True,
            "message": "Set GOOGLE_API_KEY for real image generation with Nano Banana",
        }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{GEMINI_IMAGE_API_URL}?key={GOOGLE_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": f"Generate an image: {enhanced_prompt}"
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "responseModalities": ["TEXT", "IMAGE"],
                    },
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            # Extract image from response
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        image_data = part["inlineData"]
                        mime_type = image_data.get("mimeType", "image/png")
                        base64_data = image_data.get("data", "")

                        return {
                            "prompt": prompt,
                            "enhanced_prompt": enhanced_prompt,
                            "base64": base64_data,
                            "mime_type": mime_type,
                            "data_url": f"data:{mime_type};base64,{base64_data}",
                            "style": style,
                            "aspect_ratio": aspect_ratio,
                            "simulated": False,
                        }

            return {
                "prompt": prompt,
                "error": "No image generated in response",
                "url": None,
            }

        except httpx.HTTPStatusError as e:
            return {
                "prompt": prompt,
                "error": f"Image generation failed: {e.response.status_code}",
                "url": None,
            }
        except Exception as e:
            return {
                "prompt": prompt,
                "error": f"Image generation failed: {str(e)}",
                "url": None,
            }


def _parse_aspect_ratio(ratio: str) -> tuple[int, int]:
    """Parse aspect ratio string to width and height."""
    ratio_map = {
        "16:9": (1280, 720),
        "1:1": (1024, 1024),
        "4:5": (1080, 1350),
        "9:16": (720, 1280),
    }
    return ratio_map.get(ratio, (1280, 720))
