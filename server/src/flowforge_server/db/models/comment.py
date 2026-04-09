"""Comment model for collaboration layer."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge_server.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from flowforge_server.db.models.agent import Agent
    from flowforge_server.db.models.task import Task
    from flowforge_server.db.models.user import User


class Comment(Base, TimestampMixin):
    """
    Comment on a task or run.

    Supports both human and agent authors for unified activity timeline.
    """

    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Parent entity - task or run
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Author - either user or agent
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    author_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Comment content (markdown)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Comment type for activity timeline
    comment_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="comment",
        server_default="comment",
    )
    # Types: "comment", "status_change", "assignment", "blocker", "system"

    # Mentions extracted from content (@user, @agent)
    mentions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Reactions (emoji -> list of user IDs)
    reactions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    task: Mapped["Task | None"] = relationship("Task", back_populates="comments")
    author_user: Mapped["User | None"] = relationship("User", foreign_keys=[author_user_id])
    author_agent: Mapped["Agent | None"] = relationship("Agent", foreign_keys=[author_agent_id])

    def __repr__(self) -> str:
        return f"<Comment {str(self.id)[:8]} on task={self.task_id}>"

    @property
    def author_type(self) -> str:
        """Return 'user', 'agent', or 'system'."""
        if self.author_user_id:
            return "user"
        if self.author_agent_id:
            return "agent"
        return "system"

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response dict."""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id) if self.task_id else None,
            "run_id": str(self.run_id) if self.run_id else None,
            "author_type": self.author_type,
            "author_user_id": str(self.author_user_id) if self.author_user_id else None,
            "author_agent_id": str(self.author_agent_id) if self.author_agent_id else None,
            "author": self._author_dict(),
            "content": self.content,
            "comment_type": self.comment_type,
            "mentions": self.mentions,
            "reactions": self.reactions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def _author_dict(self) -> dict[str, Any] | None:
        """Get author info dict."""
        if self.author_user:
            return {
                "id": str(self.author_user.id),
                "name": self.author_user.name,
                "email": self.author_user.email,
                "type": "user",
            }
        if self.author_agent:
            return {
                "id": str(self.author_agent.id),
                "name": self.author_agent.name,
                "avatar_url": self.author_agent.avatar_url,
                "type": "agent",
            }
        return {"type": "system", "name": "System"}
