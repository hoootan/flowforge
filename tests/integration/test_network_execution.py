"""Integration tests for step.network() execution."""

from unittest.mock import AsyncMock, patch

import pytest
from flowforge.agent import AgentResult
from flowforge.agent_def import agent_def
from flowforge.exceptions import StepCompleted
from flowforge.network import Network, NetworkResult
from flowforge.router import code
from flowforge.steps import StepManager
from flowforge.tools import tool


# Test tools
@tool(name="classify", description="Classify input")
async def classify_tool(text: str) -> dict:
    """Classify input text."""
    if "technical" in text.lower():
        return {"category": "technical", "confidence": 0.9}
    elif "billing" in text.lower():
        return {"category": "billing", "confidence": 0.85}
    return {"category": "general", "confidence": 0.5}


@tool(name="process", description="Process data")
async def process_tool(data: dict) -> dict:
    """Process data."""
    return {"status": "processed", "data": data}


@tool(name="handoff", description="Handoff to another agent")
async def handoff_tool(agent_name: str, reason: str) -> dict:
    """Handoff to another agent."""
    return {"__handoff__": agent_name, "reason": reason}


class TestNetworkExecution:
    """Test basic network execution with code router."""

    @pytest.mark.asyncio
    async def test_network_execution_single_agent(self):
        """Test network executing a single agent."""
        agent1 = agent_def("agent1", "You are agent 1", [])

        def router_fn(ctx):
            if ctx.iteration == 0:
                return "agent1"
            return None

        net = Network(
            name="test-net",
            agents=[agent1],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        # Mock step.agent to return a result
        mock_agent_result = AgentResult(
            output="Agent 1 result",
            status="completed",
            iterations=1,
            tool_calls_count=0,
            tokens_used=100,
            messages=[{"role": "assistant", "content": "Agent 1 result"}],
        )

        with patch.object(step_manager, "agent", new=AsyncMock(return_value=mock_agent_result)):
            # Execute network
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Test input",
                )
            except StepCompleted as e:
                # Network execution raises StepCompleted
                result_dict = e.result
                result = NetworkResult(
                    output=result_dict["output"],
                    status=result_dict["status"],
                    iterations=result_dict["iterations"],
                    agent_calls=result_dict["agent_calls"],
                    state=result_dict["state"],
                    total_tokens=result_dict["total_tokens"],
                    total_cost_usd=result_dict["total_cost_usd"],
                )

                assert result.output == "Agent 1 result"
                assert result.status == "completed"
                assert result.iterations == 1
                assert len(result.agent_calls) == 1

    @pytest.mark.asyncio
    async def test_network_execution_multiple_agents(self):
        """Test network executing multiple agents in sequence."""
        agent1 = agent_def("classifier", "Classify input", [classify_tool])
        agent2 = agent_def("processor", "Process classified input", [process_tool])

        def router_fn(ctx):
            if ctx.iteration == 0:
                return "classifier"
            elif ctx.iteration == 1:
                return "processor"
            return None

        net = Network(
            name="multi-agent-net",
            agents=[agent1, agent2],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        # Mock agent results
        classifier_result = AgentResult(
            output="Classification: technical",
            status="completed",
            iterations=1,
            tool_calls_count=1,
            tokens_used=150,
            messages=[],
        )

        processor_result = AgentResult(
            output="Processing complete",
            status="completed",
            iterations=1,
            tool_calls_count=1,
            tokens_used=200,
            messages=[],
        )

        mock_results = [classifier_result, processor_result]
        mock_agent = AsyncMock(side_effect=mock_results)

        with patch.object(step_manager, "agent", new=mock_agent):
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Technical issue",
                )
            except StepCompleted as e:
                result_dict = e.result
                result = NetworkResult(**result_dict)

                assert result.iterations == 2
                assert len(result.agent_calls) == 2
                assert result.agent_calls[0]["agent"] == "classifier"
                assert result.agent_calls[1]["agent"] == "processor"
                assert result.total_tokens == 350  # 150 + 200

    @pytest.mark.asyncio
    async def test_network_stops_when_router_returns_none(self):
        """Test network execution stops when router returns None."""
        agent1 = agent_def("agent1", "Agent 1", [])

        def router_fn(ctx):
            # Only execute once
            if ctx.iteration == 0:
                return "agent1"
            return None  # Stop after first agent

        net = Network(
            name="stop-net",
            agents=[agent1],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        mock_result = AgentResult(
            output="Done",
            status="completed",
            iterations=1,
            tool_calls_count=0,
            tokens_used=50,
            messages=[],
        )

        with patch.object(step_manager, "agent", new=AsyncMock(return_value=mock_result)):
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Test",
                )
            except StepCompleted as e:
                result_dict = e.result
                result = NetworkResult(**result_dict)

                assert result.status == "completed"
                assert result.iterations == 1  # Only one iteration
                assert len(result.agent_calls) == 1


