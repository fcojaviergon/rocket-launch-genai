from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

class DocumentBase(BaseModel):
    name: str  # Will be used as title (title) in the database

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    process_metadata: Optional[Dict[str, Any]] = None

class DocumentProcessingResultResponse(BaseModel):
    id: UUID
    document_id: UUID
    pipeline_name: str
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    token_count: Optional[int] = None
    process_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class PipelineExecutionResponse(BaseModel):
    id: UUID
    pipeline_id: UUID
    document_id: UUID
    user_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pipeline_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: UUID
    title: str  # Corresponds to name in the API
    content: str
    user_id: UUID  # Corresponds to user_id in the database
    created_at: datetime
    updated_at: Optional[datetime] = None
    file_path: Optional[str] = None
    type: Optional[str] = None
    processing_results: Optional[List[DocumentProcessingResultResponse]] = None
    pipeline_executions: Optional[List[PipelineExecutionResponse]] = None

    class Config:
        from_attributes = True
        exclude = {"document": {"pipeline_executions"}}
        arbitrary_types_allowed = True

class PipelineInfo(BaseModel):
    name: str
    description: str
    steps: List[str]

class DocumentProcessResult(BaseModel):
    id: UUID
    name: str
    content_type: str
    process_metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: UUID
