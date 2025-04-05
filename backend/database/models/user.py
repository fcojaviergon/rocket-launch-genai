from sqlalchemy import Boolean, Column, String, ForeignKey
from sqlalchemy.orm import relationship
from database.models.base import BaseModel

class User(BaseModel):
    """Model for user"""
    __tablename__ = "users"
    
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(String, default="user")
    
    # Relationships - using strings to avoid circular imports
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    pipelines = relationship("Pipeline", back_populates="user", cascade="all, delete-orphan")
    pipeline_executions = relationship("PipelineExecution", back_populates="user", cascade="all, delete-orphan")