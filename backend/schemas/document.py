from pydantic import BaseModel, Field, UUID4, HttpUrl
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import validator, root_validator
import enum

# Re-define Enum here for schema usage
class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_PROCESSED = "not_processed"

class DocumentBase(BaseModel):
    name: str  # Will be used as title (title) in the database
    user_id: UUID

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    process_metadata: Optional[Dict[str, Any]] = None

class EmbeddingsPayload(BaseModel):
    embeddings: List[List[float]] = Field(..., description="List of embedding vectors.")
    chunks_text: List[str] = Field(..., description="List of text chunks corresponding to embeddings.")
    model: str = Field(default="text-embedding-3-small", description="Model used for embeddings")

    @root_validator(pre=False, skip_on_failure=True) 
    def check_lengths_match(cls, values):
        embeddings, chunks_text = values.get('embeddings'), values.get('chunks_text')
        if embeddings is not None and chunks_text is not None and len(embeddings) != len(chunks_text):
            raise ValueError("The number of embeddings must match the number of text chunks.")
        return values

class SearchRequest(BaseModel):
    query: str = Field(..., description="The search query string.")
    model: str = Field("text-embedding-3-small", description="The embedding model to use for the query.")
    limit: int = Field(5, ge=1, le=50, description="Maximum number of results to return.")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score (0 to 1).")
    document_id: Optional[UUID] = Field(None, description="Optional document ID to filter search within a specific document.")

class DocumentProcessingResultResponse(BaseModel):
    id: Optional[UUID] = None
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
    processing_status: ProcessingStatus = Field(..., description="Status of the embedding process")

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
