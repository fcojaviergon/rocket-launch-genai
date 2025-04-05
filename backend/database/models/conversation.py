from sqlalchemy import Column, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import datetime
from database.models.base import BaseModel

class Conversation(BaseModel):
    """Model for conversations"""
    __tablename__ = "conversations"
    
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(BaseModel):
    """Model for messages in a conversation"""
    __tablename__ = "messages"
    
    content = Column(Text, nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    conversation_id = Column(UUID, ForeignKey("conversations.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
