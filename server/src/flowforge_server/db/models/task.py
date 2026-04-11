"""Task model for project management / Kanban board."""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.agent import Agent
    from flowforge_server.db.models.comment import Comment
    from flowforge_server.db.models.tenant import Tenant
    from flowforge_server.db.models.user import User


class TaskStatus(str, enum.Enum):
    """Task status for Kanban board."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    """Task priority levels."""

    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class Task(Base, TimestampMixin):
    """
    Task / issue for project management.

    Tasks can be assigned to humans or agents, support
    a Kanban workflow, and can trigger FlowForge functions.
    """

    __tablename__ = "tasks"

    __table_args__ = (
        UniqueConstraint("tenant_id", "identifier", name="uq_task_tenant_identifier"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-readable identifier (e.g., FF-1, FF-2)
    identifier: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Sequence number for auto-incrementing within tenant
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    # Task title
    title: Mapped[str] = mapped_column(String(500), nullable=False)

    # Rich text description (markdown)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status for Kanban
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskStatus.TODO.value,
        server_default=TaskStatus.TODO.value,
        index=True,
    )

    # Priority
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskPriority.NONE.value,
        server_default=TaskPriority.NONE.value,
    )

    # Labels / tags
    labels: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Assignee - can be a user OR an agent
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assignee_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Creator
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Parent task for sub-tasks
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Link to FlowForge function (bridge PM → orchestration)
    function_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("functions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Link to run (set when task triggers a run)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Metadata (attribute renamed to avoid conflict with SQLAlchemy's MetaData)
    task_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="tasks")
    assignee_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assignee_user_id], lazy="selectin"
    )
    assignee_agent: Mapped["Agent | None"] = relationship(
        "Agent", foreign_keys=[assignee_agent_id], lazy="selectin"
    )
    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by_user_id], lazy="selectin"
    )
    parent_task: Mapped["Task | None"] = relationship(
        "Task", remote_side=[id], foreign_keys=[parent_task_id], lazy="noload"
    )
    sub_tasks: Mapped[list["Task"]] = relationship(
        "Task", foreign_keys=[parent_task_id], lazy="noload"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="task", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Task {self.identifier}: {self.title[:40]}>"

    @property
    def assignee_type(self) -> str | None:
        """Return 'user', 'agent', or None."""
        if self.assignee_user_id:
            return "user"
        if self.assignee_agent_id:
            return "agent"
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response dict."""
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "labels": self.labels,
            "assignee_type": self.assignee_type,
            "assignee_user_id": str(self.assignee_user_id) if self.assignee_user_id else None,
            "assignee_agent_id": str(self.assignee_agent_id) if self.assignee_agent_id else None,
            "assignee_user": {
                "id": str(self.assignee_user.id),
                "name": self.assignee_user.name,
                "email": self.assignee_user.email,
            } if self.assignee_user else None,
            "assignee_agent": {
                "id": str(self.assignee_agent.id),
                "name": self.assignee_agent.name,
                "slug": self.assignee_agent.slug,
                "avatar_url": self.assignee_agent.avatar_url,
                "status": self.assignee_agent.status,
            } if self.assignee_agent else None,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "parent_task_id": str(self.parent_task_id) if self.parent_task_id else None,
            "function_id": str(self.function_id) if self.function_id else None,
            "run_id": str(self.run_id) if self.run_id else None,
            "sub_tasks_count": len(self.sub_tasks) if "sub_tasks" in self.__dict__ and self.sub_tasks else 0,
            "comments_count": len(self.comments) if "comments" in self.__dict__ and self.comments else 0,
            "metadata": self.task_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
