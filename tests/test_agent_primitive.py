"""Tests for the agent() primitive."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from flowforge.steps import StepManager
from flowforge.agent import AgentConfig, AgentState, AgentResult
from flowforge.tools import tool
from flowforge.exceptions import StepCompleted


@pytest.fixture
def step_manager():
    """Create a StepManager instance for testing."""
    return StepManager(run_id="test-run")


# Define test tools
@tool(name="search", description="Search for information")
async def search_tool(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"


@tool(name="calculator", description="Perform calculations")
async def calculator_tool(expression: str) -> str:
    """Calculate a mathematical expression."""
    return f"Result: {eval(expression)}"


@tool(
    name="sensitive_action",
    description="Perform sensitive action",
    requires_approval=True,
    approval_timeout="5m",
)
async def sensitive_tool(action: str) -> str:
    """Perform a sensitive action that requires approval."""
    return f"Executed: {action}"


@pytest.mark.asyncio
async def test_agent_basic_execution(step_manager):
    """Test basic agent execution without tool calls."""

    # Mock the AI response to return immediately without tool calls
    with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = {
            "content": "This is the final answer.",
            "finish_reason": "stop",
            "usage": {"total_tokens": 100},
            "tool_calls": None,
        }

        # Execute agent
        with pytest.raises(StepCompleted) as exc_info:
            await step_manager.agent(
                "test-agent",
                task="Answer this question",
                model="gpt-4o",
                tools=[],
                max_iterations=5,
            )

        # Verify StepCompleted was raised with correct result
        assert exc_info.value.step_id == "test-agent"
        result_dict = exc_info.value.result

        assert result_dict["output"] == "This is the final answer."
        assert result_dict["status"] == "completed"
        assert result_dict["iterations"] == 1
        assert result_dict["tool_calls_count"] == 0


@pytest.mark.asyncio
async def test_agent_with_tool_calls(step_manager):
    """Test agent execution with tool calling."""

    # Mock AI responses: first with tool call, then completion
    ai_responses = [
        {
            "content": "",
            "finish_reason": "tool_calls",
            "usage": {"total_tokens": 50},
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "search",
                        "arguments": '{"query": "Python"}',
                    },
                }
            ],
        },
        {
            "content": "Based on the search, Python is a programming language.",
            "finish_reason": "stop",
            "usage": {"total_tokens": 75},
            "tool_calls": None,
        },
    ]

    with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
        with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
            mock_ai.side_effect = ai_responses
            mock_run.return_value = "Results for: Python"

            # Execute agent
            with pytest.raises(StepCompleted) as exc_info:
                await step_manager.agent(
                    "test-agent",
                    task="Search for Python",
                    model="gpt-4o",
                    tools=[search_tool],
                    max_iterations=5,
                )

            # Verify result
            result_dict = exc_info.value.result
            assert result_dict["status"] == "completed"
            assert result_dict["iterations"] == 2
            assert result_dict["tool_calls_count"] == 1
            assert len(result_dict["tool_calls"]) == 1
            assert result_dict["tool_calls"][0]["tool"] == "search"


@pytest.mark.asyncio
async def test_agent_max_iterations(step_manager):
    """Test agent stops at max iterations."""

    # Mock AI to always request more tool calls
    with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
        with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
            mock_ai.return_value = {
                "content": "Need more info",
                "finish_reason": "tool_calls",
                "usage": {"total_tokens": 50},
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "search",
                            "arguments": '{"query": "test"}',
                        },
                    }
                ],
            }
            mock_run.return_value = "Result"

            # Execute with low max_iterations
            with pytest.raises(StepCompleted) as exc_info:
                await step_manager.agent(
                    "test-agent",
                    task="Keep searching",
                    model="gpt-4o",
                    tools=[search_tool],
                    max_iterations=3,
                    max_tool_calls=100,
                )

            # Verify stopped at max iterations
            result_dict = exc_info.value.result
            assert result_dict["status"] == "max_iterations"
            assert result_dict["iterations"] == 3


@pytest.mark.asyncio
async def test_agent_max_tool_calls(step_manager):
    """Test agent stops at max tool calls."""

    with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
        with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
            # Return 2 tool calls per iteration
            mock_ai.return_value = {
                "content": "Need more",
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

            # Execute with low max_tool_calls
            with pytest.raises(StepCompleted) as exc_info:
                await step_manager.agent(
                    "test-agent",
                    task="Search",
                    model="gpt-4o",
                    tools=[search_tool],
                    max_iterations=100,
                    max_tool_calls=3,
                )

            # Verify stopped at max tool calls
            result_dict = exc_info.value.result
            assert result_dict["status"] == "max_tool_calls"
            assert result_dict["tool_calls_count"] >= 3


@pytest.mark.asyncio
async def test_agent_with_approval_required(step_manager):
    """Test agent with tool that requires approval."""

    # Mock AI to call sensitive tool
    with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
        with patch.object(step_manager, "run", new_callable=AsyncMock) as mock_run:
            with patch.object(step_manager, "wait_for_event", new_callable=AsyncMock) as mock_wait:
                mock_ai.side_effect = [
                    {
                        "content": "",
                        "finish_reason": "tool_calls",
                        "usage": {"total_tokens": 50},
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "sensitive_action",
                                    "arguments": '{"action": "delete_database"}',
                                },
                            }
                        ],
                    },
                    {
                        "content": "Action completed",
                        "finish_reason": "stop",
                        "usage": {"total_tokens": 30},
                    },
                ]

                # Simulate approval granted
                mock_wait.return_value = {
                    "data": {"approved": True, "tool_call_id": "call_1"}
                }
                mock_run.return_value = "Executed: delete_database"

                # Execute agent
                with pytest.raises(StepCompleted) as exc_info:
                    await step_manager.agent(
                        "test-agent",
                        task="Do sensitive action",
                        model="gpt-4o",
                        tools=[sensitive_tool],
                        max_iterations=5,
                    )

                # Verify approval was requested
                mock_wait.assert_called_once()
                assert "approval" in mock_wait.call_args[0][0]


@pytest.mark.asyncio
async def test_agent_memoization(step_manager):
    """Test agent result is memoized on second call."""

    # Add a completed step to simulate memoization
    step_manager._completed_steps["test-agent-hash"] = {
        "output": "Cached output",
        "status": "completed",
        "iterations": 3,
        "tool_calls_count": 5,
        "tokens_used": 200,
        "messages": [],
        "tool_calls": [],
    }

    # Mock the hash function to return our test hash
    with patch("flowforge.steps._hash_step_id") as mock_hash:
        mock_hash.return_value = "test-agent-hash"

        # Execute agent - should return memoized result
        result = await step_manager.agent(
            "test-agent",
            task="Test task",
            model="gpt-4o",
            tools=[],
        )

        # Verify we got the cached result
        assert isinstance(result, AgentResult)
        assert result.output == "Cached output"
        assert result.iterations == 3
        assert result.tool_calls_count == 5


@pytest.mark.asyncio
async def test_agent_tool_not_found(step_manager):
    """Test agent handles tool not found gracefully."""

    with patch.object(step_manager, "ai", new_callable=AsyncMock) as mock_ai:
        mock_ai.side_effect = [
            {
                "content": "",
                "finish_reason": "tool_calls",
                "usage": {"total_tokens": 50},
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "nonexistent_tool",
                            "arguments": '{}',
                        },
                    }
                ],
            },
            {
                "content": "Tool not found, ending",
                "finish_reason": "stop",
                "usage": {"total_tokens": 30},
            },
        ]

        # Execute agent
        with pytest.raises(StepCompleted) as exc_info:
            await step_manager.agent(
                "test-agent",
                task="Use nonexistent tool",
                model="gpt-4o",
                tools=[search_tool],  # Only provide search_tool
                max_iterations=5,
            )

        # Verify tool error was added to messages
        result_dict = exc_info.value.result
        messages = result_dict["messages"]

        # Find the tool error message
        tool_error_msg = None
        for msg in messages:
            if msg.get("role") == "tool" and "error" in msg.get("content", ""):
                tool_error_msg = msg
                break

        assert tool_error_msg is not None
        assert "not found" in tool_error_msg["content"].lower()
