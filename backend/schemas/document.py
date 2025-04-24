from fileinput import filename
from pydantic import BaseModel, Field, UUID4, HttpUrl, validator, root_validator, computed_field, model_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
import enum
import json
import logging

logger = logging.getLogger(__name__)

# Re-define Enum here for schema usage
class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_PROCESSED = "NOT_PROCESSED"

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


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    filename: str
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    file_path: Optional[str] = None
    type: Optional[str] = None

    # These fields will be populated by the service layer
    processing_status: Union[ProcessingStatus, str] = Field(..., description="Status of the embedding process")

    class Config:
        from_attributes = True # Still needed to load from ORM object initially in service
        arbitrary_types_allowed = True
        use_enum_values = True
        populate_by_name = True

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
