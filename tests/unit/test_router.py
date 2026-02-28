"""Unit tests for router implementations."""

import pytest
from flowforge.agent_def import agent_def
from flowforge.network import NetworkState, RouterContext
from flowforge.router import CodeRouter, LLMRouter, code, llm

# Sample agents for testing
agent1 = agent_def("agent1", "System 1", [])
agent2 = agent_def("agent2", "System 2", [])
agent3 = agent_def("agent3", "System 3", [])


class TestCodeRouter:
    """Test CodeRouter implementation."""

    @pytest.mark.asyncio
    async def test_router_with_agent_instance(self):
        """Test router returning AgentDefinition instance."""

        def router_fn(ctx):
            return ctx.agents["agent1"]

        router = CodeRouter(router_fn)

        ctx = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents={"agent1": agent1, "agent2": agent2},
        )

        result = await router.route(ctx)
        assert result is agent1

    @pytest.mark.asyncio
    async def test_router_with_agent_name_string(self):
        """Test router returning agent name as string."""

        def router_fn(ctx):
            return "agent2"  # Return string name

        router = CodeRouter(router_fn)

        ctx = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents={"agent1": agent1, "agent2": agent2},
        )

        result = await router.route(ctx)
        assert result is agent2  # Should resolve to agent instance

    @pytest.mark.asyncio
    async def test_router_with_none(self):
        """Test router returning None to end network."""

        def router_fn(ctx):
            return None

        router = CodeRouter(router_fn)

        ctx = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents={"agent1": agent1},
        )

        result = await router.route(ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_router_with_unknown_agent_name(self):
        """Test router returning unknown agent name raises error."""

        def router_fn(ctx):
            return "nonexistent_agent"

        router = CodeRouter(router_fn)

        ctx = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents={"agent1": agent1},
        )

        with pytest.raises(ValueError, match="unknown agent"):
            await router.route(ctx)

    @pytest.mark.asyncio
    async def test_router_with_conditional_logic(self):
        """Test router with conditional logic based on iteration."""

        def router_fn(ctx):
            if ctx.iteration == 0:
                return "agent1"
            elif ctx.iteration == 1:
                return "agent2"
            else:
                return None

        router = CodeRouter(router_fn)

        agents = {"agent1": agent1, "agent2": agent2}

        # Iteration 0
        ctx0 = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents=agents,
        )
        result0 = await router.route(ctx0)
        assert result0 is agent1

        # Iteration 1
        ctx1 = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=1,
            history=[],
            agents=agents,
        )
        result1 = await router.route(ctx1)
        assert result1 is agent2

        # Iteration 2
        ctx2 = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=2,
            history=[],
            agents=agents,
        )
        result2 = await router.route(ctx2)
        assert result2 is None

    @pytest.mark.asyncio
    async def test_router_with_state_based_routing(self):
        """Test router making decisions based on state."""

        def router_fn(ctx):
            category = ctx.state.get("category")

            if category == "technical":
                return "agent1"
            elif category == "billing":
                return "agent2"
            else:
                return None

        router = CodeRouter(router_fn)

        agents = {"agent1": agent1, "agent2": agent2}

        # Technical category
        state_tech = NetworkState()
        state_tech.set("category", "technical")
        ctx_tech = RouterContext(
            last_result=None,
            state=state_tech,
            iteration=1,
            history=[],
            agents=agents,
        )
        result_tech = await router.route(ctx_tech)
        assert result_tech is agent1

        # Billing category
        state_billing = NetworkState()
        state_billing.set("category", "billing")
        ctx_billing = RouterContext(
            last_result=None,
            state=state_billing,
            iteration=1,
            history=[],
            agents=agents,
        )
        result_billing = await router.route(ctx_billing)
        assert result_billing is agent2

        # Unknown category
        state_unknown = NetworkState()
        state_unknown.set("category", "unknown")
        ctx_unknown = RouterContext(
            last_result=None,
            state=state_unknown,
            iteration=1,
            history=[],
            agents=agents,
        )
        result_unknown = await router.route(ctx_unknown)
        assert result_unknown is None

    @pytest.mark.asyncio
    async def test_router_with_last_result(self):
        """Test router accessing last agent result."""

        class MockResult:
            def __init__(self, output):
                self.output = output

        def router_fn(ctx):
            if ctx.last_result and "success" in ctx.last_result.output.lower():
                return None  # Complete
            return "agent1"  # Continue

        router = CodeRouter(router_fn)

        agents = {"agent1": agent1}

        # No last result
        ctx_no_result = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents=agents,
        )
        result_no_result = await router.route(ctx_no_result)
        assert result_no_result is agent1

        # Last result indicates success
        ctx_success = RouterContext(
            last_result=MockResult("Task completed successfully"),
            state=NetworkState(),
            iteration=1,
            history=[],
            agents=agents,
        )
        result_success = await router.route(ctx_success)
        assert result_success is None

    @pytest.mark.asyncio
    async def test_async_router_function(self):
        """Test router with async function."""

        async def async_router_fn(ctx):
            # Simulate async work
            return "agent1"

        router = CodeRouter(async_router_fn)

        ctx = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents={"agent1": agent1},
        )

        result = await router.route(ctx)
        assert result is agent1

    @pytest.mark.asyncio
    async def test_async_router_returning_none(self):
        """Test async router returning None."""

        async def async_router_fn(ctx):
            return None

        router = CodeRouter(async_router_fn)

        ctx = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents={},
        )

        result = await router.route(ctx)
        assert result is None


