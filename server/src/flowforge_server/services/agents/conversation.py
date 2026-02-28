"""Conversation management for agents.

Provides ConversationManager for tracking multi-turn conversations
with message history, context window management, and serialization.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class Message:
    """A message in the conversation."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None  # For tool messages
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to LLM-compatible message format."""
        msg: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }

        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls

        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id

        if self.name and self.role == "tool":
            msg["name"] = self.name

        return msg

    def to_full_dict(self) -> dict[str, Any]:
        """Convert to full dictionary including metadata."""
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            role=data["role"],
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
        )


class ConversationManager:
    """
    Manages multi-turn conversation state with persistence.

    Supports:
    - Message history with truncation/summarization
    - Context window management
    - Conversation branching/forking
    - Serialization for durable storage
    """

    def __init__(
        self,
        conversation_id: str | None = None,
        max_messages: int = 100,
        max_tokens: int = 100000,
    ) -> None:
        """
        Initialize the conversation manager.

        Args:
            conversation_id: Unique conversation identifier
            max_messages: Maximum messages to keep
            max_tokens: Maximum estimated tokens in history
        """
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.messages: list[Message] = []
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self._token_count = 0
        self._created_at = datetime.utcnow()
        self._updated_at = datetime.utcnow()

    def add_system_message(self, content: str) -> None:
        """Add a system message."""
        self._add_message(Message(role="system", content=content))

    def add_user_message(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a user message."""
        self._add_message(Message(
            role="user",
            content=content,
            metadata=metadata or {},
        ))

    def add_assistant_message(
        self,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add an assistant message."""
        self._add_message(Message(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            metadata=metadata or {},
        ))

    def add_tool_result(
        self,
        tool_call_id: str,
        name: str,
        result: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a tool result message."""
        content = result if isinstance(result, str) else json.dumps(result)
        self._add_message(Message(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            name=name,
            metadata=metadata or {},
        ))

    def add_message(self, message: Message) -> None:
        """Add a message directly."""
        self._add_message(message)

    def _add_message(self, message: Message) -> None:
        """Internal method to add a message with management."""
        self.messages.append(message)
        self._updated_at = datetime.utcnow()

        # Estimate tokens (rough: 4 chars per token)
        self._token_count += len(message.content) // 4

        # Enforce limits
        self._enforce_limits()

    def _enforce_limits(self) -> None:
        """Enforce message count and token limits."""
        # Keep system messages separate
        system_messages = [m for m in self.messages if m.role == "system"]
        other_messages = [m for m in self.messages if m.role != "system"]

        # Remove oldest non-system messages if over limit
        while len(other_messages) > self.max_messages - len(system_messages):
            removed = other_messages.pop(0)
            self._token_count -= len(removed.content) // 4

        # Recalculate tokens and check token limit
        self._token_count = sum(len(m.content) // 4 for m in system_messages + other_messages)
        while self._token_count > self.max_tokens and len(other_messages) > 1:
            removed = other_messages.pop(0)
            self._token_count -= len(removed.content) // 4

        # Rebuild messages list
        self.messages = system_messages + other_messages

    def to_messages(self) -> list[dict[str, Any]]:
        """Convert to LLM-compatible message format."""
        return [m.to_dict() for m in self.messages]

    def fork(self) -> ConversationManager:
        """Create a branch of this conversation."""
        forked = ConversationManager(
            conversation_id=str(uuid.uuid4()),
            max_messages=self.max_messages,
            max_tokens=self.max_tokens,
        )
        forked.messages = [
            Message.from_dict(m.to_full_dict())
            for m in self.messages
        ]
        forked._token_count = self._token_count
        return forked

    def get_last_assistant_message(self) -> Message | None:
        """Get the last assistant message."""
        for message in reversed(self.messages):
            if message.role == "assistant":
                return message
        return None

    def get_last_user_message(self) -> Message | None:
        """Get the last user message."""
        for message in reversed(self.messages):
            if message.role == "user":
                return message
        return None

    def clear_except_system(self) -> None:
        """Clear all messages except system messages."""
        self.messages = [m for m in self.messages if m.role == "system"]
        self._token_count = sum(len(m.content) // 4 for m in self.messages)
        self._updated_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "conversation_id": self.conversation_id,
            "messages": [m.to_full_dict() for m in self.messages],
            "max_messages": self.max_messages,
            "max_tokens": self.max_tokens,
            "token_count": self._token_count,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationManager:
        """Deserialize from storage."""
        manager = cls(
            conversation_id=data.get("conversation_id"),
            max_messages=data.get("max_messages", 100),
            max_tokens=data.get("max_tokens", 100000),
        )
        manager.messages = [
            Message.from_dict(m)
            for m in data.get("messages", [])
        ]
        manager._token_count = data.get("token_count", 0)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            manager._created_at = datetime.fromisoformat(created_at)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            manager._updated_at = datetime.fromisoformat(updated_at)

        return manager

    def __len__(self) -> int:
        """Return number of messages."""
        return len(self.messages)

    @property
    def token_count(self) -> int:
        """Estimated token count."""
        return self._token_count

    @property
    def created_at(self) -> datetime:
        """When conversation was created."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """When conversation was last updated."""
        return self._updated_at
