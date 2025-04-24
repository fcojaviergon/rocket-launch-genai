from __future__ import annotations
from sqlalchemy import Column, String, ForeignKey, Text, DateTime, ARRAY, JSON, Integer, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from database.models.base import BaseModel
import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from sqlalchemy.sql import func
import enum

# Import related types only for type checking to avoid circular imports
if TYPE_CHECKING:
    from database.models.user import User
    from database.models.analysis import AnalysisPipeline
    from database.models.task import Task
    from database.models.analysis_document import PipelineDocument

# Define Enum for Processing Status
class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_PROCESSED = "NOT_PROCESSED" # Initial state before any processing is triggered

class Document(BaseModel):
    """Model for documents"""
    __tablename__ = "documents"
    
    # Columns using Mapped and mapped_column
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # e.g., PDF, DOCX, TXT
    process_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="documents")
    tasks: Mapped[List[Task]] = relationship(back_populates="document")
    document_pipelines: Mapped[List["PipelineDocument"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    # Nota: La relación con document_embeddings ha sido eliminada en favor de pipeline_embeddings
    # Especificar el nombre exacto del enum en la base de datos
    processing_status: Mapped[ProcessingStatus] = mapped_column(Enum(ProcessingStatus, name="processing_status_enum"), nullable=False, default="NOT_PROCESSED", server_default="NOT_PROCESSED", index=True)
    
    # Add field for storing processing errors
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)