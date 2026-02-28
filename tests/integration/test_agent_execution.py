"""Integration tests for agent loop execution with mocked LLM."""

from unittest.mock import AsyncMock, patch

import pytest
from flowforge.agent import AgentResult
from flowforge.exceptions import StepCompleted
from flowforge.steps import StepManager
from flowforge.tools import tool


# Test tools for agent execution
@tool(name="search", description="Search for information")
async def search_tool(query: str) -> str:
    """Search for information."""
    return f"Search results for: {query}"


@tool(name="calculator", description="Perform calculations")
async def calculator_tool(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(name="get_data", description="Retrieve data from database")
async def get_data_tool(id: str) -> dict:
    """Get data by ID."""
    return {"id": id, "name": f"Item {id}", "status": "active"}


@tool(
    name="send_notification",
    description="Send notification to user",
    requires_approval=True,
    approval_timeout="5m",
)
async def send_notification_tool(message: str, recipient: str) -> dict:
    """Send notification (requires approval)."""
    return {
        "status": "sent",
        "message": message,
        "recipient": recipient,
        "sent_at": "2025-01-23T10:00:00Z",
    }


@pytest.fixture
def step_manager():
    """Create a StepManager instance for testing."""
    return StepManager(run_id="test-run-123")


class TestBasicAgentExecution:
    """Test basic agent execution scenarios."""

    @pytest.mark.asyncio
    async def test_agent_completes_without_tools(self, step_manager):
        """Test agent that completes immediately without calling any tools."""

        with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
            # Agent returns answer immediately
            mock_ai.return_value = {
                "content": "This is my final answer.",
                "finish_reason": "stop",
                "usage": {"total_tokens": 50, "prompt_tokens": 30, "completion_tokens": 20},
                "tool_calls": None,
            }

            # Execute agent
            with pytest.raises(StepCompleted) as exc_info:
                await step_manager.agent(
                    "agent-test",
                    task="Answer this simple question",
                    model="gpt-5",
                    tools=[],
                )

            # Verify result
            assert exc_info.value.step_id == "agent-test"
            result_dict = exc_info.value.result

            assert result_dict["output"] == "This is my final answer."
            assert result_dict["status"] == "completed"
            assert result_dict["iterations"] == 1
            assert result_dict["tool_calls_count"] == 0
            assert result_dict["tokens_used"] == 50

    @pytest.mark.asyncio
    async def test_agent_single_tool_call(self, step_manager):
        """Test agent that makes one tool call and completes."""

        ai_responses = [
            # First call: request tool
            {
                "content": "",
                "finish_reason": "tool_calls",
                "usage": {"total_tokens": 100},
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "search",
                            "arguments": '{"query": "Python programming"}',
                        },
                    }
                ],
            },
            # Second call: final answer
            {
                "content": "Based on the search results, Python is a programming language.",
                "finish_reason": "stop",
                "usage": {"total_tokens": 75},
                "tool_calls": None,
            },
        ]

        with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
            with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
                mock_ai.side_effect = ai_responses
                mock_run.return_value = "Search results for: Python programming"

                # Execute agent
                with pytest.raises(StepCompleted) as exc_info:
                    await step_manager.agent(
                        "agent-test",
                        task="Search for Python",
                        model="gpt-5",
                        tools=[search_tool],
                    )

                # Verify result
                result_dict = exc_info.value.result

                assert result_dict["status"] == "completed"
                assert result_dict["iterations"] == 2
                assert result_dict["tool_calls_count"] == 1
                assert result_dict["tokens_used"] == 175
                assert len(result_dict["tool_calls"]) == 1
                assert result_dict["tool_calls"][0]["tool"] == "search"
                assert result_dict["tool_calls"][0]["status"] == "success"

                # Verify step.run was called correctly
                mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_multiple_tool_calls(self, step_manager):
        """Test agent that makes multiple sequential tool calls."""

        ai_responses = [
            # Iteration 1: search
            {
                "content": "",
                "finish_reason": "tool_calls",
                "usage": {"total_tokens": 100},
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "search", "arguments": '{"query": "weather"}'},
                    }
                ],
            },
            # Iteration 2: calculate
            {
                "content": "",
                "finish_reason": "tool_calls",
                "usage": {"total_tokens": 80},
                "tool_calls": [
                    {
                        "id": "call_2",
                        "function": {"name": "calculator", "arguments": '{"expression": "25*1.8+32"}'},
                    }
                ],
            },
            # Iteration 3: final answer
            {
                "content": "The temperature is 77°F (25°C).",
                "finish_reason": "stop",
                "usage": {"total_tokens": 60},
            },
        ]

        with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
            with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
                mock_ai.side_effect = ai_responses
                mock_run.side_effect = [
                    "Search results for: weather",
                    "Result: 77.0",
                ]

                # Execute agent
                with pytest.raises(StepCompleted) as exc_info:
                    await step_manager.agent(
                        "agent-test",
                        task="Convert temperature",
                        model="gpt-5",
                        tools=[search_tool, calculator_tool],
                    )

                result_dict = exc_info.value.result

                assert result_dict["status"] == "completed"
                assert result_dict["iterations"] == 3
                assert result_dict["tool_calls_count"] == 2
                assert result_dict["tokens_used"] == 240
                assert len(result_dict["tool_calls"]) == 2


