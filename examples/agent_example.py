"""
Example: Autonomous Agent with Tool Calling

This example demonstrates the agent() primitive with multiple tools,
showing how an agent can autonomously plan and execute a multi-step task.
"""

import flowforge
from flowforge import tool


# Define tools for the agent
@tool(
    name="web_search",
    description="Search the web for information about a query",
)
async def web_search(query: str) -> dict:
    """
    Simulate a web search.

    Args:
        query: The search query
    """
    # In a real implementation, this would call a search API
    return {
        "results": [
            {"title": f"Result for {query}", "snippet": f"Information about {query}..."},
            {"title": f"More about {query}", "snippet": f"Additional details on {query}..."},
        ]
    }


@tool(
    name="get_weather",
    description="Get current weather for a city",
)
async def get_weather(city: str) -> dict:
    """
    Get weather information for a city.

    Args:
        city: The city name
    """
    # Simulate weather API call
    return {
        "city": city,
        "temperature": "22°C",
        "condition": "Sunny",
        "humidity": "65%",
    }


@tool(
    name="get_attractions",
    description="Get top tourist attractions for a city",
)
async def get_attractions(city: str, limit: int = 5) -> dict:
    """
    Get tourist attractions for a city.

    Args:
        city: The city name
        limit: Maximum number of attractions to return
    """
    # Simulate attractions API call
    return {
        "city": city,
        "attractions": [
            {"name": "Temple", "rating": 4.8},
            {"name": "Museum", "rating": 4.6},
            {"name": "Park", "rating": 4.5},
            {"name": "Market", "rating": 4.7},
            {"name": "Tower", "rating": 4.9},
        ][:limit]
    }


@tool(
    name="book_restaurant",
    description="Book a restaurant reservation",
    requires_approval=True,
    approval_timeout="5m",
)
async def book_restaurant(restaurant: str, date: str, party_size: int) -> dict:
    """
    Book a restaurant reservation (requires human approval).

    Args:
        restaurant: Restaurant name
        date: Reservation date
        party_size: Number of people
    """
    # This tool requires approval before execution
    return {
        "status": "confirmed",
        "restaurant": restaurant,
        "date": date,
        "party_size": party_size,
        "confirmation_id": "ABC123",
    }


@flowforge.function(
    id="travel-planner",
    name="Travel Planning Agent",
    trigger=flowforge.trigger.event("plan/trip"),
)
async def travel_planner(ctx: flowforge.Context) -> dict:
    """
    Autonomous travel planning agent.

    Uses multiple tools to research and plan a trip itinerary.
    """
    destination = ctx.event.data.get("destination", "Tokyo")
    duration_days = ctx.event.data.get("duration_days", 3)

    # Run the agent loop
    result = await flowforge.step.agent(
        "plan-trip",
        task=f"Research {destination} and create a detailed {duration_days}-day travel itinerary. "
             f"Include weather, top attractions to visit each day, and restaurant recommendations.",
        model="claude-sonnet-4-20250514",
        system="You are an expert travel planning assistant. Create comprehensive, "
               "practical travel itineraries with specific recommendations.",
        tools=[web_search, get_weather, get_attractions, book_restaurant],
        max_iterations=20,
        checkpoint_strategy="per_tool",
        max_tool_calls=50,
        temperature=0.7,
    )

    return {
        "itinerary": result.output,
        "stats": {
            "iterations": result.iterations,
            "tool_calls": result.tool_calls_count,
            "tokens_used": result.tokens_used,
            "status": result.status,
        },
        "tool_usage": result.tool_calls,
    }


@flowforge.function(
    id="research-agent",
    name="Research Agent with HITL",
    trigger=flowforge.trigger.event("research/request"),
)
async def research_agent(ctx: flowforge.Context) -> dict:
    """
    Research agent that requires human approval for sensitive actions.
    """
    topic = ctx.event.data.get("topic", "AI safety")

    result = await flowforge.step.agent(
        "research",
        task=f"Research {topic} and provide a comprehensive summary with key findings.",
        model="gpt-4o",
        system="You are a research assistant. Provide accurate, well-sourced information.",
        tools=[web_search],
        max_iterations=10,
    )

    return {
        "summary": result.output,
        "metrics": {
            "iterations": result.iterations,
            "tool_calls": result.tool_calls_count,
            "status": result.status,
        },
    }


if __name__ == "__main__":
    # Test the agent locally
    import asyncio
    from flowforge import Context, Event

    async def test():
        # Create a test context
        event = Event(
            name="plan/trip",
            data={"destination": "Tokyo", "duration_days": 3},
        )
        ctx = Context(event=event, run_id="test-run")

        # Run the agent
        result = await travel_planner(ctx)
        print("Agent Result:")
        print(result)

    asyncio.run(test())
