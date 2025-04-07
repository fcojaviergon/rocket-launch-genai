from __future__ import annotations
from sqlalchemy import Column, String, Text, JSON, UUID, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database.models.base import BaseModel
import enum
from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
from typing import TYPE_CHECKING

# Import related types only for type checking to avoid circular imports
if TYPE_CHECKING:
    from database.models.user import User
    from database.models.document import Document

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
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    config_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="pipelines")
    executions: Mapped[List["PipelineExecution"]] = relationship(back_populates="pipeline", cascade="all, delete-orphan")

class PipelineExecution(BaseModel):
    """Model for pipeline executions"""
    __tablename__ = "pipeline_executions"
    
    # Additional columns
    pipeline_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("pipelines.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("documents.id"), nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    pipeline: Mapped["Pipeline"] = relationship(back_populates="executions")
    document: Mapped["Document"] = relationship(back_populates="pipeline_executions")
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="pipeline_executions") 