"""Unit tests for network data structures and primitives."""

import pytest
from flowforge.network import NetworkState, RouterContext, NetworkResult, Network, network
from flowforge.router import CodeRouter, code
from flowforge.agent_def import AgentDefinition, agent_def
from flowforge.tools import tool


# Test tools for agents
@tool(name="test_tool", description="Test tool")
def test_tool(x: str) -> str:
    return f"result: {x}"


@tool(name="another_tool", description="Another tool")
async def another_tool(y: int) -> dict:
    return {"value": y * 2}


class TestNetworkState:
    """Test NetworkState class for shared agent state."""

    def test_state_initialization_empty(self):
        """Test creating empty state."""
        state = NetworkState()
        assert state._data == {}
        assert state.to_dict() == {}

    def test_state_get_set(self):
        """Test getting and setting state values."""
        state = NetworkState()

        # Set values
        state.set("key1", "value1")
        state.set("key2", 42)
        state.set("key3", {"nested": "data"})

        # Get values
        assert state.get("key1") == "value1"
        assert state.get("key2") == 42
        assert state.get("key3") == {"nested": "data"}

    def test_state_get_default(self):
        """Test get with default value."""
        state = NetworkState()

        # Non-existent key returns default
        assert state.get("missing") is None
        assert state.get("missing", "default") == "default"
        assert state.get("missing", []) == []

    def test_state_get_nonexistent_no_default(self):
        """Test get non-existent key without default returns None."""
        state = NetworkState()
        assert state.get("nonexistent") is None

    def test_state_to_dict(self):
        """Test exporting state to dictionary."""
        state = NetworkState()
        state.set("a", 1)
        state.set("b", "two")
        state.set("c", [3, 4, 5])

        result = state.to_dict()

        assert isinstance(result, dict)
        assert result == {"a": 1, "b": "two", "c": [3, 4, 5]}

    def test_state_from_dict(self):
        """Test creating state from dictionary."""
        data = {
            "user_id": "123",
            "status": "active",
            "count": 42,
        }

        state = NetworkState.from_dict(data)

        assert state.get("user_id") == "123"
        assert state.get("status") == "active"
        assert state.get("count") == 42

    def test_state_from_dict_empty(self):
        """Test creating state from empty dict."""
        state = NetworkState.from_dict({})
        assert state.to_dict() == {}

    def test_state_mutation(self):
        """Test that state can be mutated."""
        state = NetworkState()
        state.set("counter", 0)

        # Update value
        state.set("counter", 1)
        assert state.get("counter") == 1

        state.set("counter", 2)
        assert state.get("counter") == 2

    def test_state_complex_values(self):
        """Test storing complex values in state."""
        state = NetworkState()

        complex_data = {
            "list": [1, 2, 3],
            "dict": {"nested": {"deep": "value"}},
            "tuple": (4, 5, 6),
            "mixed": [{"a": 1}, {"b": 2}],
        }

        state.set("complex", complex_data)

        retrieved = state.get("complex")
        assert retrieved == complex_data
        assert retrieved["dict"]["nested"]["deep"] == "value"

    def test_state_to_dict_returns_copy(self):
        """Test that to_dict returns a copy, not reference."""
        state = NetworkState()
        state.set("key", "value")

        dict1 = state.to_dict()
        dict2 = state.to_dict()

        # Modifying dict1 shouldn't affect dict2
        dict1["key"] = "modified"

        assert dict2["key"] == "value"
        assert state.get("key") == "value"


class TestRouterContext:
    """Test RouterContext dataclass."""

    def test_context_initialization(self):
        """Test creating RouterContext."""
        state = NetworkState()
        state.set("test", "value")

        agents = {
            "agent1": agent_def("agent1", "System 1", []),
            "agent2": agent_def("agent2", "System 2", []),
        }

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        ctx = RouterContext(
            last_result="previous result",
            state=state,
            iteration=3,
            history=history,
            agents=agents,
        )

        assert ctx.last_result == "previous result"
        assert ctx.state.get("test") == "value"
        assert ctx.iteration == 3
        assert len(ctx.history) == 2
        assert len(ctx.agents) == 2
        assert "agent1" in ctx.agents

    def test_context_with_none_last_result(self):
        """Test context with None as last result (first iteration)."""
        ctx = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents={},
        )

        assert ctx.last_result is None
        assert ctx.iteration == 0
        assert ctx.history == []

    def test_context_agents_lookup(self):
        """Test looking up agents from context."""
        agent1 = agent_def("classifier", "Classify", [])
        agent2 = agent_def("processor", "Process", [])

        ctx = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents={"classifier": agent1, "processor": agent2},
        )

        assert ctx.agents["classifier"] is agent1
        assert ctx.agents["processor"] is agent2
        assert ctx.agents.get("nonexistent") is None


