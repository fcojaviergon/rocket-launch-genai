"""
Schemas for analysis scenarios and pipelines
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from database.models.analysis import PipelineType

# Base schemas
class AnalysisScenarioBase(BaseModel):
    """Base schema for analysis scenarios"""
    name: str
    description: Optional[str] = None
    metadata_config: Optional[Dict[str, Any]] = None

class AnalysisPipelineBase(BaseModel):
    """Base schema for analysis pipelines"""
    document_ids: Optional[List[UUID]] = None
    pipeline_type: PipelineType

# Create schemas
class AnalysisScenarioCreate(AnalysisScenarioBase):
    """Schema for creating analysis scenarios"""
    pass

class RfpPipelineCreate(AnalysisPipelineBase):
    """Schema for creating RFP analysis pipelines"""
    pipeline_type: PipelineType = PipelineType.RFP_ANALYSIS

class ProposalPipelineCreate(AnalysisPipelineBase):
    """Schema for creating proposal analysis pipelines"""
    pipeline_type: PipelineType = PipelineType.PROPOSAL_ANALYSIS
    rfp_pipeline_id: UUID

# Response schemas
class AnalysisScenarioResponse(AnalysisScenarioBase):
    """Schema for analysis scenario responses"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PipelineDocumentInfo(BaseModel):
    """Schema for document information in a pipeline"""
    document_id: UUID
    title: str
    role: str
    processing_order: int

class AnalysisPipelineResponse(AnalysisPipelineBase):
    """Base schema for analysis pipeline responses"""
    id: UUID
    scenario_id: UUID
    parent_pipeline_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: str = "pending"
    completed_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    associated_documents: Optional[List[PipelineDocumentInfo]] = None

    class Config:
        from_attributes = True


class RfpAnalysisPipelineResponse(AnalysisPipelineResponse):
    """Schema for RFP analysis pipeline responses"""
    # RFP-specific results
    extracted_criteria: Optional[Dict[str, Any]] = None
    evaluation_framework: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    document_ids: Optional[List[UUID]] = None

    class Config:
        from_attributes = True


class EvaluationScore(BaseModel):
    """Schema for evaluation scores"""
    score: float = Field(ge=0.0, le=1.0)
    justification: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)

class CriterionEvaluation(BaseModel):
    """Schema for criterion evaluation"""
    criterion_id: str
    criterion_name: str
    score: float = Field(ge=0.0, le=1.0)
    justification: str
    evidence: Optional[List[str]] = None

class ProposalEvaluationResults(BaseModel):
    """Schema for proposal evaluation results"""
    overall_score: float = Field(ge=0.0, le=1.0)
    summary: str
    criteria_evaluations: List[CriterionEvaluation]
    recommendation: str

class ProposalAnalysisPipelineResponse(AnalysisPipelineResponse):
    """Schema for proposal analysis pipeline responses"""
    # Proposal-specific results
    evaluation_results: Optional[Union[ProposalEvaluationResults, Dict[str, Any]]] = None
    technical_evaluation: Optional[Union[EvaluationScore, Dict[str, Any]]] = None
    grammar_evaluation: Optional[Union[EvaluationScore, Dict[str, Any]]] = None
    consistency_evaluation: Optional[Union[EvaluationScore, Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class PipelineDocumentInfo(BaseModel):
    """Información de un documento asociado a un pipeline"""
    document_id: UUID
    title: str
    filename: Optional[str] = None
    role: str
    processing_order: int

class PipelineEmbeddingResponse(BaseModel):
    """Schema for pipeline embedding responses"""
    id: UUID
    pipeline_id: UUID
    chunk_index: int
    chunk_text: str
    metadata_info: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