class TestAgentLimits:
    """Test agent iteration and tool call limits."""

    @pytest.mark.asyncio
    async def test_agent_max_iterations_limit(self, step_manager):
        """Test that agent stops at max_iterations."""

        # AI keeps requesting tools indefinitely
        with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
            with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
                mock_ai.return_value = {
                    "content": "Need more info",
                    "finish_reason": "tool_calls",
                    "usage": {"total_tokens": 50},
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {"name": "search", "arguments": '{"query": "test"}'},
                        }
                    ],
                }
                mock_run.return_value = "Result"

                # Execute with max_iterations=3
                with pytest.raises(StepCompleted) as exc_info:
                    await step_manager.agent(
                        "agent-test",
                        task="Keep searching",
                        model="gpt-5",
                        tools=[search_tool],
                        max_iterations=3,
                        max_tool_calls=100,
                    )

                result_dict = exc_info.value.result

                assert result_dict["status"] == "max_iterations"
                assert result_dict["iterations"] == 3
                # Each iteration makes 1 tool call
                assert result_dict["tool_calls_count"] == 3

    @pytest.mark.asyncio
    async def test_agent_max_tool_calls_limit(self, step_manager):
        """Test that agent stops at max_tool_calls."""

        with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
            with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
                # Return 2 tool calls per iteration
                mock_ai.return_value = {
                    "content": "",
                    "finish_reason": "tool_calls",
                    "usage": {"total_tokens": 50},
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {"name": "search", "arguments": '{"query": "a"}'},
                        },
                        {
                            "id": "call_2",
                            "function": {"name": "search", "arguments": '{"query": "b"}'},
                        },
                    ],
                }
                mock_run.return_value = "Result"

                # Execute with max_tool_calls=5
                with pytest.raises(StepCompleted) as exc_info:
                    await step_manager.agent(
                        "agent-test",
                        task="Multiple searches",
                        model="gpt-5",
                        tools=[search_tool],
                        max_iterations=100,
                        max_tool_calls=5,
                    )

                result_dict = exc_info.value.result

                assert result_dict["status"] == "max_tool_calls"
                # Should have made at least 5 tool calls (might be 6 due to iteration boundary)
                assert result_dict["tool_calls_count"] >= 5


class TestAgentWithHITL:
    """Test agent execution with human-in-the-loop approval."""

    @pytest.mark.asyncio
    async def test_agent_approval_granted(self, step_manager):
        """Test tool execution proceeds when approval is granted."""

        ai_responses = [
            # Request tool requiring approval
            {
                "content": "",
                "finish_reason": "tool_calls",
                "usage": {"total_tokens": 100},
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "send_notification",
                            "arguments": '{"message": "Hello", "recipient": "user@example.com"}',
                        },
                    }
                ],
            },
            # Complete after approval
            {
                "content": "Notification sent successfully.",
                "finish_reason": "stop",
                "usage": {"total_tokens": 50},
            },
        ]

        with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
            with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
                with patch.object(step_manager, "wait_for_event", new_callable=AsyncMock) as mock_wait:
                    mock_ai.side_effect = ai_responses
                    mock_wait.return_value = {
                        "data": {"approved": True, "tool_call_id": "call_1"}
                    }
                    mock_run.return_value = {
                        "status": "sent",
                        "message": "Hello",
                        "recipient": "user@example.com",
                    }

                    # Execute agent
                    with pytest.raises(StepCompleted) as exc_info:
                        await step_manager.agent(
                            "agent-test",
                            task="Send notification",
                            model="gpt-5",
                            tools=[send_notification_tool],
                        )

                    # Verify approval was requested
                    mock_wait.assert_called_once()
                    call_args = mock_wait.call_args[0]
                    assert "approval" in call_args[0]

                    # Verify tool was executed
                    mock_run.assert_called_once()

                    # Verify result
                    result_dict = exc_info.value.result
                    assert result_dict["status"] == "completed"
                    assert result_dict["tool_calls_count"] == 1

    @pytest.mark.asyncio
    async def test_agent_approval_rejected(self, step_manager):
        """Test tool execution is skipped when approval is rejected."""

        ai_responses = [
            # Request tool requiring approval
            {
                "content": "",
                "finish_reason": "tool_calls",
                "usage": {"total_tokens": 100},
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "send_notification",
                            "arguments": '{"message": "Test", "recipient": "user@example.com"}',
                        },
                    }
                ],
            },
            # Continue after rejection
            {
                "content": "I understand. The notification was not sent.",
                "finish_reason": "stop",
                "usage": {"total_tokens": 50},
            },
        ]

        with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
            with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
                with patch.object(step_manager, "wait_for_event", new_callable=AsyncMock) as mock_wait:
                    mock_ai.side_effect = ai_responses
                    mock_wait.return_value = {
                        "data": {
                            "approved": False,
                            "tool_call_id": "call_1",
                            "reason": "User declined",
                        }
                    }

                    # Execute agent
                    with pytest.raises(StepCompleted) as exc_info:
                        await step_manager.agent(
                            "agent-test",
                            task="Try to send notification",
                            model="gpt-5",
                            tools=[send_notification_tool],
                        )

                    # Verify approval was requested
                    mock_wait.assert_called_once()

                    # Verify tool was NOT executed
                    mock_run.assert_not_called()

                    # Check tool call was marked as rejected
                    result_dict = exc_info.value.result
                    assert len(result_dict["tool_calls"]) == 1
                    assert result_dict["tool_calls"][0]["status"] == "rejected"
                    assert "User declined" in result_dict["tool_calls"][0]["reason"]