class TestNetworkResult:
    """Test NetworkResult dataclass."""

    def test_result_initialization(self):
        """Test creating NetworkResult."""
        agent_calls = [
            {
                "iteration": 0,
                "agent": "classifier",
                "status": "completed",
                "output": "Category: technical",
                "tool_calls_count": 1,
                "tokens_used": 150,
            }
        ]

        result = NetworkResult(
            output="Final answer",
            status="completed",
            iterations=3,
            agent_calls=agent_calls,
            state={"category": "technical"},
            total_tokens=500,
            total_cost_usd=0.015,
        )

        assert result.output == "Final answer"
        assert result.status == "completed"
        assert result.iterations == 3
        assert len(result.agent_calls) == 1
        assert result.state["category"] == "technical"
        assert result.total_tokens == 500
        assert result.total_cost_usd == 0.015

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = NetworkResult(
            output="Success",
            status="completed",
            iterations=2,
            agent_calls=[{"agent": "test"}],
            state={"key": "value"},
            total_tokens=100,
            total_cost_usd=0.003,
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["output"] == "Success"
        assert result_dict["status"] == "completed"
        assert result_dict["iterations"] == 2
        assert len(result_dict["agent_calls"]) == 1
        assert result_dict["state"]["key"] == "value"
        assert result_dict["total_tokens"] == 100
        assert result_dict["total_cost_usd"] == 0.003

    def test_result_to_dict_all_fields(self):
        """Test that to_dict includes all fields."""
        result = NetworkResult(
            output="Test",
            status="max_iterations",
            iterations=10,
            agent_calls=[],
            state={},
            total_tokens=1000,
            total_cost_usd=0.05,
        )

        result_dict = result.to_dict()

        required_keys = [
            "output",
            "status",
            "iterations",
            "agent_calls",
            "state",
            "total_tokens",
            "total_cost_usd",
        ]

        for key in required_keys:
            assert key in result_dict

    def test_result_status_values(self):
        """Test different result status values."""
        statuses = ["completed", "max_iterations", "failed", "handoff_failed"]

        for status in statuses:
            result = NetworkResult(
                output="Test",
                status=status,
                iterations=1,
                agent_calls=[],
                state={},
                total_tokens=50,
                total_cost_usd=0.001,
            )
            assert result.status == status

    def test_result_with_multiple_agent_calls(self):
        """Test result with multiple agent executions."""
        agent_calls = [
            {"iteration": 0, "agent": "classifier", "tokens_used": 100},
            {"iteration": 1, "agent": "processor", "tokens_used": 200},
            {"iteration": 2, "agent": "writer", "tokens_used": 300},
        ]

        result = NetworkResult(
            output="Final output",
            status="completed",
            iterations=3,
            agent_calls=agent_calls,
            state={},
            total_tokens=600,
            total_cost_usd=0.018,
        )

        assert len(result.agent_calls) == 3
        assert result.agent_calls[0]["agent"] == "classifier"
        assert result.agent_calls[1]["agent"] == "processor"
        assert result.agent_calls[2]["agent"] == "writer"

    def test_result_empty_state(self):
        """Test result with empty state."""
        result = NetworkResult(
            output="Done",
            status="completed",
            iterations=1,
            agent_calls=[],
            state={},
            total_tokens=50,
            total_cost_usd=0.001,
        )

        assert result.state == {}
        assert result.to_dict()["state"] == {}


class TestNetworkClass:
    """Test Network class."""

    def test_network_initialization(self):
        """Test creating a Network instance."""
        agent1 = agent_def("agent1", "System 1", [test_tool])
        agent2 = agent_def("agent2", "System 2", [another_tool])

        def router_fn(ctx):
            return None

        router = code(router_fn)

        net = Network(
            name="test-network",
            agents=[agent1, agent2],
            router=router,
            default_model="gpt-5",
        )

        assert net.name == "test-network"
        assert len(net.agents) == 2
        assert "agent1" in net.agents
        assert "agent2" in net.agents
        assert net.router is router
        assert net.default_model == "gpt-5"
        assert isinstance(net.state, NetworkState)

    def test_network_agents_dict(self):
        """Test that agents are stored as dict keyed by name."""
        agent1 = agent_def("classifier", "Classify", [])
        agent2 = agent_def("processor", "Process", [])

        net = Network(
            name="test",
            agents=[agent1, agent2],
            router=code(lambda ctx: None),
        )

        assert isinstance(net.agents, dict)
        assert net.agents["classifier"] is agent1
        assert net.agents["processor"] is agent2

    def test_network_default_model(self):
        """Test default model setting."""
        net = Network(
            name="test",
            agents=[],
            router=code(lambda ctx: None),
            default_model="claude-sonnet-4-6",
        )

        assert net.default_model == "claude-sonnet-4-6"

    def test_network_default_system(self):
        """Test default system prompt."""
        net = Network(
            name="test",
            agents=[],
            router=code(lambda ctx: None),
            default_system="You are a helpful assistant",
        )

        assert net.default_system == "You are a helpful assistant"

    def test_network_state_initialization(self):
        """Test that network has initialized state."""
        net = Network(
            name="test",
            agents=[],
            router=code(lambda ctx: None),
        )

        assert isinstance(net.state, NetworkState)
        assert net.state.to_dict() == {}


class TestNetworkFactory:
    """Test network factory function."""

    def test_factory_creates_network(self):
        """Test that factory function creates Network instance."""
        agent1 = agent_def("agent1", "System 1", [])

        net = network(
            name="test-network",
            agents=[agent1],
            router=code(lambda ctx: None),
        )

        assert isinstance(net, Network)
        assert net.name == "test-network"

    def test_factory_with_all_parameters(self):
        """Test factory with all parameters."""
        agent1 = agent_def("agent1", "System 1", [])
        agent2 = agent_def("agent2", "System 2", [])

        def my_router(ctx):
            return ctx.agents.get("agent1")

        net = network(
            name="full-network",
            agents=[agent1, agent2],
            router=code(my_router),
            default_model="gpt-5-mini",
        )

        assert net.name == "full-network"
        assert len(net.agents) == 2
        assert net.default_model == "gpt-5-mini"
        assert isinstance(net.router, CodeRouter)

    def test_factory_minimal_parameters(self):
        """Test factory with minimal parameters."""
        agent1 = agent_def("agent1", "System 1", [])

        net = network(
            name="minimal",
            agents=[agent1],
            router=code(lambda ctx: None),
        )

        assert net.name == "minimal"
        assert net.default_model == "claude-sonnet-4-6"  # default


class TestNetworkIntegration:
    """Test interactions between network components."""

    def test_network_with_agents_and_state(self):
        """Test full network setup with agents and state."""
        classifier = agent_def(
            name="classifier",
            system="Classify input",
            tools=[test_tool],
        )

        processor = agent_def(
            name="processor",
            system="Process classified input",
            tools=[another_tool],
        )

        def router_fn(ctx):
            if ctx.iteration == 0:
                return ctx.agents["classifier"]
            elif ctx.state.get("classified"):
                return ctx.agents["processor"]
            return None

        net = network(
            name="classification-network",
            agents=[classifier, processor],
            router=code(router_fn),
        )

        # Test network setup
        assert len(net.agents) == 2
        assert "classifier" in net.agents
        assert "processor" in net.agents

        # Test state
        net.state.set("classified", True)
        assert net.state.get("classified") is True

    def test_router_context_with_network_agents(self):
        """Test creating RouterContext with network's agents."""
        agent1 = agent_def("agent1", "System 1", [])
        agent2 = agent_def("agent2", "System 2", [])

        net = network(
            name="test",
            agents=[agent1, agent2],
            router=code(lambda ctx: None),
        )

        # Create context using network's agents
        ctx = RouterContext(
            last_result=None,
            state=net.state,
            iteration=0,
            history=[],
            agents=net.agents,
        )

        assert len(ctx.agents) == 2
        assert ctx.agents["agent1"] is agent1
        assert ctx.agents["agent2"] is agent2

    def test_network_result_serialization_roundtrip(self):
        """Test serializing and deserializing NetworkResult."""
        original_result = NetworkResult(
            output="Final result",
            status="completed",
            iterations=5,
            agent_calls=[
                {"iteration": 0, "agent": "test", "tokens_used": 100}
            ],
            state={"key": "value"},
            total_tokens=500,
            total_cost_usd=0.015,
        )

        # Serialize to dict
        result_dict = original_result.to_dict()

        # Reconstruct from dict
        reconstructed = NetworkResult(
            output=result_dict["output"],
            status=result_dict["status"],
            iterations=result_dict["iterations"],
            agent_calls=result_dict["agent_calls"],
            state=result_dict["state"],
            total_tokens=result_dict["total_tokens"],
            total_cost_usd=result_dict["total_cost_usd"],
        )

        assert reconstructed.output == original_result.output
        assert reconstructed.status == original_result.status
        assert reconstructed.iterations == original_result.iterations
        assert reconstructed.total_tokens == original_result.total_tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
