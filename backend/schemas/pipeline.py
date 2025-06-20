from pydantic import BaseModel, Field
from pydantic import validator
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from uuid import UUID
import uuid

# Schemas for PipelineStep
class PipelineStep(BaseModel):
    name: str
    config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    id: Optional[str] = None
    type: Optional[str] = None

# Schemas for PipelineConfig
class PipelineConfigBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    steps: List[PipelineStep] = []
    config_metadata: Optional[Dict[str, Any]] = None

class PipelineConfigCreate(PipelineConfigBase):
    pass

class PipelineConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    steps: Optional[List[PipelineStep]] = None
    config_metadata: Optional[Dict[str, Any]] = None

class PipelineConfigResponse(PipelineConfigBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schemas for execution status
class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

# Schemas for pipeline execution
class PipelineExecutionBase(BaseModel):
    pipeline_id: Union[uuid.UUID, str]
    document_id: Union[uuid.UUID, str]
    parameters: Optional[Dict[str, Any]] = None

class PipelineExecutionCreate(PipelineExecutionBase):
    pass

class PipelineExecutionResponse(PipelineExecutionBase):
    id: Union[UUID, str]
    user_id: Union[UUID, str]
    pipeline_id: Union[UUID, str]
    document_id: Union[UUID, str]
    status: str
    pipeline_name: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = Field(None)
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('results', pre=True, always=True)
    def validate_results(cls, v):
        """Ensure results is a dict, parsing from JSON string if necessary."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v # Already a dict, accept it
        if isinstance(v, str):
            try:
                return json.loads(v) # Parse JSON string
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string provided for results")
        raise ValueError("Results must be a dictionary or a valid JSON string")

    class Config:
        from_attributes = True
        exclude = {
            "pipeline": {"executions", "document"},
            "document": {"pipeline_executions", "embeddings"}
        }
        arbitrary_types_allowed = True

# Schemas for batch processing
class ProcessRequest(BaseModel):
    document_id: uuid.UUID
    pipeline_id: uuid.UUID
    async_processing: bool = True
    parameters: dict = {}

class ProcessBatchRequest(BaseModel):
    document_ids: list[uuid.UUID]
    pipeline_id: uuid.UUID
    async_processing: bool = True
    parameters: dict = {}

class BatchJobResponse(BaseModel):
    job_id: str
    status: str
    total_documents: int 