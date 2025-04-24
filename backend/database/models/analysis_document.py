"""
Models for document-pipeline associations
"""
from __future__ import annotations
from sqlalchemy import Column, String, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database.models.base import BaseModel
import enum
import uuid
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.document import Document
    from database.models.analysis import AnalysisPipeline

class DocumentRole(str, enum.Enum):
    """Enum for document roles in a pipeline"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUPPLEMENTARY = "supplementary"

class PipelineDocument(BaseModel):
    """Model for document-pipeline associations"""
    __tablename__ = "pipeline_documents"
    
    pipeline_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("analysis_pipelines.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("documents.id"), nullable=False)
    
    # Role of the document in the pipeline
    role: Mapped[DocumentRole] = mapped_column(Enum(DocumentRole), nullable=False, default=DocumentRole.PRIMARY)
    
    # Order for processing (lower numbers processed first)
    processing_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Relationships
    pipeline: Mapped["AnalysisPipeline"] = relationship(back_populates="pipeline_documents")
    document: Mapped["Document"] = relationship(back_populates="document_pipelines")
