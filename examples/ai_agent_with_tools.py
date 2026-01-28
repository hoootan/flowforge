"""
Example: Complete Travel Planning Agent with Multiple Tools

This example demonstrates a comprehensive travel planning agent that uses
multiple tools to research destinations, check weather, find attractions,
and book restaurants with human-in-the-loop approval.
"""

import flowforge
from flowforge import tool, Context


# Search tool for web research
@tool(
    name="search_web",
    description="Search the web for information about destinations, activities, or travel tips",
)
async def search_web(query: str) -> dict:
    """
    Search the web for travel-related information.

    Args:
        query: The search query (e.g., "best time to visit Tokyo", "Tokyo attractions")

    Returns:
        Search results with titles, snippets, and URLs
    """
    # Simulate web search API call
    return {
        "query": query,
        "results": [
            {
                "title": f"Top results for {query}",
                "snippet": f"Comprehensive information about {query}...",
                "url": "https://example.com/result1"
            },
            {
                "title": f"Expert guide to {query}",
                "snippet": f"Everything you need to know about {query}...",
                "url": "https://example.com/result2"
            },
            {
                "title": f"{query} - Travel Tips",
                "snippet": f"Insider tips and recommendations for {query}...",
                "url": "https://example.com/result3"
            }
        ]
    }


# Weather API tool
@tool(
    name="get_weather",
    description="Get current weather and forecast for a specific location",
)
async def get_weather(location: str, days: int = 3) -> dict:
    """
    Get weather information for a travel destination.

    Args:
        location: City or location name (e.g., "Tokyo", "Paris")
        days: Number of days to forecast (1-7)

    Returns:
        Current weather and multi-day forecast
    """
    # Simulate weather API call
    return {
        "location": location,
        "current": {
            "temperature": "22°C",
            "condition": "Partly Cloudy",
            "humidity": "65%",
            "wind": "12 km/h"
        },
        "forecast": [
            {"day": "Day 1", "high": "24°C", "low": "18°C", "condition": "Sunny"},
            {"day": "Day 2", "high": "23°C", "low": "17°C", "condition": "Cloudy"},
            {"day": "Day 3", "high": "25°C", "low": "19°C", "condition": "Sunny"},
        ][:days]
    }


# Attractions finder tool
@tool(
    name="get_attractions",
    description="Get top tourist attractions and points of interest for a city",
)
async def get_attractions(city: str, category: str = "all", limit: int = 10) -> dict:
    """
    Get tourist attractions for a destination.

    Args:
        city: City name (e.g., "Tokyo", "Paris")
        category: Category filter (e.g., "museums", "parks", "restaurants", "all")
        limit: Maximum number of attractions to return (1-20)

    Returns:
        List of attractions with names, ratings, and descriptions
    """
    # Simulate attractions API call
    attractions = [
        {"name": "Historic Temple", "category": "cultural", "rating": 4.8, "description": "Ancient temple with beautiful gardens"},
        {"name": "National Museum", "category": "museums", "rating": 4.7, "description": "World-class art and history museum"},
        {"name": "City Park", "category": "parks", "rating": 4.6, "description": "Large urban park with scenic views"},
        {"name": "Traditional Market", "category": "shopping", "rating": 4.9, "description": "Bustling market with local food and crafts"},
        {"name": "Observation Tower", "category": "landmarks", "rating": 4.8, "description": "Panoramic city views from 450m high"},
        {"name": "Botanical Garden", "category": "parks", "rating": 4.5, "description": "Extensive garden with rare plants"},
        {"name": "Modern Art Gallery", "category": "museums", "rating": 4.6, "description": "Contemporary art exhibitions"},
        {"name": "Historic Castle", "category": "cultural", "rating": 4.9, "description": "Medieval castle with preserved interiors"},
    ]

    # Filter by category if specified
    if category != "all":
        attractions = [a for a in attractions if a["category"] == category]

    return {
        "city": city,
        "category": category,
        "attractions": attractions[:limit]
    }


# Restaurant booking tool (requires approval)
@tool(
    name="send_email",
    description="Send an email with itinerary, recommendations, or confirmations",
    requires_approval=True,
    approval_timeout="10m",
)
async def send_email(to: str, subject: str, body: str) -> dict:
    """
    Send an email - requires human approval before sending.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content

    Returns:
        Email send confirmation
    """
    # This tool requires approval before execution
    return {
        "status": "sent",
        "to": to,
        "subject": subject,
        "message_id": "msg_abc123xyz",
        "sent_at": "2025-01-23T10:30:00Z"
    }