class TestNetworkMaxIterations:
    """Test network respecting max_iterations limit."""

    @pytest.mark.asyncio
    async def test_network_respects_max_iterations(self):
        """Test network stops at max_iterations."""
        agent1 = agent_def("agent1", "Agent 1", [])

        def router_fn(ctx):
            # Always return agent1 (would loop forever)
            return "agent1"

        net = Network(
            name="loop-net",
            agents=[agent1],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        mock_result = AgentResult(
            output="Result",
            status="completed",
            iterations=1,
            tool_calls_count=0,
            tokens_used=50,
            messages=[],
        )

        with patch.object(step_manager, "agent", new=AsyncMock(return_value=mock_result)):
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Test",
                    max_iterations=3,  # Limit to 3 iterations
                )
            except StepCompleted as e:
                result_dict = e.result
                result = NetworkResult(**result_dict)

                assert result.status == "max_iterations"
                assert result.iterations == 3  # Hit the limit
                assert len(result.agent_calls) == 3

    @pytest.mark.asyncio
    async def test_network_completes_before_max_iterations(self):
        """Test network completing before reaching max_iterations."""
        agent1 = agent_def("agent1", "Agent 1", [])

        def router_fn(ctx):
            if ctx.iteration < 2:
                return "agent1"
            return None  # Complete after 2 iterations

        net = Network(
            name="complete-net",
            agents=[agent1],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        mock_result = AgentResult(
            output="Done",
            status="completed",
            iterations=1,
            tool_calls_count=0,
            tokens_used=50,
            messages=[],
        )

        with patch.object(step_manager, "agent", new=AsyncMock(return_value=mock_result)):
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Test",
                    max_iterations=10,  # High limit
                )
            except StepCompleted as e:
                result_dict = e.result
                result = NetworkResult(**result_dict)

                assert result.status == "completed"  # Not max_iterations
                assert result.iterations == 2  # Completed after 2


class TestNetworkHandoffDetection:
    """Test handoff detection in tool results."""

    @pytest.mark.asyncio
    async def test_handoff_detection(self):
        """Test network detects handoff in tool results."""
        agent1 = agent_def("agent1", "Agent 1", [handoff_tool])
        agent2 = agent_def("agent2", "Agent 2", [])

        def router_fn(ctx):
            if ctx.iteration == 0:
                return "agent1"
            # Handoff detection should override this
            return None

        net = Network(
            name="handoff-net",
            agents=[agent1, agent2],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        # First agent returns handoff
        agent1_result = AgentResult(
            output="Handing off to agent2",
            status="completed",
            iterations=1,
            tool_calls_count=1,
            tokens_used=100,
            messages=[],
            tool_calls=[
                {
                    "iteration": 0,
                    "tool": "handoff",
                    "status": "success",
                    "result": '{"__handoff__": "agent2", "reason": "Needs specialist"}',
                }
            ],
        )

        agent2_result = AgentResult(
            output="Agent2 handled it",
            status="completed",
            iterations=1,
            tool_calls_count=0,
            tokens_used=50,
            messages=[],
        )

        mock_agent = AsyncMock(side_effect=[agent1_result, agent2_result])

        with patch.object(step_manager, "agent", new=mock_agent):
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Test",
                )
            except StepCompleted as e:
                result_dict = e.result
                result = NetworkResult(**result_dict)

                # Should have executed both agents due to handoff
                assert result.iterations == 2
                assert len(result.agent_calls) == 2
                assert result.agent_calls[0]["agent"] == "agent1"
                assert result.agent_calls[1]["agent"] == "agent2"


