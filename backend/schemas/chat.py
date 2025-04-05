from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field, UUID4
from uuid import UUID

class MessageCreate(BaseModel):
    """Schema to create a message"""
    content: str = Field(..., description="Content of the message")
    role: str = Field(..., description="Message role: 'user', 'assistant' or 'system'")

class MessageResponse(BaseModel):
    """Schema for message response"""
    id: UUID4
    content: str
    role: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    """Schema to create a conversation"""
    title: str = Field(..., description="Conversation title")
    
class ConversationUpdate(BaseModel):
    """Schema to update a conversation"""
    title: Optional[str] = Field(None, description="New conversation title")

class ConversationResponse(BaseModel):
    """Schema for conversation response"""
    id: UUID4
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True

class ConversationListResponse(BaseModel):
    """Schema to list conversations"""
    id: UUID4
    title: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    """Schema for chat request"""
    message: Optional[str] = Field(None, description="User message (old field)")
    content: Optional[str] = Field(None, description="User message (new field)")
    conversation_id: Optional[UUID4] = Field(None, description="Existing conversation ID")
    model: Optional[str] = Field(None, description="Model to use")
    temperature: float = Field(0.7, description="Temperatura para sampling (0-1)", ge=0, le=1)
    
    def get_message(self) -> str:
        """Get the user message, either from the 'message' field or 'content' field"""
        return self.message if self.message else self.content

class ChatResponse(BaseModel):
    """Schema for chat response"""
    conversation_id: UUID4
    message: MessageResponse

class DocumentSource(BaseModel):
    document_name: str
    document_type: str
    relevance: float

class RagRequest(BaseModel):
    query: str
    conversation_id: Optional[UUID] = None

class RagResponse(BaseModel):
    answer: str
    sources: List[DocumentSource]
    conversation_id: Optional[UUID]
    created_at: datetime = datetime.now()
