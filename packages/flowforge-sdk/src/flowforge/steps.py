"""Step primitives for durable workflow execution."""

import hashlib
import json
import os
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

from flowforge.agent import AgentResult, AgentState
from flowforge.agent_def import AgentDefinition
from flowforge.exceptions import RateLimited, StepCompleted, StepFailed
from flowforge.network import Network, NetworkResult, NetworkState, RouterContext
from flowforge.router import LLMRouter
from flowforge.tools import SubAgentConfig, Tool

T = TypeVar("T")

# Defaults for LLM-call retry on rate-limit. See _resolve_num_retries /
# _retry_sleep below.
_DEFAULT_LLM_NUM_RETRIES = 5
_DEFAULT_LLM_MAX_RETRY_DELAY = 120.0
_RETRY_JITTER_RANGE = (0.8, 1.2)


def _resolve_num_retries(explicit: int | None) -> int:
    """
    Determine the retry budget for an LLM call.

    Precedence: explicit kwarg > FLOWFORGE_LLM_NUM_RETRIES env >
    LITELLM_NUM_RETRIES env (back-compat) > default 5. Clamped to >= 0.
    """
    if explicit is not None:
        return max(0, int(explicit))
    for var in ("FLOWFORGE_LLM_NUM_RETRIES", "LITELLM_NUM_RETRIES"):
        raw = os.environ.get(var)
        if raw is None:
            continue
        try:
            return max(0, int(raw))
        except ValueError:
            continue
    return _DEFAULT_LLM_NUM_RETRIES


def _retry_sleep(retry_after: float) -> float:
    """Apply ±20% jitter and clamp to [1s, FLOWFORGE_LLM_MAX_RETRY_DELAY]."""
    try:
        max_delay = float(
            os.environ.get("FLOWFORGE_LLM_MAX_RETRY_DELAY", _DEFAULT_LLM_MAX_RETRY_DELAY)
        )
    except ValueError:
        max_delay = _DEFAULT_LLM_MAX_RETRY_DELAY
    base = max(0.0, float(retry_after))
    jittered = base * random.uniform(*_RETRY_JITTER_RANGE)
    return max(1.0, min(jittered, max_delay))


def _parse_duration(duration: str | timedelta) -> float:
    """Parse a duration string or timedelta to seconds."""
    if isinstance(duration, timedelta):
        return duration.total_seconds()

    duration = duration.strip().lower()

    # Parse duration string (e.g., "30s", "5m", "1h", "1d")
    units = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hr": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
    }

    for unit, multiplier in sorted(units.items(), key=lambda x: -len(x[0])):
        if duration.endswith(unit):
            try:
                value = float(duration[: -len(unit)].strip())
                return value * multiplier
            except ValueError:
                pass

    raise ValueError(f"Invalid duration format: {duration}")


def _hash_step_id(step_id: str) -> str:
    """Create a consistent hash for a step ID."""
    return hashlib.sha256(step_id.encode()).hexdigest()[:16]