class TestAgentErrorHandling:
    """Test agent error handling scenarios."""

    @pytest.mark.asyncio
    async def test_agent_tool_not_found(self, step_manager):
        """Test agent handles nonexistent tool gracefully."""

        ai_responses = [
            # Request nonexistent tool
            {
                "content": "",
                "finish_reason": "tool_calls",
                "usage": {"total_tokens": 50},
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "nonexistent_tool", "arguments": "{}"},
                    }
                ],
            },
            # Continue after error
            {
                "content": "I apologize, that tool is not available.",
                "finish_reason": "stop",
                "usage": {"total_tokens": 40},
            },
        ]

        with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.side_effect = ai_responses

            # Execute agent
            with pytest.raises(StepCompleted) as exc_info:
                await step_manager.agent(
                    "agent-test",
                    task="Use missing tool",
                    model="gpt-5",
                    tools=[search_tool],
                )

            # Verify error was added to messages
            result_dict = exc_info.value.result
            messages = result_dict["messages"]

            # Find tool error message
            tool_error = None
            for msg in messages:
                if msg.get("role") == "tool" and "error" in msg.get("content", "").lower():
                    tool_error = msg
                    break

            assert tool_error is not None
            assert "not found" in tool_error["content"].lower()

    @pytest.mark.asyncio
    async def test_agent_tool_execution_failure(self, step_manager):
        """Test agent handles tool execution errors."""

        @tool(name="failing_tool", description="Tool that fails")
        async def failing_tool(x: str) -> str:
            raise ValueError("Tool execution failed")

        ai_responses = [
            # Request failing tool
            {
                "content": "",
                "finish_reason": "tool_calls",
                "usage": {"total_tokens": 50},
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "failing_tool", "arguments": '{"x": "test"}'},
                    }
                ],
            },
            # Handle error
            {
                "content": "There was an error executing the tool.",
                "finish_reason": "stop",
                "usage": {"total_tokens": 40},
            },
        ]

        with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
            with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
                mock_ai.side_effect = ai_responses
                mock_run.side_effect = ValueError("Tool execution failed")

                # Execute agent
                with pytest.raises(StepCompleted) as exc_info:
                    await step_manager.agent(
                        "agent-test",
                        task="Use failing tool",
                        model="gpt-5",
                        tools=[failing_tool],
                    )

                result_dict = exc_info.value.result

                # Check that error was recorded in tool calls
                assert len(result_dict["tool_calls"]) == 1
                assert result_dict["tool_calls"][0]["status"] == "failed"
                assert "error" in result_dict["tool_calls"][0]


class TestAgentMemoization:
    """Test agent step memoization."""

    @pytest.mark.asyncio
    async def test_agent_returns_cached_result(self, step_manager):
        """Test that completed agent returns memoized result."""

        # Add a completed agent result to cache
        cached_result = {
            "output": "Cached answer",
            "status": "completed",
            "iterations": 5,
            "tool_calls_count": 3,
            "tokens_used": 500,
            "messages": [{"role": "assistant", "content": "Cached answer"}],
            "tool_calls": [],
        }

        # Mock the hash function and add to completed steps
        with patch("flowforge.steps._hash_step_id") as mock_hash:
            mock_hash.return_value = "cached_hash"
            step_manager._completed_steps["cached_hash"] = cached_result

            # Execute agent - should return cached result
            result = await step_manager.agent(
                "cached-agent",
                task="Test task",
                model="gpt-5",
                tools=[],
            )

            # Verify we got the cached result
            assert isinstance(result, AgentResult)
            assert result.output == "Cached answer"
            assert result.status == "completed"
            assert result.iterations == 5
            assert result.tool_calls_count == 3
            assert result.tokens_used == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