class TestLLMRouter:
    """Test LLMRouter configuration and initialization."""

    def test_llm_router_initialization_defaults(self):
        """Test LLM router with default parameters."""
        router = LLMRouter()

        assert router.model == "gpt-5-mini"
        assert router.temperature == 0.3
        assert router.prompt is not None

    def test_llm_router_initialization_custom(self):
        """Test LLM router with custom parameters."""
        custom_prompt = "Select the best agent: {agents}"

        router = LLMRouter(
            model="gpt-5",
            prompt=custom_prompt,
            temperature=0.5,
        )

        assert router.model == "gpt-5"
        assert router.prompt == custom_prompt
        assert router.temperature == 0.5

    def test_llm_router_default_prompt(self):
        """Test that default prompt is generated."""
        router = LLMRouter()

        assert "routing agent" in router.prompt.lower()
        assert "{agents}" in router.prompt
        assert "{state}" in router.prompt
        assert "{last_result}" in router.prompt

    def test_llm_router_custom_prompt_override(self):
        """Test custom prompt overrides default."""
        custom = "Custom routing prompt"
        router = LLMRouter(prompt=custom)

        assert router.prompt == custom

    @pytest.mark.asyncio
    async def test_llm_router_route_not_implemented(self):
        """Test that LLM router route raises NotImplementedError."""
        router = LLMRouter()

        ctx = RouterContext(
            last_result=None,
            state=NetworkState(),
            iteration=0,
            history=[],
            agents={},
        )

        # LLM routing is handled by step.network() orchestrator
        with pytest.raises(NotImplementedError):
            await router.route(ctx)


class TestRouterFactoryFunctions:
    """Test router factory functions."""

    def test_code_factory_creates_code_router(self):
        """Test code() factory creates CodeRouter."""

        def router_fn(ctx):
            return None

        router = code(router_fn)

        assert isinstance(router, CodeRouter)
        assert router.fn is router_fn

    def test_code_factory_with_lambda(self):
        """Test code() factory with lambda function."""
        router = code(lambda ctx: ctx.agents.get("agent1"))

        assert isinstance(router, CodeRouter)
        assert callable(router.fn)

    def test_llm_factory_creates_llm_router(self):
        """Test llm() factory creates LLMRouter."""
        router = llm()

        assert isinstance(router, LLMRouter)
        assert router.model == "gpt-5-mini"

    def test_llm_factory_with_custom_parameters(self):
        """Test llm() factory with custom parameters."""
        router = llm(
            model="gpt-5",
            prompt="Custom prompt",
            temperature=0.7,
        )

        assert isinstance(router, LLMRouter)
        assert router.model == "gpt-5"
        assert router.prompt == "Custom prompt"
        assert router.temperature == 0.7

    def test_llm_factory_default_parameters(self):
        """Test llm() factory with defaults."""
        router = llm()

        assert router.model == "gpt-5-mini"
        assert router.temperature == 0.3
        assert router.prompt is not None


class TestRouterIntegration:
    """Test routers in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_multi_stage_routing(self):
        """Test router handling multi-stage workflow."""

        def multi_stage_router(ctx):
            # Stage 1: Classification
            if ctx.iteration == 0:
                return "agent1"

            # Stage 2: Processing
            if ctx.iteration == 1 and ctx.state.get("classified"):
                return "agent2"

            # Stage 3: Finalization
            if ctx.iteration == 2 and ctx.state.get("processed"):
                return "agent3"

            # Complete
            return None

        router = code(multi_stage_router)

        agents = {"agent1": agent1, "agent2": agent2, "agent3": agent3}

        # Stage 1
        state1 = NetworkState()
        ctx1 = RouterContext(
            last_result=None,
            state=state1,
            iteration=0,
            history=[],
            agents=agents,
        )
        result1 = await router.route(ctx1)
        assert result1 is agent1

        # Stage 2
        state2 = NetworkState()
        state2.set("classified", True)
        ctx2 = RouterContext(
            last_result=None,
            state=state2,
            iteration=1,
            history=[],
            agents=agents,
        )
        result2 = await router.route(ctx2)
        assert result2 is agent2

        # Stage 3
        state3 = NetworkState()
        state3.set("classified", True)
        state3.set("processed", True)
        ctx3 = RouterContext(
            last_result=None,
            state=state3,
            iteration=2,
            history=[],
            agents=agents,
        )
        result3 = await router.route(ctx3)
        assert result3 is agent3

    @pytest.mark.asyncio
    async def test_router_with_completion_check(self):
        """Test router checking completion state."""

        def completion_router(ctx):
            # Check if work is complete
            if ctx.state.get("resolved"):
                return None

            # Check if escalated
            if ctx.state.get("escalated"):
                return "agent2"

            # Default to agent1
            return "agent1"

        router = code(completion_router)

        agents = {"agent1": agent1, "agent2": agent2}

        # Not resolved, not escalated -> agent1
        state_default = NetworkState()
        ctx_default = RouterContext(
            last_result=None,
            state=state_default,
            iteration=0,
            history=[],
            agents=agents,
        )
        result_default = await router.route(ctx_default)
        assert result_default is agent1

        # Escalated -> agent2
        state_escalated = NetworkState()
        state_escalated.set("escalated", True)
        ctx_escalated = RouterContext(
            last_result=None,
            state=state_escalated,
            iteration=1,
            history=[],
            agents=agents,
        )
        result_escalated = await router.route(ctx_escalated)
        assert result_escalated is agent2

        # Resolved -> None (complete)
        state_resolved = NetworkState()
        state_resolved.set("resolved", True)
        ctx_resolved = RouterContext(
            last_result=None,
            state=state_resolved,
            iteration=2,
            history=[],
            agents=agents,
        )
        result_resolved = await router.route(ctx_resolved)
        assert result_resolved is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