class StepManager:
    """
    Manages step execution with memoization and durability.

    This class is responsible for:
    - Checking if steps have already completed (memoization)
    - Executing new steps and yielding control back to the server
    - Handling retries and error propagation
    """

    def __init__(
        self,
        run_id: str,
        completed_steps: dict[str, Any] | None = None,
    ) -> None:
        self.run_id = run_id
        self._completed_steps = completed_steps or {}

    def _get_memoized_result(self, step_id: str) -> tuple[bool, Any]:
        """Check if a step has already completed and return its result."""
        step_hash = _hash_step_id(step_id)
        if step_hash in self._completed_steps:
            return True, self._completed_steps[step_hash]
        return False, None

    async def run(
        self,
        step_id: str,
        fn: Callable[..., T | Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute a function as a durable step with memoization.

        If this step has already completed in a previous execution,
        returns the cached result. Otherwise, executes the function
        and signals completion to the server.

        Args:
            step_id: Unique identifier for this step within the function.
            fn: The function to execute. Can be sync or async.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The result of the function execution.

        Raises:
            StepCompleted: Control flow exception to yield to the server.
            StepFailed: When the step fails after all retries.

        Example:
            result = await step.run("process-payment", process_payment, order)
        """
        # Check for memoized result
        is_memoized, result = self._get_memoized_result(step_id)
        if is_memoized:
            return result  # type: ignore

        # Execute the function with timing
        started_at = datetime.now(UTC).isoformat()
        try:
            if callable(fn):
                result = fn(*args, **kwargs)
                # Handle coroutines
                if hasattr(result, "__await__"):
                    result = await result
        except (StepCompleted, StepFailed):
            # Re-raise control flow exceptions from nested steps
            raise
        except Exception as e:
            # Let the server handle retries
            raise StepFailed(step_id=step_id, error=e) from e

        # Signal completion to the server (with timing)
        raise StepCompleted(step_id=step_id, result=result, started_at=started_at)

    async def sleep(
        self,
        step_id: str,
        duration: str | timedelta,
    ) -> None:
        """
        Pause execution for a specified duration.

        The function suspends and the server will resume it after
        the duration elapses. No resources are consumed during sleep.

        Args:
            step_id: Unique identifier for this sleep step.
            duration: How long to sleep. Can be a string like "30s", "5m", "1h"
                     or a timedelta object.

        Example:
            await step.sleep("wait-before-retry", "30s")
            await step.sleep("daily-delay", timedelta(hours=24))
        """
        # Check for memoized result (sleep already completed)
        is_memoized, _ = self._get_memoized_result(step_id)
        if is_memoized:
            return

        seconds = _parse_duration(duration)

        # Signal sleep to the server
        raise StepCompleted(
            step_id=step_id,
            result={"type": "sleep", "duration_seconds": seconds},
        )

    async def ai(
        self,
        step_id: str,
        *,
        model: str,
        prompt: str | list[dict[str, str]] | None = None,
        messages: list[dict[str, str]] | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        provider: str | None = None,
        use_cache: bool = True,
        tools: list[Any] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        max_tool_calls: int = 10,
        num_retries: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute an LLM call with automatic retry and cost tracking.

        Supports multiple providers (OpenAI, Anthropic, etc.) with
        unified interface. Automatically retries on rate limits
        and transient errors.

        Args:
            step_id: Unique identifier for this AI step.
            model: Model name (e.g., "gpt-5", "claude-sonnet-4-6").
            prompt: Simple text prompt (converted to messages internally).
            messages: Full messages array for chat models.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature.
            provider: Optional provider override (auto-detected from model).
            use_cache: Whether to cache the response (default True).
            tools: List of Tool objects that the LLM can call.
            tool_choice: How the LLM should choose tools ("auto", "required", "none", or specific tool).
            max_tool_calls: Maximum number of tool calls allowed in this step.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Dictionary with the model response and usage information:
            - content: The model's response text
            - model: The model used
            - provider: The provider (openai, anthropic, etc.)
            - usage: Token counts and cost information
              - prompt_tokens: Number of input tokens
              - completion_tokens: Number of output tokens
              - total_tokens: Total token count
              - cost_usd: Estimated cost in USD
              - latency_ms: Response latency in milliseconds
            - finish_reason: Why the model stopped generating
            - tool_calls: List of tool calls made (if tools provided)

        Example:
            result = await step.ai(
                "analyze-order",
                model="gpt-5",
                prompt=f"Analyze this order for fraud: {order}",
            )
            analysis = result["content"]
            cost = result["usage"]["cost_usd"]

            # Or with full messages
            result = await step.ai(
                "chat-response",
                model="claude-sonnet-4-6",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"},
                ],
            )

            # With tools
            from flowforge import tool

            @tool(name="search_db", description="Search database")
            async def search_db(query: str) -> dict:
                return {"results": [...]}

            result = await step.ai(
                "search-step",
                model="gpt-5",
                prompt="Find customer john@example.com",
                tools=[search_db],
                tool_choice="auto",
            )
            if result.get("tool_calls"):
                print(f"Tools called: {result['tool_calls']}")
        """
        num_retries = _resolve_num_retries(num_retries)

        # Build messages once (shared across attempts).
        if prompt is not None and messages is None:
            if isinstance(prompt, str):
                messages = [{"role": "user", "content": prompt}]
            else:
                messages = prompt

        if messages is None:
            raise ValueError("Either 'prompt' or 'messages' must be provided")

        tools_schema = None
        if tools:
            tools_schema = [
                t.to_openai_schema() if isinstance(t, Tool) else t
                for t in tools
            ]

        # Durable retry loop. Each attempt is its own memoised sub-step, with
        # a step.sleep between attempts so the worker is freed during the
        # wait. First attempt keeps the caller's step_id (back-compat); only
        # subsequent attempts get an /attempt-N suffix.
        last_signal: dict[str, Any] | None = None
        for attempt in range(num_retries + 1):
            attempt_id = step_id if attempt == 0 else f"{step_id}/attempt-{attempt + 1}"
            result = await self._ai_attempt(
                attempt_id,
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                provider=provider,
                use_cache=use_cache,
                tools_schema=tools_schema,
                tool_choice=tool_choice,
                max_tool_calls=max_tool_calls,
                extra_kwargs=kwargs,
            )

            if not (isinstance(result, dict) and result.get("__rate_limited")):
                return result  # type: ignore[return-value]

            last_signal = result
            if attempt >= num_retries:
                break

            retry_after = float(result.get("__retry_after") or 1.0)
            sleep_s = _retry_sleep(retry_after)
            await self.sleep(
                f"{step_id}/retry-sleep-{attempt + 1}",
                duration=f"{sleep_s:.3f}s",
            )

        assert last_signal is not None  # loop always sets it before breaking
        raise RateLimited(
            step_id=step_id,
            retry_after=last_signal.get("__retry_after"),
            provider=str(last_signal.get("__provider") or ""),
            model=str(last_signal.get("__model") or model),
            original=str(last_signal.get("__error") or ""),
            attempt=num_retries + 1,
            max_attempts=num_retries + 1,
        )

    async def _ai_attempt(
        self,
        attempt_id: str,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        provider: str | None,
        use_cache: bool,
        tools_schema: list[dict[str, Any]] | None,
        tool_choice: str | dict[str, Any],
        max_tool_calls: int,
        extra_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a single LLM attempt.

        On first call yields to the server (raises StepCompleted). On replay,
        returns the memoised server response — either a normal AI response dict
        or a rate-limit marker ({"__rate_limited": True, "__retry_after": ...}).
        """
        is_memoized, result = self._get_memoized_result(attempt_id)
        if is_memoized:
            return result  # type: ignore[return-value]

        ai_request: dict[str, Any] = {
            "type": "ai",
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "provider": provider,
            "use_cache": use_cache,
            "tools": tools_schema,
            "tool_choice": tool_choice,
            "max_tool_calls": max_tool_calls,
            **extra_kwargs,
        }

        raise StepCompleted(step_id=attempt_id, result=ai_request)

    async def wait_for_event(
        self,
        step_id: str,
        *,
        event: str,
        match: str | None = None,
        timeout: str | timedelta | None = None,
    ) -> dict[str, Any] | None:
        """
        Pause and wait for an external event.

        The function suspends until a matching event is received
        or the timeout expires.

        Args:
            step_id: Unique identifier for this wait step.
            event: Event name to wait for (e.g., "order/approved").
            match: Optional expression to match specific events.
                  Example: "data.order_id == '123'"
            timeout: How long to wait before timing out.
                    If not specified, waits indefinitely.

        Returns:
            The matching event data, or None if timeout.

        Raises:
            WaitForEventTimeout: If timeout expires (when raise_on_timeout=True).

        Example:
            approval = await step.wait_for_event(
                "wait-approval",
                event="order/approved",
                match=f"data.order_id == '{order_id}'",
                timeout="24h",
            )

            if approval is None:
                # Handle timeout
                return {"status": "timed_out"}
        """
        # Check for memoized result
        is_memoized, result = self._get_memoized_result(step_id)
        if is_memoized:
            return result  # type: ignore

        timeout_seconds = None
        if timeout is not None:
            timeout_seconds = _parse_duration(timeout)

        wait_request = {
            "type": "wait_for_event",
            "event": event,
            "match": match,
            "timeout_seconds": timeout_seconds,
        }

        raise StepCompleted(step_id=step_id, result=wait_request)

    async def invoke(
        self,
        step_id: str,
        *,
        function_id: str,
        data: dict[str, Any],
        wait: bool = True,
    ) -> Any:
        """
        Invoke another FlowForge function.

        Args:
            step_id: Unique identifier for this invoke step.
            function_id: The ID of the function to invoke.
            data: Data to pass as the event payload.
            wait: If True, waits for the function to complete.
                 If False, returns the run ID immediately.

        Returns:
            If wait=True: The result of the invoked function.
            If wait=False: The run ID of the spawned function.

        Example:
            # Wait for result
            result = await step.invoke(
                "send-notification",
                function_id="send-email",
                data={"to": user.email, "template": "welcome"},
            )

            # Fire and forget
            run_id = await step.invoke(
                "start-background-job",
                function_id="process-data",
                data={"batch_id": batch.id},
                wait=False,
            )
        """
        # Check for memoized result
        is_memoized, result = self._get_memoized_result(step_id)
        if is_memoized:
            return result  # type: ignore

        invoke_request = {
            "type": "invoke",
            "function_id": function_id,
            "data": data,
            "wait": wait,
        }

        raise StepCompleted(step_id=step_id, result=invoke_request)

    async def send_event(
        self,
        step_id: str,
        *,
        name: str,
        data: dict[str, Any],
        id: str | None = None,
    ) -> str:
        """
        Send an event to trigger other functions.

        Args:
            step_id: Unique identifier for this send step.
            name: Event name (e.g., "order/shipped").
            data: Event payload data.
            id: Optional idempotency key for the event.

        Returns:
            The event ID.

        Example:
            event_id = await step.send_event(
                "notify-shipping",
                name="order/shipped",
                data={"order_id": order.id, "tracking": tracking_number},
            )
        """
        # Check for memoized result
        is_memoized, result = self._get_memoized_result(step_id)
        if is_memoized:
            return result  # type: ignore

        send_request = {
            "type": "send_event",
            "name": name,
            "data": data,
            "id": id,
        }

        raise StepCompleted(step_id=step_id, result=send_request)

    async def agent(
        self,
        step_id: str,
        *,
        task: str,
        model: str,
        system: str = "",
        tools: list[Tool],
        max_iterations: int = 20,
        checkpoint_strategy: str = "per_tool",
        max_tool_calls: int = 50,
        temperature: float = 0.7,
        num_retries: int | None = None,
        _depth: int = 0,
        _max_depth: int = 3,
        **kwargs: Any,
    ) -> AgentResult:
        """
        Execute an autonomous agent loop with tool calling and HITL support.

        The agent will iteratively call the LLM, execute tools, and continue
        until the task is complete or limits are reached. Each tool execution
        is checkpointed for durability.

        Sub-agent tools (created via ``sub_agent()``) are automatically
        detected and executed as nested agent loops.

        Args:
            step_id: Unique identifier for this agent execution.
            task: The task/prompt for the agent to accomplish.
            model: LLM model to use (e.g., "claude-sonnet-4-6", "gpt-5").
            system: System prompt for the agent.
            tools: List of Tool objects the agent can call.
            max_iterations: Maximum reasoning iterations (default 20).
            checkpoint_strategy: When to checkpoint:
                - "per_tool": Checkpoint after each tool execution (default)
                - "per_iteration": Checkpoint after each LLM call
                - "final_only": Only checkpoint final result
            max_tool_calls: Maximum total tool calls across iterations (default 50).
            temperature: Sampling temperature for LLM (default 0.7).
            _depth: Current nesting depth (internal, used by sub-agent recursion).
            _max_depth: Maximum allowed nesting depth (default 3).
            **kwargs: Additional LLM parameters.

        Returns:
            AgentResult with output, status, metrics, and full execution trace.

        Example:
            result = await step.agent(
                "research-agent",
                task="Research Tokyo weather and create a 3-day itinerary",
                model="claude-sonnet-4-6",
                system="You are a travel planning assistant.",
                tools=[web_search, weather_api, get_attractions],
                max_iterations=20,
            )
            print(result.output)
            print(f"Used {result.iterations} iterations, {result.tool_calls_count} tool calls")
        """
        # Check for memoized result (agent already completed)
        is_memoized, result = self._get_memoized_result(step_id)
        if is_memoized:
            # Reconstruct AgentResult from stored dict
            if isinstance(result, dict):
                return AgentResult(
                    output=result.get("output", ""),
                    status=result.get("status", "completed"),
                    iterations=result.get("iterations", 0),
                    tool_calls_count=result.get("tool_calls_count", 0),
                    tokens_used=result.get("tokens_used", 0),
                    messages=result.get("messages", []),
                    tool_calls=result.get("tool_calls", []),
                )
            return result  # type: ignore

        # Initialize agent state
        state = AgentState(
            messages=[],
            iteration=0,
            tool_calls_count=0,
            tokens_used=0,
            status="running",
        )

        # Add system message if provided
        if system:
            state.messages.append({"role": "system", "content": system})

        # Add initial user task
        state.messages.append({"role": "user", "content": task})

        # Build tool map for quick lookup
        tool_map = {tool.name: tool for tool in tools}

        # Track all tool calls for the result
        all_tool_calls: list[dict[str, Any]] = []

        # Agent loop
        while state.iteration < max_iterations:
            # Check if we've hit tool call limit
            if state.tool_calls_count >= max_tool_calls:
                state.status = "max_tool_calls"
                break

            # Call LLM with current messages. num_retries propagates per
            # iteration — a 429 on iter-N/think only retries iter-N/think;
            # earlier iterations stay memoised.
            think_step_id = f"{step_id}/iter-{state.iteration}/think"
            ai_response = await self.ai(
                think_step_id,
                model=model,
                messages=state.messages,
                temperature=temperature,
                tools=tools,
                tool_choice="auto",
                max_tool_calls=max_tool_calls - state.tool_calls_count,
                num_retries=num_retries,
                **kwargs,
            )

            # Update token count
            if "usage" in ai_response:
                state.tokens_used += ai_response["usage"].get("total_tokens", 0)

            # Add assistant response to messages
            assistant_message = {
                "role": "assistant",
                "content": ai_response.get("content", ""),
            }

            # Normalize tool calls to OpenAI format for litellm compatibility.
            # Server stores flat format: {"id", "name", "arguments"}
            # LiteLLM expects OpenAI format: {"id", "type", "function": {"name", "arguments"}}
            raw_tool_calls = ai_response.get("tool_calls", [])
            normalized_tool_calls = []
            for tc in raw_tool_calls:
                if "function" in tc:
                    # Already in OpenAI format
                    normalized_tool_calls.append(tc)
                else:
                    # Convert flat format to OpenAI format
                    args = tc.get("arguments", {})
                    if not isinstance(args, str):
                        args = json.dumps(args)
                    normalized_tool_calls.append({
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": args,
                        },
                    })

            # Include tool calls in assistant message if present
            if normalized_tool_calls:
                assistant_message["tool_calls"] = normalized_tool_calls

            state.messages.append(assistant_message)

            # Check finish reason
            finish_reason = ai_response.get("finish_reason", "stop")

            # If no tool calls, we're done
            if not normalized_tool_calls or finish_reason == "stop":
                state.status = "completed"
                break

            # Execute each tool call
            for i, tool_call in enumerate(normalized_tool_calls):
                tool_call_id = tool_call.get("id", f"tool-{state.tool_calls_count}")
                tool_name = tool_call.get("function", {}).get("name", "")
                tool_args = tool_call.get("function", {}).get("arguments", {})

                # Parse arguments if they're a JSON string
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError:
                        tool_args = {}

                # Find the tool
                tool = tool_map.get(tool_name)
                if not tool:
                    # Tool not found - add error message
                    state.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": json.dumps({"error": f"Tool '{tool_name}' not found"}),
                    })
                    continue

                # Record tool call
                tool_call_record = {
                    "iteration": state.iteration,
                    "tool_call_id": tool_call_id,
                    "tool": tool_name,
                    "arguments": tool_args,
                }
                all_tool_calls.append(tool_call_record)

                # Check if tool requires approval (HITL)
                if tool.requires_approval:
                    # Create approval request step
                    approval_step_id = f"{step_id}/iter-{state.iteration}/approval-{tool_call_id}"

                    # Wait for approval event
                    approval_timeout = tool.approval_timeout or "30m"
                    approval_event = await self.wait_for_event(
                        approval_step_id,
                        event="tool/approved",
                        match=f"data.tool_call_id == '{tool_call_id}'",
                        timeout=approval_timeout,
                    )

                    # Check if approved
                    if approval_event is None or not approval_event.get("data", {}).get("approved", False):
                        # Rejected or timed out
                        rejection_reason = approval_event.get("data", {}).get("reason", "Tool execution rejected")
                        state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps({"error": f"Tool execution rejected: {rejection_reason}"}),
                        })
                        tool_call_record["status"] = "rejected"
                        tool_call_record["reason"] = rejection_reason
                        continue

                # Execute tool via step.run for checkpointing
                tool_step_id = f"{step_id}/iter-{state.iteration}/tool-{tool_call_id}"

                # --- Sub-agent interception ---
                # If the tool is a sub-agent wrapper, run a nested agent
                # loop instead of calling tool.fn directly.
                cfg: SubAgentConfig | None = getattr(tool, "_sub_agent_config", None)
                if cfg is not None:
                    # Depth guard: prevent infinite sub-agent recursion
                    if _depth >= _max_depth:
                        error_message = json.dumps({
                            "error": f"Sub-agent depth limit reached ({_max_depth}). "
                            "Cannot spawn further sub-agents.",
                        })
                        state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": error_message,
                        })
                        tool_call_record["status"] = "failed"
                        tool_call_record["error"] = "depth_limit_reached"
                        state.tool_calls_count += 1
                        continue

                    sub_step_id = f"{step_id}/sub-{cfg.agent.name}-{tool_call_id}"

                    # Build sub-agent system prompt with optional parent context
                    sub_system = cfg.agent.system
                    if cfg.context_mode == "summary":
                        recent = state.messages[-6:]  # last 3 exchanges
                        context_lines = [
                            f"[{m['role']}]: {str(m.get('content', ''))[:200]}"
                            for m in recent
                        ]
                        sub_system += "\n\nParent context:\n" + "\n".join(context_lines)
                    elif cfg.context_mode == "full_history":
                        sub_system += "\n\nFull parent conversation:\n" + json.dumps(state.messages)

                    try:
                        sub_result = await self.agent(
                            sub_step_id,
                            task=tool_args.get("task", ""),
                            model=cfg.agent.model or model,
                            system=sub_system,
                            tools=cfg.agent.tools,
                            max_iterations=cfg.max_iterations,
                            max_tool_calls=cfg.max_tool_calls,
                            temperature=cfg.temperature,
                            _depth=_depth + 1,
                            _max_depth=_max_depth,
                            **kwargs,
                        )
                        sub_output = sub_result.output

                        state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": sub_output,
                        })
                        tool_call_record["status"] = "success"
                        tool_call_record["result"] = sub_output
                        tool_call_record["sub_agent"] = sub_result.to_dict()
                    except StepCompleted:
                        # Sub-agent completed its first execution — propagate
                        # so the server can memoize the step. On replay the
                        # nested agent() call returns normally.
                        raise
                    except (StepFailed, Exception) as e:
                        err_msg = str(e)
                        error_message = json.dumps({"error": err_msg})
                        state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": error_message,
                        })
                        tool_call_record["status"] = "failed"
                        tool_call_record["error"] = err_msg

                    state.tool_calls_count += 1
                    continue
                # --- End sub-agent interception ---

                try:
                    tool_result = await self.run(
                        tool_step_id,
                        tool.fn,
                        **tool_args,
                    )

                    # Serialize result
                    if not isinstance(tool_result, str):
                        tool_result = json.dumps(tool_result)

                    # Add tool result to messages
                    state.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": tool_result,
                    })

                    tool_call_record["status"] = "success"
                    tool_call_record["result"] = tool_result

                except StepCompleted:
                    # Success checkpoint — must propagate to the server.
                    # The server saves the tool result and re-enqueues;
                    # on replay the step is memoized and returns instantly.
                    raise

                except (StepFailed, Exception) as e:
                    # Tool execution failed — feed the error back to the
                    # agent so it can adapt (retry, use a different tool,
                    # or skip). Do NOT kill the whole run.
                    err_msg = str(e)
                    error_message = json.dumps({"error": err_msg})
                    state.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": error_message,
                    })

                    tool_call_record["status"] = "failed"
                    tool_call_record["error"] = err_msg

                state.tool_calls_count += 1

                # Check if we've hit tool call limit after this tool
                if state.tool_calls_count >= max_tool_calls:
                    state.status = "max_tool_calls"
                    # Add placeholder results for remaining unprocessed tool calls
                    # in this batch — Anthropic requires every tool_use block to
                    # have a corresponding tool_result in the next message.
                    for remaining in normalized_tool_calls[i + 1:]:
                        remaining_id = remaining.get("id", "")
                        remaining_name = remaining.get("function", {}).get("name", "")
                        state.messages.append({
                            "role": "tool",
                            "tool_call_id": remaining_id,
                            "name": remaining_name,
                            "content": json.dumps({"status": "skipped", "reason": "tool call limit reached"}),
                        })
                    break

            # If we hit max tool calls, exit loop
            if state.status == "max_tool_calls":
                break

            # Increment iteration
            state.iteration += 1

        # If we exited loop due to max iterations
        if state.iteration >= max_iterations and state.status == "running":
            state.status = "max_iterations"

        # If we hit limits without a final text response, make one last
        # LLM call WITHOUT tools to force the agent to synthesize output.
        if state.status in ("max_tool_calls", "max_iterations"):
            state.messages.append({
                "role": "user",
                "content": (
                    "You've reached the tool call limit. Based on ALL the research "
                    "you've gathered so far, produce your final output now. "
                    "Do NOT call any more tools — just return the result."
                ),
            })
            wrap_step_id = f"{step_id}/wrap-up"
            # Forward max_tokens from kwargs so the wrap-up gets adequate space
            wrap_kwargs: dict[str, Any] = {}
            if "max_tokens" in kwargs:
                wrap_kwargs["max_tokens"] = kwargs["max_tokens"]
            wrap_response = await self.ai(
                wrap_step_id,
                model=model,
                messages=state.messages,
                temperature=temperature,
                # Pass tools so Anthropic understands the message history
                # (tool_use/tool_result blocks), but tool_choice="none" prevents
                # the model from making any further tool calls.
                tools=tools,
                tool_choice="none",
                **wrap_kwargs,
            )
            wrap_content = wrap_response.get("content", "")
            if wrap_content:
                state.messages.append({
                    "role": "assistant",
                    "content": wrap_content,
                })

        # Extract final output
        final_output = ""
        for msg in reversed(state.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                final_output = msg["content"]
                break

        # Create result
        result = AgentResult(
            output=final_output,
            status=state.status,
            iterations=state.iteration + 1,  # +1 because iteration is 0-indexed
            tool_calls_count=state.tool_calls_count,
            tokens_used=state.tokens_used,
            messages=state.messages,
            tool_calls=all_tool_calls,
        )

        # Signal completion with the full result
        raise StepCompleted(step_id=step_id, result=result.to_dict())

    async def network(
        self,
        step_id: str,
        *,
        network: Network,
        input: str,
        initial_state: dict[str, Any] | None = None,
        max_iterations: int = 10,
        **kwargs: Any,
    ) -> NetworkResult:
        """
        Execute a multi-agent network with routing and shared state.

        The network will:
        1. Initialize shared state
        2. Execute first agent (or let router decide)
        3. After each agent, call router to get next agent
        4. Repeat until router returns None or max_iterations
        5. Detect handoffs via {"__handoff__": "agent_name"} in tool returns

        Args:
            step_id: Unique identifier for this network execution.
            network: The Network to execute.
            input: Initial input/prompt for the network.
            initial_state: Optional initial state values.
            max_iterations: Max agent invocations (default 10).
            **kwargs: Additional parameters passed to agents.

        Returns:
            NetworkResult with output, status, metrics, and execution trace.

        Example:
            result = await step.network(
                "support-network",
                network=support_net,
                input="Customer wants refund for order #123",
                initial_state={"customer_id": "c_123"},
                max_iterations=15,
            )
            print(result.output)
            print(f"Executed {result.iterations} iterations across {len(result.agent_calls)} agents")
        """
        # Check for memoized result
        is_memoized, result = self._get_memoized_result(step_id)
        if is_memoized:
            # Reconstruct NetworkResult from stored dict
            if isinstance(result, dict):
                return NetworkResult(
                    output=result.get("output"),
                    status=result.get("status", "completed"),
                    iterations=result.get("iterations", 0),
                    agent_calls=result.get("agent_calls", []),
                    state=result.get("state", {}),
                    total_tokens=result.get("total_tokens", 0),
                    total_cost_usd=result.get("total_cost_usd", 0.0),
                )
            return result  # type: ignore

        # Initialize state
        state = NetworkState()
        if initial_state:
            for k, v in initial_state.items():
                state.set(k, v)
        network.state = state

        # Track execution
        agent_calls: list[dict[str, Any]] = []
        total_tokens = 0
        total_cost = 0.0
        iteration = 0
        last_result = None
        history: list[dict[str, Any]] = [{"role": "user", "content": input}]

        # Main network execution loop
        while iteration < max_iterations:
            # Build router context
            ctx = RouterContext(
                last_result=last_result,
                state=state,
                iteration=iteration,
                history=history,
                agents=network.agents,
            )

            # Get next agent from router
            if isinstance(network.router, LLMRouter):
                # Execute LLM routing via step.ai()
                next_agent = await self._llm_route(
                    f"{step_id}/route-{iteration}",
                    network.router,
                    ctx,
                )
            else:
                # Execute code-based routing
                next_agent = await network.router.route(ctx)

            # Check if network is complete
            if next_agent is None:
                break

            # Check for handoff in last result
            if last_result and hasattr(last_result, "tool_calls"):
                handoff = self._detect_handoff(last_result, network.agents)
                if handoff:
                    next_agent = handoff

            # Determine task for agent
            agent_task = input if iteration == 0 else "Continue based on previous result"

            # Execute agent via step.agent()
            agent_result = await self.agent(
                f"{step_id}/agent-{iteration}-{next_agent.name}",
                task=agent_task,
                model=next_agent.model or network.default_model,
                system=next_agent.system,
                tools=next_agent.tools,
                **kwargs,
            )

            # Track execution
            agent_calls.append({
                "iteration": iteration,
                "agent": next_agent.name,
                "status": agent_result.status,
                "output": agent_result.output,
                "tool_calls_count": agent_result.tool_calls_count,
                "tokens_used": agent_result.tokens_used,
            })

            total_tokens += agent_result.tokens_used
            total_cost += agent_result.tokens_used * 0.000015  # rough estimate

            # Update history
            history.append({
                "role": "assistant",
                "agent": next_agent.name,
                "content": agent_result.output,
            })

            last_result = agent_result
            iteration += 1

        # Determine final status
        status: str = "completed" if iteration < max_iterations else "max_iterations"

        # Build result
        result_obj = NetworkResult(
            output=last_result.output if last_result else None,
            status=status,  # type: ignore
            iterations=iteration,
            agent_calls=agent_calls,
            state=state.to_dict(),
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
        )

        # Signal completion with the full result
        raise StepCompleted(step_id=step_id, result=result_obj.to_dict())

    async def _llm_route(
        self,
        step_id: str,
        router: LLMRouter,
        ctx: RouterContext,
    ) -> AgentDefinition | None:
        """Execute LLM-based routing."""
        agent_names = list(ctx.agents.keys())

        # Format the prompt with context
        prompt = router.prompt.format(
            agents=", ".join(agent_names),
            state=ctx.state.to_dict(),
            last_result=ctx.last_result.output if ctx.last_result else "None",
        )

        # Execute LLM call via step.ai()
        response = await self.ai(
            step_id,
            model=router.model,
            prompt=prompt,
            temperature=router.temperature,
        )

        # Parse the LLM's response
        selected = response.get("content", "").strip()

        # Check if LLM indicated completion
        if selected.upper() == "DONE":
            return None

        # Look up the selected agent
        agent = ctx.agents.get(selected)
        if agent is None:
            # LLM returned invalid agent name - fallback to None (end network)
            return None

        return agent

    def _detect_handoff(
        self,
        result: AgentResult,
        agents: dict[str, AgentDefinition],
    ) -> AgentDefinition | None:
        """Detect handoff request in tool call results."""
        if not result.tool_calls:
            return None

        for tc in result.tool_calls:
            # Check if tool result contains handoff directive
            tc_result = tc.get("result")
            if isinstance(tc_result, str):
                try:
                    tc_result = json.loads(tc_result)
                except json.JSONDecodeError:
                    continue

            if isinstance(tc_result, dict):
                handoff_to = tc_result.get("__handoff__")
                if handoff_to and handoff_to in agents:
                    return agents[handoff_to]

        return None


# Global step instance for module-level access
# This gets configured by the execution context
class _StepProxy:
    """
    Proxy that provides module-level access to step functions.

    The actual StepManager is set per-execution by the context.
    """

    _current_manager: StepManager | None = None

    def _get_manager(self) -> StepManager:
        if self._current_manager is None:
            raise RuntimeError(
                "Step functions can only be called within a FlowForge function context. "
                "Make sure you're using @flowforge.function decorator."
            )
        return self._current_manager

    async def run(
        self,
        step_id: str,
        fn: Callable[..., T | Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        return await self._get_manager().run(step_id, fn, *args, **kwargs)

    async def sleep(self, step_id: str, duration: str | timedelta) -> None:
        return await self._get_manager().sleep(step_id, duration)

    async def ai(
        self,
        step_id: str,
        *,
        model: str,
        prompt: str | list[dict[str, str]] | None = None,
        messages: list[dict[str, str]] | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        provider: str | None = None,
        use_cache: bool = True,
        tools: list[Any] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        max_tool_calls: int = 10,
        num_retries: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self._get_manager().ai(
            step_id,
            model=model,
            prompt=prompt,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            provider=provider,
            use_cache=use_cache,
            tools=tools,
            tool_choice=tool_choice,
            max_tool_calls=max_tool_calls,
            num_retries=num_retries,
            **kwargs,
        )

    async def wait_for_event(
        self,
        step_id: str,
        *,
        event: str,
        match: str | None = None,
        timeout: str | timedelta | None = None,
    ) -> dict[str, Any] | None:
        return await self._get_manager().wait_for_event(
            step_id, event=event, match=match, timeout=timeout
        )

    async def invoke(
        self,
        step_id: str,
        *,
        function_id: str,
        data: dict[str, Any],
        wait: bool = True,
    ) -> Any:
        return await self._get_manager().invoke(
            step_id, function_id=function_id, data=data, wait=wait
        )

    async def send_event(
        self,
        step_id: str,
        *,
        name: str,
        data: dict[str, Any],
        id: str | None = None,
    ) -> str:
        return await self._get_manager().send_event(step_id, name=name, data=data, id=id)

    async def agent(
        self,
        step_id: str,
        *,
        task: str,
        model: str,
        system: str = "",
        tools: list[Tool],
        max_iterations: int = 20,
        checkpoint_strategy: str = "per_tool",
        max_tool_calls: int = 50,
        temperature: float = 0.7,
        num_retries: int | None = None,
        _depth: int = 0,
        _max_depth: int = 3,
        **kwargs: Any,
    ) -> AgentResult:
        return await self._get_manager().agent(
            step_id,
            task=task,
            model=model,
            system=system,
            tools=tools,
            max_iterations=max_iterations,
            checkpoint_strategy=checkpoint_strategy,
            max_tool_calls=max_tool_calls,
            temperature=temperature,
            num_retries=num_retries,
            _depth=_depth,
            _max_depth=_max_depth,
            **kwargs,
        )

    async def network(
        self,
        step_id: str,
        *,
        network: Network,
        input: str,
        initial_state: dict[str, Any] | None = None,
        max_iterations: int = 10,
        **kwargs: Any,
    ) -> NetworkResult:
        return await self._get_manager().network(
            step_id,
            network=network,
            input=input,
            initial_state=initial_state,
            max_iterations=max_iterations,
            **kwargs,
        )


# Global step instance
step = _StepProxy()
