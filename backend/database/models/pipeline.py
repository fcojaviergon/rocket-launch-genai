from sqlalchemy import Column, String, Text, JSON, UUID, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from database.models.base import BaseModel
import enum
from datetime import datetime
import uuid

class ExecutionStatus(str, enum.Enum):
    """Possible execution statuses for the pipeline"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class Pipeline(BaseModel):
    """Model for pipeline for document processing"""
    __tablename__ = "pipelines"
    
    # Additional columns
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    type = Column(String, nullable=True)
    steps = Column(JSON, nullable=False, default=list)
    config_metadata = Column(JSON, nullable=True)
    
    # Relationships
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="pipelines")
    executions = relationship("PipelineExecution", back_populates="pipeline", cascade="all, delete-orphan")

class PipelineExecution(BaseModel):
    """Model for pipeline executions"""
    __tablename__ = "pipeline_executions"
    
    # Additional columns
    pipeline_id = Column(UUID, ForeignKey("pipelines.id"), nullable=False)
    document_id = Column(UUID, ForeignKey("documents.id"), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    results = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    pipeline = relationship("Pipeline", back_populates="executions")
    document = relationship("Document", back_populates="pipeline_executions")
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="pipeline_executions") 