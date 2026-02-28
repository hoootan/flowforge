"""Base queue interface and job definitions."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    """Status of a job in the queue."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SCHEDULED = "scheduled"  # Delayed job


@dataclass
class Job:
    """
    Represents a job in the queue.

    Jobs are the unit of work processed by executors.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Job type identifier
    job_type: str = ""

    # The run this job belongs to
    run_id: str = ""

    # Function to execute
    function_id: str = ""

    # Tenant for multi-tenancy
    tenant_id: str = ""

    # Job payload data
    data: dict[str, Any] = field(default_factory=dict)

    # Job status
    status: JobStatus = JobStatus.PENDING

    # Priority (lower = higher priority)
    priority: int = 0

    # Retry tracking
    attempt: int = 1
    max_attempts: int = 3

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Error information
    error: str | None = None

    # Idempotency key
    idempotency_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary for serialization."""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "run_id": self.run_id,
            "function_id": self.function_id,
            "tenant_id": self.tenant_id,
            "data": self.data,
            "status": self.status.value,
            "priority": self.priority,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        """Create a Job from a dictionary."""

        def parse_datetime(value: str | None) -> datetime | None:
            if value is None:
                return None
            return datetime.fromisoformat(value)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            job_type=data.get("job_type", ""),
            run_id=data.get("run_id", ""),
            function_id=data.get("function_id", ""),
            tenant_id=data.get("tenant_id", ""),
            data=data.get("data", {}),
            status=JobStatus(data.get("status", "pending")),
            priority=data.get("priority", 0),
            attempt=data.get("attempt", 1),
            max_attempts=data.get("max_attempts", 3),
            created_at=parse_datetime(data.get("created_at")) or datetime.utcnow(),
            scheduled_at=parse_datetime(data.get("scheduled_at")),
            started_at=parse_datetime(data.get("started_at")),
            completed_at=parse_datetime(data.get("completed_at")),
            error=data.get("error"),
            idempotency_key=data.get("idempotency_key"),
        )


class Queue(ABC):
    """
    Abstract base class for queue implementations.

    Queues manage the lifecycle of jobs from enqueue to completion.
    """

    @abstractmethod
    async def enqueue(
        self,
        job: Job,
        delay: float | None = None,
    ) -> str:
        """
        Add a job to the queue.

        Args:
            job: The job to enqueue.
            delay: Optional delay in seconds before job becomes available.

        Returns:
            The job ID.
        """
        pass

    @abstractmethod
    async def dequeue(
        self,
        timeout: float = 0,
    ) -> Job | None:
        """
        Remove and return the next available job.

        Args:
            timeout: How long to wait for a job (0 = don't wait).

        Returns:
            The next job, or None if no jobs available.
        """
        pass

    @abstractmethod
    async def complete(self, job_id: str, result: Any = None) -> None:
        """
        Mark a job as completed.

        Args:
            job_id: The job ID.
            result: Optional result data.
        """
        pass

    @abstractmethod
    async def fail(
        self,
        job_id: str,
        error: str,
        retry: bool = True,
    ) -> bool:
        """
        Mark a job as failed.

        Args:
            job_id: The job ID.
            error: Error message.
            retry: Whether to retry the job.

        Returns:
            True if job will be retried, False otherwise.
        """
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Job | None:
        """
        Get a job by ID.

        Args:
            job_id: The job ID.

        Returns:
            The job, or None if not found.
        """
        pass

    @abstractmethod
    async def get_pending_count(self) -> int:
        """Get the number of pending jobs."""
        pass

    @abstractmethod
    async def get_running_count(self) -> int:
        """Get the number of running jobs."""
        pass

    async def schedule(
        self,
        job: Job,
        run_at: datetime,
    ) -> str:
        """
        Schedule a job to run at a specific time.

        Args:
            job: The job to schedule.
            run_at: When to run the job.

        Returns:
            The job ID.
        """
        delay = (run_at - datetime.utcnow()).total_seconds()
        if delay < 0:
            delay = 0
        job.scheduled_at = run_at
        job.status = JobStatus.SCHEDULED
        return await self.enqueue(job, delay=delay)
