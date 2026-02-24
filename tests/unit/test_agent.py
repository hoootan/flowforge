"""Unit tests for agent data structures and configuration."""

import pytest
from flowforge.agent import AgentConfig, AgentState, AgentResult
from flowforge.tools import tool


# Sample test tools
@tool(name="test_tool", description="Test tool")
def test_tool(x: str) -> str:
    return f"result: {x}"


@tool(name="another_tool", description="Another tool")
async def another_tool(y: int) -> dict:
    return {"value": y * 2}


class TestAgentConfig:
    """Test AgentConfig dataclass."""

    def test_config_initialization_minimal(self):
        """Test creating config with minimal required parameters."""
        config = AgentConfig(model="gpt-5")

        assert config.model == "gpt-5"
        assert config.system == ""
        assert config.tools == []
        assert config.max_iterations == 20
        assert config.checkpoint_strategy == "per_tool"
        assert config.max_tool_calls == 50
        assert config.temperature == 0.7

    def test_config_initialization_full(self):
        """Test creating config with all parameters."""
        config = AgentConfig(
            model="claude-sonnet-4-6",
            system="You are a helpful assistant",
            tools=[test_tool, another_tool],
            max_iterations=30,
            checkpoint_strategy="per_iteration",
            max_tool_calls=100,
            temperature=0.5,
        )

        assert config.model == "claude-sonnet-4-6"
        assert config.system == "You are a helpful assistant"
        assert len(config.tools) == 2
        assert config.max_iterations == 30
        assert config.checkpoint_strategy == "per_iteration"
        assert config.max_tool_calls == 100
        assert config.temperature == 0.5

    def test_config_checkpoint_strategies(self):
        """Test different checkpoint strategy options."""
        strategies = ["per_tool", "per_iteration", "final_only"]

        for strategy in strategies:
            config = AgentConfig(
                model="gpt-5",
                checkpoint_strategy=strategy,
            )
            assert config.checkpoint_strategy == strategy

    def test_config_tools_list(self):
        """Test that tools can be provided as a list."""
        tools = [test_tool, another_tool]
        config = AgentConfig(model="gpt-5", tools=tools)

        assert len(config.tools) == 2
        assert config.tools[0] is test_tool
        assert config.tools[1] is another_tool

    def test_config_empty_system_prompt(self):
        """Test config with empty system prompt."""
        config = AgentConfig(model="gpt-5", system="")
        assert config.system == ""


