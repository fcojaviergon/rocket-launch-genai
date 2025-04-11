"""
Defines the SQLAlchemy models for agent conversations and messages.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from typing import TYPE_CHECKING

from sqlalchemy import Column, String, Text, JSON, UUID, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from database.models.base import BaseModel


# Import related types only for type checking to avoid circular imports
if TYPE_CHECKING:
    from database.models.user import User # Assuming User model exists

class AgentConversation(BaseModel):
    """
    Represents a single conversation instance with the agent.
    """
    __tablename__ = "agent_conversations"

    # Foreign key to the user who initiated the conversation
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Optional field for storing arbitrary metadata related to the conversation
    # Using metadata_info because 'metadata' can be reserved in SQLAlchemy setups
    # metadata_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # The user who owns this conversation
    user: Mapped[User] = relationship(back_populates="agent_conversations")
    # Messages belonging to this conversation, ordered by creation time
    messages: Mapped[List[AgentMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentMessage.created_at"
    )

class AgentMessage(BaseModel):
    """
    Represents a single message within an agent conversation.
    """
    __tablename__ = "agent_messages"

    # Foreign key to the conversation this message belongs to
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_conversations.id"), nullable=False, index=True)
    # Role of the message sender (e.g., 'user', 'assistant', 'system', 'tool')
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    # The actual content of the message
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Whether the message should be visible to the user
    visible: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Optional field for storing structured tool call/result info
    # tool_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # The conversation this message is part of
    conversation: Mapped["AgentConversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<AgentMessage(id={self.id}, role='{self.role}', conversation_id={self.conversation_id})>" 