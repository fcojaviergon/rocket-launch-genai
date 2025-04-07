from __future__ import annotations
from sqlalchemy import Column, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from database.models.base import BaseModel
import uuid
from typing import List, Optional, TYPE_CHECKING

# Import related types only for type checking to avoid circular imports
if TYPE_CHECKING:
    from database.models.user import User

class Conversation(BaseModel):
    """Model for conversations"""
    __tablename__ = "conversations"
    
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[List[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(BaseModel):
    """Model for messages in a conversation"""
    __tablename__ = "messages"
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'user', 'assistant', 'system'
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("conversations.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation: Mapped[Conversation] = relationship(back_populates="messages")
