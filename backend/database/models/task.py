from __future__ import annotations
from sqlalchemy import Column, String, Text, JSON, UUID, ForeignKey, Enum, Integer, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database.models.base import BaseModel
import enum
from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.user import User
    from database.models.document import Document
    from database.models.analysis import AnalysisPipeline

class TaskStatus(str, enum.Enum):
    """Possible task statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELED = "canceled"

class TaskType(str, enum.Enum):
    """Types of tasks in the system"""
    DOCUMENT_PROCESSING = "document_processing"
    RFP_ANALYSIS = "rfp_analysis"
    PROPOSAL_ANALYSIS = "proposal_analysis"
    OTHER = "other"

class TaskPriority(str, enum.Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class Task(BaseModel):
    """
    Centralized model for tracking all background tasks in the system
    """
    __tablename__ = "tasks"
    
    # Task identification and metadata
    task_id: Mapped[str] = mapped_column(String, nullable=False, index=True)  # Celery task ID
    name: Mapped[str] = mapped_column(String, nullable=False)  # Task name (function)
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False, index=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), default=TaskPriority.NORMAL, nullable=False)
    
    # Execution timing
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Execution details
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Task parameters and context
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 'pipeline', 'document', etc.
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)  # Reference to the source entity
    
    # User who created this task
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, ForeignKey("users.id"), nullable=True)
    user: Mapped[Optional["User"]] = relationship(back_populates="tasks")
    
    # Relationship with analysis pipeline
    analysis_pipeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, ForeignKey("analysis_pipelines.id"), nullable=True)
    analysis_pipeline: Mapped[Optional["AnalysisPipeline"]] = relationship(back_populates="tasks")
    
    # Relationship with document
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, ForeignKey("documents.id"), nullable=True)
    document: Mapped[Optional["Document"]] = relationship(back_populates="tasks")
    
    def __repr__(self):
        return f"<Task {self.id}: {self.name} ({self.status})>"