# Main travel planning agent function
@flowforge.function(
    id="travel-planner",
    name="Travel Planning Agent",
    trigger=flowforge.trigger.event("travel/plan"),
)
async def plan_travel(ctx: Context) -> dict:
    """
    Autonomous travel planning agent.

    This agent uses multiple tools to:
    1. Research the destination
    2. Check weather forecasts
    3. Find top attractions
    4. Create a day-by-day itinerary
    5. Send the itinerary via email (with approval)

    Event payload:
        - destination: City name (required)
        - duration_days: Number of days for the trip (default: 3)
        - interests: List of interests (e.g., ["culture", "food", "nature"])
        - email: Email address to send itinerary (optional)
    """
    # Extract parameters from event
    destination = ctx.event.data.get("destination", "Tokyo")
    duration_days = ctx.event.data.get("duration_days", 3)
    interests = ctx.event.data.get("interests", ["culture", "food", "sightseeing"])
    email = ctx.event.data.get("email")

    # Build task description
    task_description = (
        f"Plan a comprehensive {duration_days}-day trip to {destination}. "
        f"The traveler is interested in: {', '.join(interests)}. "
        f"\n\nPlease:\n"
        f"1. Research {destination} to understand the best areas to visit\n"
        f"2. Check the weather forecast for planning appropriate activities\n"
        f"3. Find top attractions matching the interests: {', '.join(interests)}\n"
        f"4. Create a detailed day-by-day itinerary with specific recommendations\n"
        f"5. Include practical tips (transportation, best times to visit, etc.)\n"
    )

    if email:
        task_description += f"6. Send the final itinerary to {email}\n"

    # Execute the agent loop
    result = await flowforge.step.agent(
        "travel-planner-agent",
        task=task_description,
        model="claude-sonnet-4-20250514",
        system=(
            "You are an expert travel planning assistant with deep knowledge of destinations worldwide. "
            "Create comprehensive, practical travel itineraries that are well-researched and personalized. "
            "Always use the available tools to gather current information rather than relying on your training data. "
            "Be specific with recommendations - include names of places, estimated times, and practical tips. "
            "When creating itineraries, balance popular attractions with hidden gems."
        ),
        tools=[search_web, get_weather, get_attractions, send_email],
        max_iterations=15,
        checkpoint_strategy="per_tool",
        max_tool_calls=50,
        temperature=0.7,
    )

    # Return the result with metrics
    return {
        "destination": destination,
        "duration_days": duration_days,
        "itinerary": result.output,
        "execution_stats": {
            "status": result.status,
            "iterations": result.iterations,
            "tool_calls": result.tool_calls_count,
            "tokens_used": result.tokens_used,
        },
        "tool_usage": [
            {
                "iteration": tc["iteration"],
                "tool": tc["tool"],
                "status": tc.get("status", "unknown"),
            }
            for tc in result.tool_calls
        ],
    }


# Additional example: Quick weather-focused planner
@flowforge.function(
    id="weather-planner",
    name="Weather-Based Activity Planner",
    trigger=flowforge.trigger.event("travel/weather-plan"),
)
async def weather_based_planner(ctx: Context) -> dict:
    """
    Create activity recommendations based on weather forecast.

    This simpler agent focuses on weather-appropriate activities.
    """
    destination = ctx.event.data.get("destination", "Tokyo")

    result = await flowforge.step.agent(
        "weather-activities",
        task=f"Check the weather for {destination} and recommend appropriate activities for each day",
        model="gpt-4o",
        system="You are a travel assistant. Recommend indoor activities for rainy days and outdoor activities for sunny days.",
        tools=[get_weather, get_attractions],
        max_iterations=10,
    )

    return {
        "destination": destination,
        "recommendations": result.output,
        "stats": {
            "iterations": result.iterations,
            "tool_calls": result.tool_calls_count,
        },
    }


if __name__ == "__main__":
    # Test the agent locally
    import asyncio

    async def test_travel_planner():
        """Test the travel planning agent."""
        event = flowforge.Event(
            name="travel/plan",
            data={
                "destination": "Tokyo",
                "duration_days": 3,
                "interests": ["culture", "food", "technology"],
                "email": "traveler@example.com"
            },
        )
        ctx = Context(event=event, run_id="test-run-123")

        # Note: This will raise StepCompleted in real execution
        # For testing, you'd need to mock the step manager
        try:
            result = await plan_travel(ctx)
            print("Travel Plan Result:")
            print(f"Destination: {result['destination']}")
            print(f"Duration: {result['duration_days']} days")
            print(f"\nItinerary:\n{result['itinerary']}")
            print(f"\nExecution Stats: {result['execution_stats']}")
        except flowforge.StepCompleted as e:
            print(f"Step completed (expected in test): {e.step_id}")

    asyncio.run(test_travel_planner())
