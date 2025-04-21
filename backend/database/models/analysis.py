from __future__ import annotations
from sqlalchemy import Column, String, Text, JSON, UUID, ForeignKey, Enum, DateTime, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
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
    from database.models.task import Task

class AnalysisScenario(BaseModel):
    """Model for analysis scenarios (e.g., "")"""
    __tablename__ = "analysis_scenarios"
    
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="analysis_scenarios")
    
    # Relationship with associated pipelines
    pipelines: Mapped[List["AnalysisPipeline"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")

class PipelineType(str, enum.Enum):
    """Enum for pipeline types"""
    RFP_ANALYSIS = "rfp_analysis"
    PROPOSAL_ANALYSIS = "proposal_analysis"

class AnalysisPipeline(BaseModel):
    """Base model for analysis pipelines"""
    __tablename__ = "analysis_pipelines"
    
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("analysis_scenarios.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("documents.id"), nullable=False)
    pipeline_type: Mapped[PipelineType] = mapped_column(Enum(PipelineType), nullable=False)
    parent_pipeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, ForeignKey("analysis_pipelines.id"), nullable=True)
    
    # Common pipeline results
    results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    scenario: Mapped["AnalysisScenario"] = relationship(back_populates="pipelines")
    document: Mapped["Document"] = relationship(back_populates="analysis_pipelines")
    tasks: Mapped[List["Task"]] = relationship(back_populates="analysis_pipeline")
    
    # Relationship with parent pipeline
    parent_pipeline: Mapped[Optional["AnalysisPipeline"]] = relationship(foreign_keys=[parent_pipeline_id], remote_side="AnalysisPipeline.id", backref="child_pipelines")
    
    # Relationship with embeddings
    embeddings: Mapped[List["PipelineEmbedding"]] = relationship(back_populates="pipeline", cascade="all, delete-orphan")
    
    # Discriminator column for inheritance
    __mapper_args__ = {
        "polymorphic_on": pipeline_type,
        "polymorphic_identity": None
    }

class RfpAnalysisPipeline(AnalysisPipeline):
    """Model for RFP analysis pipelines"""
    __tablename__ = "rfp_analysis_pipelines"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("analysis_pipelines.id"), primary_key=True)
    
    # RFP-specific results
    extracted_criteria: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    evaluation_framework: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    __mapper_args__ = {
        "polymorphic_identity": PipelineType.RFP_ANALYSIS,
    }


class ProposalAnalysisPipeline(AnalysisPipeline):
    """Model for proposal analysis pipelines"""
    __tablename__ = "proposal_analysis_pipelines"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("analysis_pipelines.id"), primary_key=True)
    
    # Proposal-specific results
    evaluation_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    technical_evaluation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    grammar_evaluation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    consistency_evaluation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    __mapper_args__ = {
        "polymorphic_identity": PipelineType.PROPOSAL_ANALYSIS,
    }


class PipelineEmbedding(BaseModel):
    """Model for pipeline embeddings"""
    __tablename__ = "pipeline_embeddings"
    
    pipeline_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("analysis_pipelines.id"), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_vector: Mapped[List[float]] = mapped_column(JSON, nullable=False)  # Use pgvector in production
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    pipeline: Mapped["AnalysisPipeline"] = relationship(back_populates="embeddings")
