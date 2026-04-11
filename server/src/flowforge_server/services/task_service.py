"""Task automation service — bridges tasks with the event/execution pipeline."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models import Event, Function, Run, RunStatus
from flowforge_server.db.models.agent import Agent
from flowforge_server.db.models.comment import Comment
from flowforge_server.db.models.notification import Notification
from flowforge_server.db.models.task import Task, TaskStatus
from flowforge_server.logging import Loggers
from flowforge_server.stream import RedisEventStream, StreamMessage

log = Loggers.api()


class TaskService:
    """Bridges task CRUD with the event/function/agent execution pipeline."""

    MAX_TASK_EVENT_DEPTH = 3

    def __init__(self, event_stream: RedisEventStream) -> None:
        self.event_stream = event_stream

    async def on_task_created(
        self,
        session: AsyncSession,
        task: Task,
        *,
        _depth: int = 0,
    ) -> None:
        """
        Handle a newly created task.

        Emits a ``task/created`` event and, if the task is already assigned
        to an agent with a linked function, kicks off agent execution.
        """
        await self._emit_task_event(
            session,
            task.tenant_id,
            "task/created",
            {
                "task_id": str(task.id),
                "identifier": task.identifier,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "assignee_agent_id": str(task.assignee_agent_id) if task.assignee_agent_id else None,
                "assignee_user_id": str(task.assignee_user_id) if task.assignee_user_id else None,
                "function_id": str(task.function_id) if task.function_id else None,
                "metadata": task.task_metadata,
            },
            _depth=_depth,
        )

        if task.assignee_agent_id and task.function_id:
            await self._maybe_trigger_agent_execution(session, task, _depth=_depth)

    async def on_task_updated(
        self,
        session: AsyncSession,
        task: Task,
        changes: dict[str, Any],
        previous_values: dict[str, Any],
        *,
        _depth: int = 0,
    ) -> None:
        """
        Handle task field changes.

        Emits targeted events for assignment and status transitions, creates
        notifications for affected users, and triggers agent execution when
        appropriate.
        """
        agent_assigned = (
            "assignee_agent_id" in changes
            and changes["assignee_agent_id"] is not None
        )
        user_assigned = (
            "assignee_user_id" in changes
            and changes["assignee_user_id"] is not None
        )
        status_changed = "status" in changes

        if agent_assigned:
            await self._emit_task_event(
                session,
                task.tenant_id,
                "task/assigned",
                {
                    "task_id": str(task.id),
                    "identifier": task.identifier,
                    "title": task.title,
                    "assignee_type": "agent",
                    "assignee_agent_id": str(task.assignee_agent_id),
                    "previous_assignee_agent_id": str(previous_values.get("assignee_agent_id"))
                    if previous_values.get("assignee_agent_id") else None,
                },
                _depth=_depth,
            )

        if user_assigned:
            await self._emit_task_event(
                session,
                task.tenant_id,
                "task/assigned",
                {
                    "task_id": str(task.id),
                    "identifier": task.identifier,
                    "title": task.title,
                    "assignee_type": "user",
                    "assignee_user_id": str(task.assignee_user_id),
                    "previous_assignee_user_id": str(previous_values.get("assignee_user_id"))
                    if previous_values.get("assignee_user_id") else None,
                },
                _depth=_depth,
            )
            self._create_notification(
                session,
                user_id=task.assignee_user_id,
                notification_type="task_assigned",
                title=f"You've been assigned to {task.identifier}",
                body=task.title,
                resource_type="task",
                resource_id=str(task.id),
                data={"task_id": str(task.id), "identifier": task.identifier},
            )

        if status_changed:
            await self._emit_task_event(
                session,
                task.tenant_id,
                "task/status_changed",
                {
                    "task_id": str(task.id),
                    "identifier": task.identifier,
                    "title": task.title,
                    "status": task.status,
                    "previous_status": previous_values.get("status"),
                },
                _depth=_depth,
            )

            if task.status == TaskStatus.DONE.value:
                await self._emit_task_event(
                    session,
                    task.tenant_id,
                    "task/completed",
                    {
                        "task_id": str(task.id),
                        "identifier": task.identifier,
                        "title": task.title,
                    },
                    _depth=_depth,
                )
                if task.created_by_user_id:
                    self._create_notification(
                        session,
                        user_id=task.created_by_user_id,
                        notification_type="task_completed",
                        title=f"{task.identifier} is done",
                        body=task.title,
                        resource_type="task",
                        resource_id=str(task.id),
                        data={"task_id": str(task.id), "identifier": task.identifier},
                    )

        # If agent was newly assigned and a function is linked, trigger execution
        if agent_assigned and task.function_id:
            await self._maybe_trigger_agent_execution(session, task, _depth=_depth)

    async def on_run_completed(self, session: AsyncSession, run: Run) -> None:
        """
        Update linked task when a run finishes successfully.

        Sets task status to DONE, posts a system comment with the output
        summary, and notifies the task creator.
        """
        result = await session.execute(
            select(Task).where(Task.run_id == run.id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            return

        try:
            task.status = TaskStatus.DONE.value

            output_summary = _summarise_run_output(run)
            self._create_system_comment(
                session,
                task_id=task.id,
                content=f"Run completed successfully. {output_summary}",
                comment_type="system",
                agent_id=None,
                run_id=run.id,
            )

            if task.created_by_user_id:
                self._create_notification(
                    session,
                    user_id=task.created_by_user_id,
                    notification_type="task_completed",
                    title=f"{task.identifier} completed",
                    body=f"The run for '{task.title}' finished successfully.",
                    resource_type="task",
                    resource_id=str(task.id),
                    data={
                        "task_id": str(task.id),
                        "identifier": task.identifier,
                        "run_id": str(run.id),
                    },
                )

            await session.commit()
        except Exception as exc:
            log.warning(
                "task_service.on_run_completed.error",
                task_id=str(task.id),
                run_id=str(run.id),
                error=str(exc),
            )
            await session.rollback()

    async def on_run_failed(self, session: AsyncSession, run: Run) -> None:
        """
        Update linked task when a run fails.

        Sets task status to BLOCKED, posts a system comment with the error,
        and notifies the task creator.
        """
        result = await session.execute(
            select(Task).where(Task.run_id == run.id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            return

        try:
            task.status = TaskStatus.BLOCKED.value

            error_summary = _summarise_run_error(run)
            self._create_system_comment(
                session,
                task_id=task.id,
                content=f"Run failed. {error_summary}",
                comment_type="system",
                agent_id=None,
                run_id=run.id,
            )

            if task.created_by_user_id:
                self._create_notification(
                    session,
                    user_id=task.created_by_user_id,
                    notification_type="run_failed",
                    title=f"{task.identifier} is blocked",
                    body=f"The run for '{task.title}' failed: {error_summary}",
                    resource_type="task",
                    resource_id=str(task.id),
                    data={
                        "task_id": str(task.id),
                        "identifier": task.identifier,
                        "run_id": str(run.id),
                        "error": run.error,
                    },
                )

            await session.commit()
        except Exception as exc:
            log.warning(
                "task_service.on_run_failed.error",
                task_id=str(task.id),
                run_id=str(run.id),
                error=str(exc),
            )
            await session.rollback()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _maybe_trigger_agent_execution(
        self,
        session: AsyncSession,
        task: Task,
        *,
        _depth: int = 0,
    ) -> None:
        """Resolve agent and function, then delegate to _trigger_agent_execution."""
        try:
            agent_result = await session.execute(
                select(Agent).where(Agent.id == task.assignee_agent_id)
            )
            agent = agent_result.scalar_one_or_none()

            function_result = await session.execute(
                select(Function).where(Function.id == task.function_id)
            )
            function = function_result.scalar_one_or_none()

            if agent is None:
                log.warning(
                    "task_service.trigger_agent_execution.agent_not_found",
                    task_id=str(task.id),
                    assignee_agent_id=str(task.assignee_agent_id),
                )
                return

            if function is None:
                log.warning(
                    "task_service.trigger_agent_execution.function_not_found",
                    task_id=str(task.id),
                    function_id=str(task.function_id),
                )
                return

            await self._trigger_agent_execution(session, task, agent, function)
        except Exception as exc:
            log.warning(
                "task_service.maybe_trigger_agent_execution.error",
                task_id=str(task.id),
                error=str(exc),
            )

    async def _trigger_agent_execution(
        self,
        session: AsyncSession,
        task: Task,
        agent: Agent,
        function: Function,
    ) -> None:
        """
        Create a Run for the task and publish it to the stream for the Runner.

        Skips execution if an existing non-terminal run is already linked.
        """
        # Guard: skip if a live run already exists for this task
        if task.run_id is not None:
            existing_result = await session.execute(
                select(Run).where(Run.id == task.run_id)
            )
            existing_run = existing_result.scalar_one_or_none()
            if existing_run is not None and not existing_run.is_terminal:
                log.info(
                    "task_service.trigger_agent_execution.skipped_active_run",
                    task_id=str(task.id),
                    run_id=str(task.run_id),
                    run_status=existing_run.status,
                )
                return

        try:
            now = datetime.utcnow()
            event_id = str(uuid.uuid4())
            max_attempts = getattr(function, "retries", 2) + 1

            run = Run(
                tenant_id=task.tenant_id,
                function_id=function.id,
                status=RunStatus.PENDING,
                trigger_type="event",
                trigger_data={
                    "event": {
                        "name": "task/assigned",
                        "data": {
                            "task_id": str(task.id),
                            "identifier": task.identifier,
                            "title": task.title,
                            "description": task.description,
                            "metadata": task.task_metadata,
                        },
                    }
                },
                attempt=1,
                max_attempts=max_attempts,
            )
            session.add(run)
            await session.flush()  # populate run.id

            task.run_id = run.id
            task.status = TaskStatus.IN_PROGRESS.value

            self._create_system_comment(
                session,
                task_id=task.id,
                content=f"Agent '{agent.name}' started working on this task",
                comment_type="system",
                agent_id=agent.id,
                run_id=run.id,
            )

            await session.commit()

            # Publish to stream so the Runner picks it up
            message = StreamMessage(
                id=str(run.id),
                event_name="task/assigned",
                event_id=event_id,
                event_data={
                    "task_id": str(task.id),
                    "identifier": task.identifier,
                    "title": task.title,
                    "description": task.description,
                    "metadata": task.task_metadata,
                },
                tenant_id=str(task.tenant_id),
                timestamp=now,
                run_id=str(run.id),
            )
            await self.event_stream.publish(message)

            log.info(
                "task_service.trigger_agent_execution.run_created",
                task_id=str(task.id),
                run_id=str(run.id),
                agent_id=str(agent.id),
                function_id=str(function.id),
            )
        except Exception as exc:
            log.warning(
                "task_service.trigger_agent_execution.error",
                task_id=str(task.id),
                agent_id=str(agent.id),
                function_id=str(function.id),
                error=str(exc),
            )
            await session.rollback()

    async def _emit_task_event(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        event_name: str,
        event_data: dict[str, Any],
        *,
        _depth: int = 0,
    ) -> None:
        """
        Persist an Event record and publish it to the stream.

        Depth tracking prevents circular automation chains from running
        indefinitely.
        """
        if _depth >= self.MAX_TASK_EVENT_DEPTH:
            log.warning(
                "task_service.emit_task_event.depth_limit_reached",
                event_name=event_name,
                depth=_depth,
            )
            return

        enriched_data = {
            **event_data,
            "_task_event_depth": _depth + 1,
            "_source": "automation",
        }

        try:
            event_id = str(uuid.uuid4())
            now = datetime.utcnow()

            event = Event(
                tenant_id=tenant_id,
                event_id=event_id,
                name=event_name,
                data=enriched_data,
                timestamp=now,
                received_at=now,
                processed=False,
            )
            session.add(event)
            await session.flush()

            # Check for registered functions that match this event
            functions_result = await session.execute(
                select(Function).where(
                    Function.tenant_id == tenant_id,
                    Function.trigger_type == "event",
                    Function.trigger_value == event_name,
                    Function.is_active == True,  # noqa: E712
                )
            )
            matching_functions = list(functions_result.scalars().all())

            run_id: str | None = None

            if matching_functions:
                # Create a pending run for the first matching function.
                # Additional functions would each need their own run — callers
                # creating more targeted automation should wire that up explicitly.
                function = matching_functions[0]
                max_attempts = getattr(function, "retries", 2) + 1
                run = Run(
                    tenant_id=tenant_id,
                    function_id=function.id,
                    event_id=event.id,
                    status=RunStatus.PENDING,
                    trigger_type="event",
                    trigger_data={"event": {"name": event_name, "data": enriched_data}},
                    attempt=1,
                    max_attempts=max_attempts,
                )
                session.add(run)
                await session.flush()
                run_id = str(run.id)

            event.processed = True
            await session.commit()

            message = StreamMessage(
                id=str(event.id),
                event_name=event_name,
                event_id=event_id,
                event_data=enriched_data,
                tenant_id=str(tenant_id),
                timestamp=now,
                run_id=run_id,
            )
            await self.event_stream.publish(message)

            log.info(
                "task_service.emit_task_event",
                event_name=event_name,
                event_id=event_id,
                tenant_id=str(tenant_id),
                depth=_depth,
                matched_functions=len(matching_functions),
            )
        except Exception as exc:
            log.warning(
                "task_service.emit_task_event.error",
                event_name=event_name,
                tenant_id=str(tenant_id),
                error=str(exc),
            )
            await session.rollback()

    def _create_notification(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        body: str | None,
        resource_type: str | None,
        resource_id: str | None,
        data: dict[str, Any],
    ) -> Notification:
        """
        Build and stage a Notification record.

        Does NOT commit — caller is responsible for the transaction boundary.
        """
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            resource_type=resource_type,
            resource_id=resource_id,
            data=data,
            is_read=False,
            is_archived=False,
        )
        session.add(notification)
        return notification

    def _create_system_comment(
        self,
        session: AsyncSession,
        task_id: uuid.UUID,
        content: str,
        comment_type: str,
        agent_id: uuid.UUID | None,
        run_id: uuid.UUID | None,
    ) -> Comment:
        """
        Build and stage a Comment record.

        Does NOT commit — caller is responsible for the transaction boundary.
        """
        comment = Comment(
            task_id=task_id,
            run_id=run_id,
            content=content,
            comment_type=comment_type,
            author_agent_id=agent_id,
            author_user_id=None,
            mentions=[],
            reactions={},
        )
        session.add(comment)
        return comment


# ------------------------------------------------------------------
# Private module-level helpers
# ------------------------------------------------------------------


def _summarise_run_output(run: Run) -> str:
    """Return a short human-readable summary of a completed run's output."""
    if not run.output:
        return ""
    if isinstance(run.output, dict):
        result = run.output.get("result") or run.output.get("output") or run.output.get("message")
        if result and isinstance(result, str):
            return result[:200]
        return ""
    return str(run.output)[:200]


def _summarise_run_error(run: Run) -> str:
    """Return a short human-readable summary of a failed run's error."""
    if not run.error:
        return "An unknown error occurred."
    if isinstance(run.error, dict):
        message = run.error.get("message") or run.error.get("error") or run.error.get("detail")
        if message and isinstance(message, str):
            return message[:300]
        return str(run.error)[:300]
    return str(run.error)[:300]
