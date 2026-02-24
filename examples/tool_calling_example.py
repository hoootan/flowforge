"""Example demonstrating tool calling with FlowForge."""

import flowforge
from flowforge import tool


@tool(
    name="search_database",
    description="Search customer database by email or ID",
    requires_approval=False,
)
async def search_database(query: str, field: str = "email") -> dict:
    """
    Search the customer database.

    Args:
        query: The search query (email or ID)
        field: The field to search by (email or id)

    Returns:
        Dictionary containing search results
    """
    # Simulate database search
    return {
        "results": [
            {
                "id": "123",
                "email": query if field == "email" else "customer@example.com",
                "name": "John Doe",
                "orders": 5,
            }
        ]
    }


@tool(
    name="get_weather",
    description="Get current weather for a city",
    requires_approval=False,
)
async def get_weather(city: str, units: str = "celsius") -> dict:
    """
    Get weather information for a city.

    Args:
        city: The city name
        units: Temperature units (celsius or fahrenheit)

    Returns:
        Dictionary containing weather data
    """
    # Simulate weather API
    return {
        "city": city,
        "temperature": 22 if units == "celsius" else 72,
        "units": units,
        "conditions": "Partly cloudy",
    }


@flowforge.function(
    id="tool-calling-demo",
    name="Tool Calling Demo",
)
async def tool_calling_demo(ctx: flowforge.Context, step: flowforge.step) -> dict:
    """Demonstrate tool calling capabilities."""

    # Example 1: LLM with tools (auto choice)
    result1 = await step.ai(
        "search-customer",
        model="gpt-5",
        prompt="Find the customer with email john@example.com",
        tools=[search_database],
        tool_choice="auto",
    )

    print(f"Result 1 - Content: {result1.get('content')}")
    if result1.get("tool_calls"):
        print(f"Tool calls made: {result1['tool_calls']}")

    # Example 2: Multiple tools
    result2 = await step.ai(
        "weather-and-search",
        model="gpt-5",
        prompt="What's the weather in Tokyo and find customer alice@example.com?",
        tools=[search_database, get_weather],
        tool_choice="auto",
    )

    print(f"Result 2 - Content: {result2.get('content')}")
    if result2.get("tool_calls"):
        print(f"Tool calls made: {result2['tool_calls']}")

    # Example 3: Without tools (regular chat)
    result3 = await step.ai(
        "regular-chat",
        model="gpt-5",
        prompt="What is the capital of France?",
    )

    print(f"Result 3 - Content: {result3.get('content')}")

    return {
        "example1": result1,
        "example2": result2,
        "example3": result3,
    }


if __name__ == "__main__":
    # For local testing
    import asyncio

    async def test():
        # Test tool schema generation
        print("=== Tool Schema Testing ===\n")

        print("search_database OpenAI schema:")
        print(search_database.to_openai_schema())
        print()

        print("search_database Anthropic schema:")
        print(search_database.to_anthropic_schema())
        print()

        print("get_weather OpenAI schema:")
        print(get_weather.to_openai_schema())
        print()

    asyncio.run(test())
