from __future__ import annotations
from sqlalchemy import Column, String, ForeignKey, Text, DateTime, ARRAY, JSON, Integer, Enum as SQLEnum
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
    from database.models.pipeline import PipelineExecution

# Define Enum for Processing Status
class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_PROCESSED = "not_processed" # Initial state before any processing is triggered

class Document(BaseModel):
    """Model for documents"""
    __tablename__ = "documents"
    
    # Columns using Mapped and mapped_column
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # e.g., PDF, DOCX, TXT
    process_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="documents")
    embeddings: Mapped[List[DocumentEmbedding]] = relationship(back_populates="document", cascade="all, delete-orphan")
    processing_results: Mapped[List[DocumentProcessingResult]] = relationship(back_populates="document", cascade="all, delete-orphan")
    pipeline_executions: Mapped[List[PipelineExecution]] = relationship(back_populates="document")
    processing_status = Column(
        SQLEnum(ProcessingStatus, name="processing_status_enum", create_type=False), # Use SQLEnum, create_type=False if using Alembic
        nullable=False,
        default=ProcessingStatus.NOT_PROCESSED,
        server_default=ProcessingStatus.NOT_PROCESSED.value,
        index=True # Add index if frequently queried by status
    )
    
    # Add field for storing processing errors
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class DocumentEmbedding(BaseModel):
    """Model for document embeddings"""
    __tablename__ = "document_embeddings"
    
    document_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)
    chunk_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    document: Mapped[Document] = relationship(back_populates="embeddings")

    def __repr__(self):
        return f'<Document {self.document.title} ({self.id})>'

class DocumentProcessingResult(BaseModel):
    """Model for document processing results"""
    __tablename__ = "document_processing_results"
    
    document_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    pipeline_name: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    process_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    document: Mapped[Document] = relationship(back_populates="processing_results")
