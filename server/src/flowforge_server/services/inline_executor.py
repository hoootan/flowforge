"""Inline executor for serverless/agent-based functions.

This module handles execution of inline functions that don't require
an external worker. It runs the agent loop directly within FlowForge.
"""

import asyncio
import html
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models import (
    ApprovalStatus,
    Function,
    Run,
    Step,
    StepStatus,
    StepType,
    Tool,
    ToolApproval,
    UsageRecord,
)
from flowforge_server.logging import Loggers
from flowforge_server.services.ai import AIService, ToolCall
from flowforge_server.services.builtin_tools import execute_builtin_tool, get_builtin_tool_names
from flowforge_server.services.credentials import (
    CredentialResolutionError,
    resolve_dict_placeholders,
    resolve_placeholders,
)
from flowforge_server.services.network_utils import validate_webhook_url
from flowforge_server.services.sandbox import (
    DEFAULT_TIMEOUT_SECONDS,
    SandboxError,
    SandboxSecurityError,
    SandboxTimeoutError,
    execute_sandboxed,
)
from flowforge_server.stream.pubsub import RunEventType, publish_run_event

log = Loggers.inline_executor()

# Maximum sub-agent nesting depth (server-side)
MAX_SUB_AGENT_DEPTH = 3


class InlineExecutor:
    """
    Executes inline/serverless functions directly within FlowForge.

    For inline functions (is_inline=True), this executor:
    1. Loads the function's tools from the database
    2. Runs an agent loop with the AI service
    3. Handles tool calls (including approval flows and sub-agents)
    4. Returns the final result
    """

    def __init__(self, ai_service: AIService) -> None:
        self.ai_service = ai_service
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def execute(
        self,
        session: AsyncSession,
        fn: Function,
        run: Run,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute an inline function.

        Args:
            session: Database session
            fn: The function to execute
            run: The run record
            event_data: Event data that triggered the function

        Returns:
            Result dictionary with status and output
        """
        if not fn.is_inline:
            raise ValueError(f"Function {fn.function_id} is not an inline function")

        # Small delay to allow SSE clients to connect before streaming begins.
        # This prevents the race condition where chunks are buffered before
        # the client establishes their SSE connection.
        await asyncio.sleep(0.15)

        # Get configuration
        agent_config = fn.agent_config or {}
        model = agent_config.get("model", "claude-sonnet-4-6")
        max_iterations = agent_config.get("max_iterations", 30)
        max_tool_calls = agent_config.get("max_tool_calls", 50)
        sub_agents_config = agent_config.get("sub_agents", {})

        # Load tools
        tools = await self._load_tools(session, fn.tools_config or [], tenant_id=run.tenant_id)

        # Synthesize sub-agent tools from config
        sub_agent_tools = self._synthesize_sub_agent_tools(sub_agents_config)
        tools.extend(sub_agent_tools)

        # Get the task from event data
        task = event_data.get("prompt", "")
        if not task:
            return {
                "status": "error",
                "error": {"type": "ValidationError", "message": "No prompt provided"},
            }

        # Build initial messages
        messages: list[dict[str, Any]] = []
        system_content = fn.system_prompt or ""

        # Inject enabled skill instructions at runtime
        if fn.enabled_skills:
            skill_instructions = await self._load_skill_instructions(
                session, fn.enabled_skills, tenant_id=run.tenant_id,
            )
            if skill_instructions:
                system_content = (system_content + "\n\n" + skill_instructions).strip()

        if system_content:
            messages.append({"role": "system", "content": system_content})

        # Pass full event data as user message so the agent has all context
        # (brand_context, content_items, fields, etc.)
        user_message = json.dumps(event_data, indent=2, default=str)
        messages.append({"role": "user", "content": user_message})

        # Run agent loop
        result = await self._run_agent_loop(
            session=session,
            run=run,
            model=model,
            tools=tools,
            messages=messages,
            max_iterations=max_iterations,
            max_tool_calls=max_tool_calls,
            sub_agents_config=sub_agents_config,
            step_prefix="agent",
            depth=0,
        )

        return result

    async def _run_agent_loop(
        self,
        session: AsyncSession,
        run: Run,
        model: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        max_iterations: int,
        max_tool_calls: int,
        sub_agents_config: dict[str, Any],
        step_prefix: str = "agent",
        depth: int = 0,
    ) -> dict[str, Any]:
        """
        Core agent loop shared by top-level execution and sub-agent calls.

        Args:
            session: Database session
            run: The run record
            model: LLM model to use
            tools: List of tool info dicts (including sub-agent tools)
            messages: Initial message history
            max_iterations: Max LLM iterations
            max_tool_calls: Max tool calls
            sub_agents_config: Sub-agent configuration dict
            step_prefix: Prefix for step hashes (e.g. "agent" or "sub-researcher")
            depth: Current sub-agent nesting depth

        Returns:
            Result dictionary with status and output
        """
        iteration = 0
        tool_calls_count = 0
        tokens_used = {"prompt": 0, "completion": 0, "total": 0}
        all_tool_calls: list[dict[str, Any]] = []
        final_output = None

        task_preview = ""
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                task_preview = content[:200] if isinstance(content, str) else str(content)[:200]
                break

        await publish_run_event(
            str(run.id),
            RunEventType.THINKING,
            {
                "run_id": str(run.id),
                "model": model,
                "status": "agent_started",
                "task": task_preview,
                "depth": depth,
                "step_prefix": step_prefix,
            },
        )

        while iteration < max_iterations and tool_calls_count < max_tool_calls:
            iteration += 1

            # Check for existing step (for retries)
            step_hash = f"{step_prefix}:{run.id}:{iteration}"
            existing_step = await session.execute(
                select(Step).where(
                    Step.run_id == run.id,
                    Step.step_hash == step_hash,
                )
            )
            step = existing_step.scalar_one_or_none()

            if step:
                # Reuse existing step
                step.status = StepStatus.RUNNING
                step.started_at = datetime.utcnow()
                step.ended_at = None
                step.error = None
            else:
                # Create new step for this iteration
                step_type = StepType.SUB_AGENT if depth > 0 else StepType.AI
                step = Step(
                    run_id=run.id,
                    step_id=f"{step_prefix}-iteration-{iteration}",
                    step_hash=step_hash,
                    step_type=step_type,
                    status=StepStatus.RUNNING,
                    started_at=datetime.utcnow(),
                )
                session.add(step)

            await session.flush()

            # Publish step started event for this iteration
            await publish_run_event(
                str(run.id),
                RunEventType.STEP_STARTED,
                {
                    "run_id": str(run.id),
                    "step_id": step.step_id,
                    "step_type": "sub_agent" if depth > 0 else "ai",
                    "iteration": iteration,
                    "depth": depth,
                },
            )

            # Publish thinking event
            await publish_run_event(
                str(run.id),
                RunEventType.THINKING,
                {
                    "run_id": str(run.id),
                    "step_id": step.step_id,
                    "model": model,
                    "iteration": iteration,
                    "status": "calling_llm",
                    "depth": depth,
                },
            )

            # Call LLM with streaming
            try:
                accumulated_content = ""
                final_usage = None
                final_tool_calls = []
                finish_reason = None
                chunk_count = 0

                log.info("llm_stream_starting", model=model, run_id=str(run.id))

                async for chunk in self.ai_service.complete_stream(
                    model=model,
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.7,
                    tools=[t["schema"] for t in tools] if tools else None,
                    tool_choice="auto" if tools else None,
                    tenant_id=run.tenant_id,
                    session=session,
                ):
                    if chunk["type"] == "content":
                        chunk_count += 1
                        accumulated_content += chunk["chunk"]
                        # Log every 10th chunk for debugging
                        if chunk_count % 10 == 1:
                            log.debug("llm_chunk_received", chunk_num=chunk_count, chunk_len=len(chunk["chunk"]))
                        # Publish chunk event for streaming UI
                        subscribers = await publish_run_event(
                            str(run.id),
                            RunEventType.THINKING_CHUNK,
                            {
                                "run_id": str(run.id),
                                "step_id": step.step_id,
                                "chunk": chunk["chunk"],
                            },
                        )
                        if chunk_count == 1:
                            log.info("first_chunk_published", subscribers=subscribers, run_id=str(run.id))
                    elif chunk["type"] == "done":
                        final_usage = chunk["usage"]
                        final_tool_calls = chunk.get("tool_calls", [])
                        finish_reason = chunk.get("finish_reason")
                        log.info("llm_stream_complete", total_chunks=chunk_count, content_len=len(accumulated_content))

                # Build response-like object for compatibility
                class StreamedResponse:
                    def __init__(self, content, usage, tool_calls):
                        self.content = content
                        self.usage = usage
                        self.tool_calls = tool_calls

                    def to_dict(self):
                        result = {
                            "content": self.content,
                            "model": model,
                            "provider": final_usage.provider if final_usage else "unknown",
                            "usage": {
                                "prompt_tokens": self.usage.prompt_tokens if self.usage else 0,
                                "completion_tokens": self.usage.completion_tokens if self.usage else 0,
                                "total_tokens": self.usage.total_tokens if self.usage else 0,
                                "cost_usd": self.usage.cost_usd if self.usage else 0,
                                "latency_ms": self.usage.latency_ms if self.usage else 0,
                            },
                            "finish_reason": finish_reason,
                        }
                        if self.tool_calls:
                            result["tool_calls"] = [
                                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                                for tc in self.tool_calls
                            ]
                        return result

                response = StreamedResponse(accumulated_content, final_usage, final_tool_calls)

            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = {"type": type(e).__name__, "message": str(e)}
                step.ended_at = datetime.utcnow()
                await session.commit()

                return {
                    "status": "error",
                    "error": {"type": type(e).__name__, "message": str(e)},
                }

            # Track token usage and record to database
            if response.usage:
                tokens_used["prompt"] += response.usage.prompt_tokens
                tokens_used["completion"] += response.usage.completion_tokens
                tokens_used["total"] += response.usage.total_tokens

                # Record usage to database
                usage_record = UsageRecord(
                    tenant_id=run.tenant_id,
                    run_id=run.id,
                    model=response.usage.model or model,
                    provider=response.usage.provider or "unknown",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    cost_usd=response.usage.cost_usd,
                    latency_ms=response.usage.latency_ms,
                    request_type="inline_agent" if depth == 0 else "sub_agent",
                    extra_data={
                        "step_id": step.step_id,
                        "iteration": iteration,
                        "depth": depth,
                    },
                )
                session.add(usage_record)

            # Update step
            step.output = response.to_dict()
            step.ended_at = datetime.utcnow()

            # Check if LLM wants to call tools
            if response.tool_calls:
                step.status = StepStatus.COMPLETED
                await session.flush()

                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                # Arguments must be JSON string for LiteLLM/Anthropic
                                "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else tc.arguments,
                            },
                        }
                        for tc in response.tool_calls
                    ],
                })

                # Execute each tool call
                for tool_call in response.tool_calls:
                    tool_calls_count += 1

                    # Find tool info
                    tool_info = next(
                        (t for t in tools if t["name"] == tool_call.name),
                        None
                    )

                    if not tool_info:
                        # Unknown tool
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: Unknown tool '{tool_call.name}'",
                        })
                        continue

                    # Check if tool requires approval
                    tool_arguments = tool_call.arguments.copy()  # Start with original args
                    if tool_info.get("requires_approval"):
                        # Create approval request and wait
                        approval_result = await self._request_approval(
                            session,
                            run,
                            step,
                            tool_call,
                            tool_info,
                        )

                        if approval_result["status"] == "rejected":
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Tool call was rejected by user: {approval_result.get('reason', 'No reason provided')}",
                            })
                            continue
                        elif approval_result["status"] == "timeout":
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": "Tool call timed out waiting for approval",
                            })
                            continue

                        # Merge any modified arguments from the approval (e.g., user input)
                        if approval_result.get("modified_arguments"):
                            tool_arguments.update(approval_result["modified_arguments"])

                    # --- Sub-agent interception (server-side) ---
                    if tool_info.get("is_sub_agent") and tool_call.name in sub_agents_config:
                        if depth >= MAX_SUB_AGENT_DEPTH:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Error: Sub-agent depth limit reached ({MAX_SUB_AGENT_DEPTH}). Cannot spawn further sub-agents.",
                            })
                            all_tool_calls.append({
                                "id": tool_call.id,
                                "tool_name": tool_call.name,
                                "arguments": tool_arguments,
                                "result": "depth_limit_reached",
                                "iteration": iteration,
                                "is_sub_agent": True,
                            })
                            continue

                        sub_config = sub_agents_config[tool_call.name]
                        sub_task = tool_arguments.get("task", "")

                        # Publish sub-agent started event
                        await publish_run_event(
                            str(run.id),
                            RunEventType.SUB_AGENT_STARTED,
                            {
                                "run_id": str(run.id),
                                "sub_agent_name": tool_call.name,
                                "task": sub_task[:200],
                                "depth": depth + 1,
                                "parent_step_id": step.step_id,
                            },
                        )

                        # Build sub-agent messages
                        sub_messages: list[dict[str, Any]] = []
                        sub_system = sub_config.get("system_prompt", "")
                        if sub_system:
                            sub_messages.append({"role": "system", "content": sub_system})
                        sub_messages.append({"role": "user", "content": sub_task})

                        # Load sub-agent tools
                        sub_tool_names = sub_config.get("tools", [])
                        sub_tools = await self._load_tools(session, sub_tool_names, tenant_id=run.tenant_id)

                        # Recursively run agent loop
                        sub_result = await self._run_agent_loop(
                            session=session,
                            run=run,
                            model=sub_config.get("model", model),
                            tools=sub_tools,
                            messages=sub_messages,
                            max_iterations=sub_config.get("max_iterations", 15),
                            max_tool_calls=sub_config.get("max_tool_calls", 30),
                            sub_agents_config={},  # Sub-agents don't get nested sub-agents by default
                            step_prefix=f"sub-{tool_call.name}",
                            depth=depth + 1,
                        )

                        # Extract output
                        sub_output = ""
                        if sub_result.get("status") == "function_complete":
                            sub_output = sub_result.get("output", {}).get("result", "") or ""
                        elif sub_result.get("status") == "error":
                            sub_output = f"Sub-agent error: {sub_result.get('error', {}).get('message', 'unknown')}"

                        # Publish sub-agent completed event
                        await publish_run_event(
                            str(run.id),
                            RunEventType.SUB_AGENT_COMPLETED,
                            {
                                "run_id": str(run.id),
                                "sub_agent_name": tool_call.name,
                                "output": sub_output[:500],
                                "depth": depth + 1,
                                "parent_step_id": step.step_id,
                            },
                        )

                        result_str = sub_output

                        all_tool_calls.append({
                            "id": tool_call.id,
                            "tool_name": tool_call.name,
                            "arguments": tool_arguments,
                            "result": result_str,
                            "iteration": iteration,
                            "is_sub_agent": True,
                            "sub_agent_result": sub_result.get("output"),
                        })

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_str,
                        })
                        continue
                    # --- End sub-agent interception ---

                    # Publish tool call started event
                    await publish_run_event(
                        str(run.id),
                        RunEventType.TOOL_CALL_STARTED,
                        {
                            "run_id": str(run.id),
                            "step_id": step.step_id,
                            "tool_name": tool_call.name,
                            "tool_call_id": tool_call.id,
                            "arguments": tool_call.arguments,
                        },
                    )

                    # Execute the tool with potentially modified arguments
                    try:
                        tool_result = await self._execute_tool(
                            session, tool_info, tool_arguments
                        )
                        result_str = str(tool_result)
                    except Exception as e:
                        result_str = f"Error executing tool: {str(e)}"

                    # Publish tool call completed event
                    await publish_run_event(
                        str(run.id),
                        RunEventType.TOOL_CALL_COMPLETED,
                        {
                            "run_id": str(run.id),
                            "step_id": step.step_id,
                            "tool_name": tool_call.name,
                            "tool_call_id": tool_call.id,
                            "result": result_str[:500],  # First 500 chars
                        },
                    )

                    # Track tool call for agent summary
                    all_tool_calls.append({
                        "id": tool_call.id,
                        "tool_name": tool_call.name,
                        "arguments": tool_arguments,
                        "result": result_str,
                        "iteration": iteration,
                    })

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    })

            else:
                # No tool calls - agent is done
                step.status = StepStatus.COMPLETED
                final_output = response.content
                await session.commit()
                break

            await session.commit()

        # Publish completion event
        await publish_run_event(
            str(run.id),
            RunEventType.STEP_COMPLETED,
            {
                "run_id": str(run.id),
                "step_type": "sub_agent" if depth > 0 else "agent",
                "iterations": iteration,
                "tool_calls": tool_calls_count,
                "output": (final_output or "")[:500],
                "depth": depth,
            },
        )

        return {
            "status": "function_complete",
            "output": {
                "result": final_output,
                "iterations": iteration,
                "tool_calls_count": tool_calls_count,
                "tokens_used": tokens_used,
                "messages": messages,
                "tool_calls": all_tool_calls,
            },
        }

    def _synthesize_sub_agent_tools(
        self,
        sub_agents_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Synthesize tool definitions for sub-agents from agent_config.

        Sub-agents defined in agent_config.sub_agents are exposed as
        tools with a single ``task`` string parameter.
        """
        tools = []
        for name, config in sub_agents_config.items():
            description = config.get("description", f"Delegate a task to the '{name}' sub-agent.")
            tools.append({
                "name": name,
                "description": description,
                "schema": {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "task": {
                                    "type": "string",
                                    "description": "The task to delegate to the sub-agent.",
                                },
                            },
                            "required": ["task"],
                        },
                    },
                },
                "is_builtin": False,
                "code": None,
                "tool_type": "sub_agent",
                "webhook_url": None,
                "webhook_method": "POST",
                "webhook_headers": None,
                "tenant_id": None,
                "requires_approval": False,
                "approval_timeout": None,
                "is_sub_agent": True,
            })
        return tools

    async def _load_skill_instructions(
        self,
        session: AsyncSession,
        skill_ids: list[str],
        tenant_id: Any = None,
    ) -> str:
        """Load instructions from enabled skills and assemble into a knowledge block."""
        if not skill_ids:
            return ""

        from flowforge_server.db.models import SkillTemplate

        parts: list[str] = []
        for skill_id_str in skill_ids:
            try:
                skill_uuid = uuid.UUID(skill_id_str)
            except ValueError:
                continue

            result = await session.execute(
                select(SkillTemplate).where(
                    SkillTemplate.id == skill_uuid,
                    SkillTemplate.is_active == True,
                    or_(
                        SkillTemplate.tenant_id == tenant_id,
                        SkillTemplate.is_builtin == True,
                    ),
                )
            )
            skill = result.scalar_one_or_none()

            if skill and skill.instructions:
                source = (skill.source_metadata or {}).get("repo", skill.name)
                safe_name = html.escape(skill.name, quote=True)
                safe_source = html.escape(source, quote=True)
                safe_instructions = skill.instructions.replace("</skill-knowledge>", "")
                parts.append(
                    f'<skill-knowledge name="{safe_name}" source="{safe_source}">\n'
                    f"{safe_instructions}\n"
                    f"</skill-knowledge>"
                )

        return "\n\n".join(parts)

    async def _load_tools(
        self,
        session: AsyncSession,
        tool_names: list[str],
        tenant_id: Any = None,
    ) -> list[dict[str, Any]]:
        """Load tool definitions from database."""
        tools = []
        builtin_names = get_builtin_tool_names()

        for name in tool_names:
            # Query for tool (tenant-specific or built-in)
            result = await session.execute(
                select(Tool).where(
                    or_(
                        Tool.is_builtin == True,
                        Tool.tenant_id == tenant_id,
                    ),
                    Tool.name == name,
                    Tool.is_active == True,
                )
            )
            tool = result.scalar_one_or_none()

            if tool:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "schema": {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        },
                    },
                    "is_builtin": tool.is_builtin,
                    "code": tool.code,
                    "tool_type": getattr(tool, "tool_type", "custom"),
                    "webhook_url": getattr(tool, "webhook_url", None),
                    "webhook_method": getattr(tool, "webhook_method", "POST"),
                    "webhook_headers": getattr(tool, "webhook_headers", None),
                    "tenant_id": tool.tenant_id,
                    "requires_approval": tool.requires_approval,
                    "approval_timeout": tool.approval_timeout,
                })
            elif name in builtin_names:
                # Tool not in DB but is a known builtin - this shouldn't happen
                # after seeding, but handle gracefully
                log.warning("builtin_tool_not_in_database", tool_name=name)

        return tools

    async def _execute_tool(
        self,
        session: AsyncSession,
        tool_info: dict[str, Any],
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a tool with the given arguments."""
        if tool_info["is_builtin"]:
            return await execute_builtin_tool(tool_info["name"], arguments)
        elif tool_info.get("webhook_url"):
            return await self._execute_webhook_tool(session, tool_info, arguments)
        elif tool_info.get("code"):
            return await self._execute_custom_tool(tool_info["code"], arguments)
        else:
            return {"error": f"Tool '{tool_info['name']}' has no implementation"}

    async def _execute_webhook_tool(
        self,
        session: AsyncSession,
        tool_info: dict[str, Any],
        arguments: dict[str, Any],
    ) -> Any:
        """
        Execute a webhook-based tool by calling its configured URL.

        Resolves {{credential:name}} and {{env:VAR}} placeholders in
        the URL and headers before making the HTTP call.
        """
        tenant_id = tool_info.get("tenant_id")
        if not tenant_id:
            return {"error": "Webhook tool is missing tenant context"}

        try:
            # Resolve credential placeholders in URL
            url = await resolve_placeholders(
                tool_info["webhook_url"], tenant_id, session
            )

            # SSRF protection: block private/internal URLs
            try:
                validate_webhook_url(url)
            except ValueError as e:
                return {"error": str(e)}

            # Resolve credential placeholders in headers
            raw_headers = tool_info.get("webhook_headers") or {}
            headers = await resolve_dict_placeholders(
                raw_headers, tenant_id, session
            )

            method = (tool_info.get("webhook_method") or "POST").upper()

            client = await self._get_http_client()
            request_kwargs: dict[str, Any] = {
                "method": method,
                "url": url,
                "headers": headers,
            }
            if arguments and method in ("POST", "PUT", "PATCH"):
                request_kwargs["json"] = arguments
            elif arguments and method == "GET":
                request_kwargs["params"] = {
                    k: str(v) for k, v in arguments.items()
                }

            response = await client.request(**request_kwargs)

            try:
                body = response.json()
            except Exception:
                body = response.text[:10000]

            return {
                "status_code": response.status_code,
                "body": body,
            }

        except CredentialResolutionError as e:
            return {"error": f"Credential resolution failed: {str(e)}"}
        except httpx.TimeoutException:
            return {"error": "Webhook request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Webhook request failed: {str(e)}"}

    async def _execute_custom_tool(
        self,
        code: str,
        arguments: dict[str, Any],
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> Any:
        """
        Execute custom tool code in a sandboxed environment.

        The code should define a function called 'execute'.
        Example:
            def execute(query: str) -> dict:
                return {"result": f"Searched for {query}"}

        Security features:
        - Code is compiled with RestrictedPython
        - Only safe builtins are allowed (str, int, list, dict, etc.)
        - File I/O and dangerous imports are blocked
        - Timeout enforcement prevents infinite loops

        Args:
            code: Python source code defining an 'execute' function
            arguments: Arguments to pass to the execute function
            timeout_seconds: Maximum execution time (default 30s)

        Returns:
            Result from the execute function, or error dict on failure
        """
        try:
            result = await execute_sandboxed(
                code=code,
                arguments=arguments,
                timeout_seconds=timeout_seconds,
            )
            return result

        except SandboxTimeoutError:
            return {
                "error": f"Tool execution timed out after {timeout_seconds} seconds"
            }
        except SandboxSecurityError as e:
            return {
                "error": f"Security violation: {str(e)}"
            }
        except SandboxError as e:
            return {
                "error": f"Tool execution failed: {str(e)}"
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}"
            }

    async def _request_approval(
        self,
        session: AsyncSession,
        run: Run,
        step: Step,
        tool_call: ToolCall,
        tool_info: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Request approval for a tool call.

        This creates an approval record and publishes an event.
        The actual approval/rejection is handled by the approvals API.
        """
        # Parse timeout
        timeout_str = tool_info.get("approval_timeout", "1h")
        timeout_seconds = self._parse_timeout(timeout_str)
        timeout_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        # Create approval record
        approval = ToolApproval(
            run_id=run.id,
            step_id=step.id,
            tool_name=tool_call.name,
            tool_call_id=tool_call.id,
            tool_arguments=tool_call.arguments,
            status=ApprovalStatus.PENDING,
            requested_at=datetime.utcnow(),
            timeout_at=timeout_at,
        )
        session.add(approval)
        await session.commit()  # Commit so approval is visible to API

        # Publish approval required event
        await publish_run_event(
            str(run.id),
            RunEventType.APPROVAL_REQUIRED,
            {
                "run_id": str(run.id),
                "step_id": step.step_id,
                "approval_id": str(approval.id),
                "tool_name": tool_call.name,
                "tool_call_id": tool_call.id,
                "arguments": tool_call.arguments,
                "timeout_at": timeout_at.isoformat(),
            },
        )

        # Wait for approval resolution
        log.info(
            "waiting_for_approval",
            approval_id=str(approval.id),
            tool_name=tool_call.name,
            timeout_seconds=timeout_seconds,
        )

        # Poll for approval status with timeout
        poll_interval = 1.0  # Check every second
        elapsed = 0.0

        while elapsed < timeout_seconds:
            # Refresh the approval record to check for updates
            await session.refresh(approval)

            if approval.status == ApprovalStatus.APPROVED:
                log.info("approval_granted", approval_id=str(approval.id))
                return {
                    "status": "approved",
                    "modified_arguments": approval.modified_arguments,
                }

            if approval.status == ApprovalStatus.REJECTED:
                log.info(
                    "approval_rejected",
                    approval_id=str(approval.id),
                    reason=approval.rejection_reason,
                )
                return {
                    "status": "rejected",
                    "reason": approval.rejection_reason or "No reason provided",
                }

            if approval.status == ApprovalStatus.TIMEOUT:
                log.warning("approval_timeout", approval_id=str(approval.id))
                return {"status": "timeout"}

            # Wait before next poll
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout reached - update approval status
        approval.status = ApprovalStatus.TIMEOUT
        approval.resolved_at = datetime.utcnow()
        await session.commit()  # Commit timeout status

        log.warning(
            "approval_timeout_reached",
            approval_id=str(approval.id),
            elapsed_seconds=elapsed,
        )

        return {"status": "timeout"}

    def _parse_timeout(self, timeout_str: str) -> int:
        """Parse timeout string to seconds."""
        if timeout_str.endswith("h"):
            return int(timeout_str[:-1]) * 3600
        elif timeout_str.endswith("m"):
            return int(timeout_str[:-1]) * 60
        elif timeout_str.endswith("s"):
            return int(timeout_str[:-1])
        else:
            return int(timeout_str)
