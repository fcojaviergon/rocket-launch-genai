from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import uuid
from datetime import datetime
from enum import Enum

# If you have a common base model in your project (e.g., in schemas.base), 
# you might want to inherit from that instead.
# from .base import BaseSchema # Example

# --- Message Role Enum ---

class MessageRole(str, Enum):
    """Enumeration of possible message roles in agent conversations."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    THINKING = "thinking"

# --- Agent Message Schemas ---

class AgentMessageBase(BaseModel):
    role: str = Field(..., description="Role of the message sender (e.g., 'user', 'assistant', 'system', 'tool', 'thinking')")
    content: str = Field(..., description="The textual content of the message")
    visible: bool = Field(True, description="Whether the message should be visible to users")

class AgentMessageCreate(AgentMessageBase):
    # No extra fields needed for creation beyond base
    pass

class AgentMessage(AgentMessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True # Replace orm_mode if using Pydantic v2

# --- Agent Conversation Schemas ---

class AgentConversationBase(BaseModel):
    title: Optional[str] = Field(None, description="Optional title for the conversation")
    # metadata_info: Optional[Dict[str, Any]] = Field(None, description="Optional metadata dictionary")

class AgentConversationCreate(AgentConversationBase):
    user_id: uuid.UUID # Required on creation

class AgentConversation(AgentConversationBase):
    id: uuid.UUID
    user_id: uuid.UUID
    started_at: datetime
    messages: List[AgentMessage] = Field([], description="Messages within the conversation")

    class Config:
        from_attributes = True # Replace orm_mode if using Pydantic v2

# --- Agent Invocation Schemas (Existing - kept for context) ---

class AgentQuery(BaseModel):
    """Request model for invoking the agent."""
    query: str
    conversation_id: Optional[uuid.UUID] = Field(None, description="Existing conversation ID to continue, or None to start a new one")

class AgentResponse(BaseModel):
    """Response model for the agent's final answer."""
    response: str
    conversation_id: uuid.UUID # Return the ID of the conversation
    # thoughts: Optional[List[str]] = None
    # tool_calls: Optional[List[Dict[str, Any]]] = None
