"""
Schemas for analysis scenarios and pipelines
"""
from typing import Dict, Any, List, Optional
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
    document_id: UUID
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

class AnalysisPipelineResponse(AnalysisPipelineBase):
    """Base schema for analysis pipeline responses"""
    id: UUID
    scenario_id: UUID
    parent_pipeline_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RfpAnalysisPipelineResponse(AnalysisPipelineResponse):
    """Schema for RFP analysis pipeline responses"""
    # RFP-specific results
    extracted_criteria: Optional[Dict[str, Any]] = None
    evaluation_framework: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ProposalAnalysisPipelineResponse(AnalysisPipelineResponse):
    """Schema for proposal analysis pipeline responses"""
    # Proposal-specific results
    evaluation_results: Optional[Dict[str, Any]] = None
    technical_evaluation: Optional[Dict[str, Any]] = None
    grammar_evaluation: Optional[Dict[str, Any]] = None
    consistency_evaluation: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class PipelineEmbeddingResponse(BaseModel):
    """Schema for pipeline embedding responses"""
    id: UUID
    pipeline_id: UUID
    chunk_index: int
    chunk_text: str
    metadata_info: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
