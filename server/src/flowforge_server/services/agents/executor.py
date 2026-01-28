"""Agent executor for running agent loops.

Provides AgentExecutor for executing agent definitions with
automatic tool calling, streaming, and approval flows.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, AsyncIterator

from .base import (
    AgentDefinition,
    AgentExecutionResult,
    AgentState,
    StepAction,
    StepContext,
    ToolDefinition,
)
from .conversation import ConversationManager

if TYPE_CHECKING:
    from flowforge_server.services.ai import AIService, ToolCall
    from flowforge_server.services.providers import ProviderRegistry
    from flowforge_server.services.streaming import (
        AnyStreamEvent,
        ApprovalRequiredEvent,
        IterationCompleteEvent,
        StreamCompleteEvent,
        ThinkingEvent,
        ToolCallEndEvent,
        ToolCallStartEvent,
    )


class AgentExecutor:
    """
    Executes an agent loop with automatic tool calling.

    Implements the Vercel AI SDK 6 pattern:
    1. LLM generates response (possibly with tool calls)
    2. If tool calls present, execute them (with optional approval)
    3. Feed results back to LLM
    4. Repeat until LLM stops calling tools or limits reached
    """

    def __init__(
        self,
        ai_service: AIService,
        provider_registry: ProviderRegistry | None = None,
        tool_executor: ToolExecutorProtocol | None = None,
    ) -> None:
        """
        Initialize the agent executor.

        Args:
            ai_service: AI service for making completions
            provider_registry: Provider registry for model resolution
            tool_executor: Optional custom tool executor
        """
        self.ai_service = ai_service
        self.provider_registry = provider_registry
        self.tool_executor = tool_executor or DefaultToolExecutor()

    async def execute(
        self,
        agent: AgentDefinition,
        task: str,
        conversation: ConversationManager | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> AgentExecutionResult:
        """
        Execute the agent loop.

        Args:
            agent: The agent definition to execute
            task: The user's task/prompt
            conversation: Optional existing conversation to continue
            initial_state: Initial state for the agent

        Returns:
            AgentExecutionResult with output and metadata
        """
        # Initialize conversation and state
        conv = conversation or ConversationManager()
        state = AgentState(custom=initial_state or agent.initial_state.copy())

        # Add system prompt and task
        if not conversation:
            if agent.system_prompt:
                conv.add_system_message(agent.system_prompt)
            conv.add_user_message(task)

        # Run agent loop
        final_content = ""
        start_time = time.time()

        while state.can_continue(agent):
            state.iteration += 1

            # Call prepare_step callback if provided
            if agent.prepare_step:
                context = self._build_step_context(state, conv)
                action = await agent.prepare_step(context)
                if action.action == "stop":
                    state.status = "stopped"
                    break

            # Call LLM
            try:
                response = await self.ai_service.complete(
                    model=agent.model,
                    messages=conv.to_messages(),
                    max_tokens=agent.max_tokens_per_step,
                    temperature=agent.temperature,
                    tools=agent.get_tool_schemas() if agent.tools else None,
                    tool_choice="auto" if agent.tools else None,
                )
            except Exception as e:
                state.status = "failed"
                return AgentExecutionResult(
                    output="",
                    status="failed",
                    iterations=state.iteration,
                    tool_calls_made=state.tool_calls_count,
                    tokens_used=state.tokens_used,
                    cost_usd=state.cost_usd,
                    messages=conv.to_messages(),
                    error=str(e),
                )

            # Update usage tracking
            state.tokens_used += response.usage.total_tokens
            state.cost_usd += response.usage.cost_usd

            # Check for tool calls
            if response.tool_calls:
                # Add assistant message with tool calls
                conv.add_assistant_message(
                    content=response.content,
                    tool_calls=[
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                )

                # Execute each tool call
                for tool_call in response.tool_calls:
                    state.tool_calls_count += 1

                    # Check if tool requires approval
                    if agent.tool_requires_approval(tool_call.name):
                        # For now, auto-approve (real implementation would wait)
                        pass

                    # Execute tool
                    tool_def = agent.get_tool(tool_call.name)
                    try:
                        result = await self.tool_executor.execute(
                            tool_def or ToolDefinition(
                                name=tool_call.name,
                                description="",
                                parameters={},
                            ),
                            tool_call.arguments,
                        )
                        result_str = str(result) if not isinstance(result, str) else result
                    except Exception as e:
                        result_str = f"Error: {str(e)}"

                    # Add tool result
                    conv.add_tool_result(
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                        result=result_str,
                    )

                    # Call tool execution callback
                    if agent.on_tool_execution:
                        await agent.on_tool_execution(
                            tool_call.name,
                            tool_call.arguments,
                            result_str,
                        )
            else:
                # No tool calls - agent is done
                final_content = response.content
                conv.add_assistant_message(content=final_content)
                state.status = "completed"
                break

            # Call step complete callback
            if agent.on_step_complete:
                context = self._build_step_context(state, conv)
                await agent.on_step_complete(context)

        # Determine final status
        if state.status == "running":
            if state.iteration >= agent.max_steps:
                state.status = "completed"
                status = "max_steps"
            elif state.tool_calls_count >= agent.max_tool_calls:
                state.status = "completed"
                status = "max_tool_calls"
            else:
                status = "completed"
        elif state.status == "stopped":
            status = "stopped"
        elif state.status == "failed":
            status = "failed"
        else:
            status = "completed"

        # Parse structured output if schema provided
        output: str | Any = final_content
        if agent.output_schema and final_content:
            try:
                output = agent.output_schema.model_validate_json(final_content)
            except Exception:
                pass

        return AgentExecutionResult(
            output=output,
            status=status,
            iterations=state.iteration,
            tool_calls_made=state.tool_calls_count,
            tokens_used=state.tokens_used,
            cost_usd=state.cost_usd,
            messages=conv.to_messages(),
        )

    async def execute_stream(
        self,
        agent: AgentDefinition,
        task: str,
        conversation: ConversationManager | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[AnyStreamEvent]:
        """
        Execute agent with streaming events.

        Yields events for:
        - thinking_start, thinking_chunk, thinking_end
        - tool_call_start, tool_call_end
        - approval_required, approval_resolved
        - iteration_complete
        - agent_complete
        """
        from flowforge_server.services.streaming import (
            IterationCompleteEvent,
            StreamCompleteEvent,
            ThinkingEvent,
            ToolCallEndEvent,
            ToolCallStartEvent,
        )

        # Initialize conversation and state
        conv = conversation or ConversationManager()
        state = AgentState(custom=initial_state or agent.initial_state.copy())

        # Add system prompt and task
        if not conversation:
            if agent.system_prompt:
                conv.add_system_message(agent.system_prompt)
            conv.add_user_message(task)

        # Run agent loop
        final_content = ""
        start_time = time.time()

        while state.can_continue(agent):
            state.iteration += 1

            # Yield thinking start
            yield ThinkingEvent(
                status="start",
                iteration=state.iteration,
            )

            # Stream LLM response
            accumulated_content = ""
            tool_calls: list[ToolCall] = []

            try:
                async for chunk in self.ai_service.complete_stream(
                    model=agent.model,
                    messages=conv.to_messages(),
                    max_tokens=agent.max_tokens_per_step,
                    temperature=agent.temperature,
                    tools=agent.get_tool_schemas() if agent.tools else None,
                    tool_choice="auto" if agent.tools else None,
                ):
                    if chunk["type"] == "content":
                        accumulated_content += chunk["chunk"]
                        yield ThinkingEvent(
                            status="chunk",
                            content=chunk["chunk"],
                            iteration=state.iteration,
                        )
                    elif chunk["type"] == "done":
                        state.tokens_used += chunk["usage"].total_tokens
                        state.cost_usd += chunk["usage"].cost_usd
                        tool_calls = chunk.get("tool_calls", [])

            except Exception as e:
                from flowforge_server.services.streaming import ErrorEvent
                yield ErrorEvent(
                    error_type=type(e).__name__,
                    message=str(e),
                    recoverable=False,
                )
                return

            # Yield thinking end
            yield ThinkingEvent(
                status="end",
                content=accumulated_content,
                iteration=state.iteration,
            )

            # Handle tool calls
            if tool_calls:
                conv.add_assistant_message(
                    content=accumulated_content,
                    tool_calls=[
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in tool_calls
                    ],
                )

                for tool_call in tool_calls:
                    state.tool_calls_count += 1

                    yield ToolCallStartEvent(
                        tool_name=tool_call.name,
                        tool_call_id=tool_call.id,
                        arguments=tool_call.arguments,
                    )

                    tool_start = time.time()
                    tool_def = agent.get_tool(tool_call.name)

                    try:
                        result = await self.tool_executor.execute(
                            tool_def or ToolDefinition(
                                name=tool_call.name,
                                description="",
                                parameters={},
                            ),
                            tool_call.arguments,
                        )
                        result_str = str(result) if not isinstance(result, str) else result
                        error = None
                    except Exception as e:
                        result_str = f"Error: {str(e)}"
                        error = str(e)

                    duration_ms = int((time.time() - tool_start) * 1000)

                    conv.add_tool_result(
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                        result=result_str,
                    )

                    yield ToolCallEndEvent(
                        tool_name=tool_call.name,
                        tool_call_id=tool_call.id,
                        result=result_str[:500],  # Truncate for event
                        error=error,
                        duration_ms=duration_ms,
                    )

                yield IterationCompleteEvent(
                    iteration=state.iteration,
                    tool_calls_made=len(tool_calls),
                    tokens_used=state.tokens_used,
                    has_more=state.can_continue(agent),
                )
            else:
                # No tool calls - done
                final_content = accumulated_content
                conv.add_assistant_message(content=final_content)
                state.status = "completed"
                break

        # Determine final status
        if state.iteration >= agent.max_steps:
            status = "max_steps"
        elif state.tool_calls_count >= agent.max_tool_calls:
            status = "max_tool_calls"
        else:
            status = "completed"

        yield StreamCompleteEvent(
            content=final_content,
            usage={
                "total_tokens": state.tokens_used,
                "cost_usd": state.cost_usd,
            },
            finish_reason=status,
            total_iterations=state.iteration,
            total_tool_calls=state.tool_calls_count,
        )

    def _build_step_context(
        self,
        state: AgentState,
        conv: ConversationManager,
    ) -> StepContext:
        """Build step context from current state."""
        return StepContext(
            iteration=state.iteration,
            messages=conv.to_messages(),
            pending_tool_calls=[],
            state=state.custom,
            tokens_used=state.tokens_used,
            cost_usd=state.cost_usd,
        )


class ToolExecutorProtocol:
    """Protocol for tool execution."""

    async def execute(
        self,
        tool: ToolDefinition,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a tool with given arguments."""
        ...


class DefaultToolExecutor(ToolExecutorProtocol):
    """Default tool executor that handles code-based tools."""

    async def execute(
        self,
        tool: ToolDefinition,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a tool with given arguments."""
        if tool.code:
            return await self._execute_code_tool(tool.code, arguments)
        return {"error": f"Tool '{tool.name}' has no implementation"}

    async def _execute_code_tool(
        self,
        code: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a code-based tool."""
        import asyncio

        namespace: dict[str, Any] = {}

        try:
            exec(code, namespace)
            execute_fn = namespace.get("execute")

            if not execute_fn:
                return {"error": "Tool code must define an 'execute' function"}

            if asyncio.iscoroutinefunction(execute_fn):
                return await execute_fn(**arguments)
            else:
                return execute_fn(**arguments)

        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