class TestAgentState:
    """Test AgentState dataclass."""

    def test_state_initialization_default(self):
        """Test default state initialization."""
        state = AgentState()

        assert state.messages == []
        assert state.iteration == 0
        assert state.tool_calls_count == 0
        assert state.tokens_used == 0
        assert state.status == "running"

    def test_state_initialization_with_values(self):
        """Test state initialization with custom values."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        state = AgentState(
            messages=messages,
            iteration=5,
            tool_calls_count=10,
            tokens_used=1500,
            status="completed",
        )

        assert len(state.messages) == 2
        assert state.iteration == 5
        assert state.tool_calls_count == 10
        assert state.tokens_used == 1500
        assert state.status == "completed"

    def test_state_status_values(self):
        """Test different status values."""
        statuses = ["running", "completed", "max_iterations", "max_tool_calls", "failed"]

        for status in statuses:
            state = AgentState(status=status)
            assert state.status == status

    def test_state_messages_mutation(self):
        """Test that messages list can be modified."""
        state = AgentState()

        state.messages.append({"role": "user", "content": "Test"})
        assert len(state.messages) == 1

        state.messages.append({"role": "assistant", "content": "Response"})
        assert len(state.messages) == 2

    def test_state_iteration_increment(self):
        """Test incrementing iteration count."""
        state = AgentState()
        assert state.iteration == 0

        state.iteration += 1
        assert state.iteration == 1

        state.iteration += 1
        assert state.iteration == 2

    def test_state_token_accumulation(self):
        """Test accumulating token usage."""
        state = AgentState()
        assert state.tokens_used == 0

        state.tokens_used += 100
        assert state.tokens_used == 100

        state.tokens_used += 250
        assert state.tokens_used == 350


class TestAgentResult:
    """Test AgentResult dataclass."""

    def test_result_initialization(self):
        """Test creating an AgentResult."""
        messages = [
            {"role": "user", "content": "Task"},
            {"role": "assistant", "content": "Done"},
        ]

        tool_calls = [
            {"iteration": 0, "tool": "search", "status": "success"},
            {"iteration": 1, "tool": "calculator", "status": "success"},
        ]

        result = AgentResult(
            output="Final answer here",
            status="completed",
            iterations=3,
            tool_calls_count=2,
            tokens_used=500,
            messages=messages,
            tool_calls=tool_calls,
        )

        assert result.output == "Final answer here"
        assert result.status == "completed"
        assert result.iterations == 3
        assert result.tool_calls_count == 2
        assert result.tokens_used == 500
        assert len(result.messages) == 2
        assert len(result.tool_calls) == 2

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = AgentResult(
            output="Success",
            status="completed",
            iterations=2,
            tool_calls_count=1,
            tokens_used=200,
            messages=[{"role": "user", "content": "Hi"}],
            tool_calls=[{"iteration": 0, "tool": "test"}],
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["output"] == "Success"
        assert result_dict["status"] == "completed"
        assert result_dict["iterations"] == 2
        assert result_dict["tool_calls_count"] == 1
        assert result_dict["tokens_used"] == 200
        assert len(result_dict["messages"]) == 1
        assert len(result_dict["tool_calls"]) == 1

    def test_result_to_dict_all_fields(self):
        """Test that to_dict includes all fields."""
        result = AgentResult(
            output="Test output",
            status="max_iterations",
            iterations=20,
            tool_calls_count=45,
            tokens_used=3000,
            messages=[],
            tool_calls=[],
        )

        result_dict = result.to_dict()

        required_keys = [
            "output",
            "status",
            "iterations",
            "tool_calls_count",
            "tokens_used",
            "messages",
            "tool_calls",
        ]

        for key in required_keys:
            assert key in result_dict

    def test_result_empty_tool_calls(self):
        """Test result with no tool calls."""
        result = AgentResult(
            output="Answer without tools",
            status="completed",
            iterations=1,
            tool_calls_count=0,
            tokens_used=100,
            messages=[],
        )

        assert result.tool_calls == []
        assert result.tool_calls_count == 0

    def test_result_status_values(self):
        """Test different result status values."""
        statuses = ["completed", "max_iterations", "max_tool_calls", "failed"]

        for status in statuses:
            result = AgentResult(
                output="Test",
                status=status,
                iterations=1,
                tool_calls_count=0,
                tokens_used=50,
                messages=[],
            )
            assert result.status == status

    def test_result_with_complex_messages(self):
        """Test result with complex message structures."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User query"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "search", "arguments": '{"q": "test"}'},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "search",
                "content": '{"results": []}',
            },
            {"role": "assistant", "content": "Final answer"},
        ]

        result = AgentResult(
            output="Final answer",
            status="completed",
            iterations=2,
            tool_calls_count=1,
            tokens_used=300,
            messages=messages,
        )

        assert len(result.messages) == 5
        # Messages should be preserved as-is
        assert result.messages[0]["role"] == "system"
        assert result.messages[2].get("tool_calls") is not None
        assert result.messages[3]["role"] == "tool"

    def test_result_with_detailed_tool_calls(self):
        """Test result with detailed tool call information."""
        tool_calls = [
            {
                "iteration": 0,
                "tool_call_id": "call_1",
                "tool": "search",
                "arguments": {"query": "Python"},
                "status": "success",
                "result": "Search results...",
            },
            {
                "iteration": 1,
                "tool_call_id": "call_2",
                "tool": "calculator",
                "arguments": {"expression": "2+2"},
                "status": "success",
                "result": "4",
            },
            {
                "iteration": 2,
                "tool_call_id": "call_3",
                "tool": "email",
                "arguments": {"to": "user@example.com"},
                "status": "rejected",
                "reason": "User denied approval",
            },
        ]

        result = AgentResult(
            output="Task completed",
            status="completed",
            iterations=3,
            tool_calls_count=3,
            tokens_used=500,
            messages=[],
            tool_calls=tool_calls,
        )

        assert len(result.tool_calls) == 3
        assert result.tool_calls[0]["status"] == "success"
        assert result.tool_calls[2]["status"] == "rejected"
        assert "reason" in result.tool_calls[2]


class TestAgentDataIntegration:
    """Test interactions between agent data structures."""

    def test_state_to_result_conversion(self):
        """Test converting AgentState data to AgentResult."""
        # Simulate agent execution
        state = AgentState(
            messages=[
                {"role": "user", "content": "Calculate 2+2"},
                {"role": "assistant", "content": "The answer is 4"},
            ],
            iteration=2,
            tool_calls_count=1,
            tokens_used=150,
            status="completed",
        )

        tool_calls = [
            {"iteration": 0, "tool": "calculator", "status": "success"}
        ]

        # Extract final output from messages
        final_output = ""
        for msg in reversed(state.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                final_output = msg["content"]
                break

        # Create result from state
        result = AgentResult(
            output=final_output,
            status=state.status,
            iterations=state.iteration,
            tool_calls_count=state.tool_calls_count,
            tokens_used=state.tokens_used,
            messages=state.messages,
            tool_calls=tool_calls,
        )

        assert result.output == "The answer is 4"
        assert result.status == "completed"
        assert result.iterations == 2
        assert result.tool_calls_count == 1

    def test_result_serialization_deserialization(self):
        """Test that result can be serialized and deserialized."""
        original_result = AgentResult(
            output="Test output",
            status="completed",
            iterations=5,
            tool_calls_count=3,
            tokens_used=750,
            messages=[{"role": "user", "content": "test"}],
            tool_calls=[{"iteration": 0, "tool": "search"}],
        )

        # Serialize to dict
        result_dict = original_result.to_dict()

        # Reconstruct from dict
        reconstructed_result = AgentResult(
            output=result_dict["output"],
            status=result_dict["status"],
            iterations=result_dict["iterations"],
            tool_calls_count=result_dict["tool_calls_count"],
            tokens_used=result_dict["tokens_used"],
            messages=result_dict["messages"],
            tool_calls=result_dict["tool_calls"],
        )

        assert reconstructed_result.output == original_result.output
        assert reconstructed_result.status == original_result.status
        assert reconstructed_result.iterations == original_result.iterations
        assert reconstructed_result.tool_calls_count == original_result.tool_calls_count
        assert reconstructed_result.tokens_used == original_result.tokens_used


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