class TestNetworkStatePersistence:
    """Test state persistence across agents."""

    @pytest.mark.asyncio
    async def test_state_persists_across_agents(self):
        """Test that network state persists across agent calls."""
        agent1 = agent_def("agent1", "Agent 1", [])
        agent2 = agent_def("agent2", "Agent 2", [])

        def router_fn(ctx):
            if ctx.iteration == 0:
                return "agent1"
            elif ctx.iteration == 1:
                # Check that state from agent1 is available
                assert ctx.state.get("agent1_ran") is True
                return "agent2"
            return None

        net = Network(
            name="state-net",
            agents=[agent1, agent2],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        async def mock_agent_execution(step_id, **kwargs):
            # Simulate agents setting state
            if "agent1" in step_id:
                net.state.set("agent1_ran", True)
                return AgentResult(
                    output="Agent 1 done",
                    status="completed",
                    iterations=1,
                    tool_calls_count=0,
                    tokens_used=50,
                    messages=[],
                )
            elif "agent2" in step_id:
                # Agent2 should see agent1's state
                assert net.state.get("agent1_ran") is True
                net.state.set("agent2_ran", True)
                return AgentResult(
                    output="Agent 2 done",
                    status="completed",
                    iterations=1,
                    tool_calls_count=0,
                    tokens_used=50,
                    messages=[],
                )

        with patch.object(step_manager, "agent", new=mock_agent_execution):
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Test",
                )
            except StepCompleted as e:
                result_dict = e.result
                result = NetworkResult(**result_dict)

                # Both agents should have run
                assert result.iterations == 2
                # State should contain both values
                assert result.state.get("agent1_ran") is True
                assert result.state.get("agent2_ran") is True

    @pytest.mark.asyncio
    async def test_initial_state_provided(self):
        """Test providing initial state to network."""
        agent1 = agent_def("agent1", "Agent 1", [])

        def router_fn(ctx):
            # Router can access initial state
            if ctx.iteration == 0 and ctx.state.get("user_id"):
                return "agent1"
            return None

        net = Network(
            name="init-state-net",
            agents=[agent1],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        mock_result = AgentResult(
            output="Done",
            status="completed",
            iterations=1,
            tool_calls_count=0,
            tokens_used=50,
            messages=[],
        )

        with patch.object(step_manager, "agent", new=AsyncMock(return_value=mock_result)):
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Test",
                    initial_state={"user_id": "user123", "role": "admin"},
                )
            except StepCompleted as e:
                result_dict = e.result
                result = NetworkResult(**result_dict)

                # Initial state should be in final state
                assert result.state.get("user_id") == "user123"
                assert result.state.get("role") == "admin"


class TestNetworkMetricsTracking:
    """Test metrics tracking during network execution."""

    @pytest.mark.asyncio
    async def test_token_usage_tracking(self):
        """Test that token usage is tracked across agents."""
        agent1 = agent_def("agent1", "Agent 1", [])
        agent2 = agent_def("agent2", "Agent 2", [])

        def router_fn(ctx):
            if ctx.iteration < 2:
                return ["agent1", "agent2"][ctx.iteration]
            return None

        net = Network(
            name="metrics-net",
            agents=[agent1, agent2],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        agent1_result = AgentResult(
            output="Agent 1",
            status="completed",
            iterations=1,
            tool_calls_count=1,
            tokens_used=150,
            messages=[],
        )

        agent2_result = AgentResult(
            output="Agent 2",
            status="completed",
            iterations=1,
            tool_calls_count=2,
            tokens_used=250,
            messages=[],
        )

        mock_agent = AsyncMock(side_effect=[agent1_result, agent2_result])

        with patch.object(step_manager, "agent", new=mock_agent):
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Test",
                )
            except StepCompleted as e:
                result_dict = e.result
                result = NetworkResult(**result_dict)

                # Total tokens should be sum of both agents
                assert result.total_tokens == 400  # 150 + 250
                # Cost should be calculated (rough estimate)
                assert result.total_cost_usd > 0

    @pytest.mark.asyncio
    async def test_agent_call_tracking(self):
        """Test that all agent calls are tracked."""
        agent1 = agent_def("agent1", "Agent 1", [])

        def router_fn(ctx):
            if ctx.iteration < 3:
                return "agent1"
            return None

        net = Network(
            name="tracking-net",
            agents=[agent1],
            router=code(router_fn),
        )

        step_manager = StepManager(run_id="test-run", completed_steps={})

        mock_result = AgentResult(
            output="Result",
            status="completed",
            iterations=1,
            tool_calls_count=1,
            tokens_used=100,
            messages=[],
        )

        with patch.object(step_manager, "agent", new=AsyncMock(return_value=mock_result)):
            try:
                await step_manager.network(
                    "test-network",
                    network=net,
                    input="Test",
                )
            except StepCompleted as e:
                result_dict = e.result
                result = NetworkResult(**result_dict)

                # Should track all 3 agent calls
                assert len(result.agent_calls) == 3

                for i, call in enumerate(result.agent_calls):
                    assert call["iteration"] == i
                    assert call["agent"] == "agent1"
                    assert call["status"] == "completed"
                    assert call["tokens_used"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
