"""Inline executor for serverless/agent-based functions.

This module handles execution of inline functions that don't require
an external worker. It runs the agent loop directly within FlowForge.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models import Function, Tool, Run, Step, StepStatus, StepType, ToolApproval, ApprovalStatus
from flowforge_server.services.ai import AIService, AIResponse, ToolCall
from flowforge_server.services.builtin_tools import execute_builtin_tool, get_builtin_tool_names
from flowforge_server.services.sandbox import (
    execute_sandboxed,
    SandboxError,
    SandboxTimeoutError,
    SandboxSecurityError,
    DEFAULT_TIMEOUT_SECONDS,
)
from flowforge_server.stream.pubsub import publish_run_event, RunEventType
from flowforge_server.logging import Loggers

log = Loggers.inline_executor()


class InlineExecutor:
    """
    Executes inline/serverless functions directly within FlowForge.

    For inline functions (is_inline=True), this executor:
    1. Loads the function's tools from the database
    2. Runs an agent loop with the AI service
    3. Handles tool calls (including approval flows)
    4. Returns the final result
    """

    def __init__(self, ai_service: AIService) -> None:
        self.ai_service = ai_service

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

        # Load tools
        tools = await self._load_tools(session, fn.tools_config or [])

        # Get the task from event data
        task = event_data.get("prompt", "")
        if not task:
            return {
                "status": "error",
                "error": {"type": "ValidationError", "message": "No prompt provided"},
            }

        # Build initial messages
        messages = []
        if fn.system_prompt:
            messages.append({"role": "system", "content": fn.system_prompt})
        messages.append({"role": "user", "content": task})

        # Run agent loop
        iteration = 0
        tool_calls_count = 0
        tokens_used = {"prompt": 0, "completion": 0, "total": 0}
        final_output = None

        await publish_run_event(
            str(run.id),
            RunEventType.THINKING,
            {
                "run_id": str(run.id),
                "model": model,
                "status": "agent_started",
                "task": task[:200],  # First 200 chars
            },
        )

        while iteration < max_iterations and tool_calls_count < max_tool_calls:
            iteration += 1

            # Check for existing step (for retries)
            step_hash = f"agent:{run.id}:{iteration}"
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
                step = Step(
                    run_id=run.id,
                    step_id=f"agent-iteration-{iteration}",
                    step_hash=step_hash,
                    step_type=StepType.AI,
                    status=StepStatus.RUNNING,
                    started_at=datetime.utcnow(),
                )
                session.add(step)

            await session.flush()

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

            # Track token usage
            if response.usage:
                tokens_used["prompt"] += response.usage.prompt_tokens
                tokens_used["completion"] += response.usage.completion_tokens
                tokens_used["total"] += response.usage.total_tokens

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
                "step_type": "agent",
                "iterations": iteration,
                "tool_calls": tool_calls_count,
                "output": (final_output or "")[:500],
            },
        )

        return {
            "status": "function_complete",
            "output": {
                "result": final_output,
                "iterations": iteration,
                "tool_calls_count": tool_calls_count,
                "tokens_used": tokens_used,
            },
        }

    async def _load_tools(
        self,
        session: AsyncSession,
        tool_names: list[str],
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
                        # TODO: Add tenant_id filter when multi-tenancy is implemented
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
            # Use built-in executor
            return await execute_builtin_tool(tool_info["name"], arguments)
        elif tool_info.get("code"):
            # Execute custom code
            return await self._execute_custom_tool(tool_info["code"], arguments)
        else:
            return {"error": f"Tool '{tool_info['name']}' has no implementation"}

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
