from typing import Optional, List
from pydantic import BaseModel, Field

class CompletionRequest(BaseModel):
    """Schema for text completion request"""
    prompt: str = Field(..., description="Initial text for completion")
    model: Optional[str] = Field(None, description="Model to use")
    max_tokens: int = Field(500, description="Maximum number of tokens to generate")
    temperature: float = Field(0.7, description="Temperature for sampling (0-1)", ge=0, le=1)
    top_p: float = Field(1.0, description="Cumulative probability for nucleus sampling", ge=0, le=1)
    frequency_penalty: float = Field(0.0, description="Frequency penalty for tokens", ge=-2, le=2)
    presence_penalty: float = Field(0.0, description="Presence penalty for tokens", ge=-2, le=2)
    stop: Optional[List[str]] = Field(None, description="Sequences that stop the generation")

class TokenUsage(BaseModel):
    """Token usage information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class CompletionResponse(BaseModel):
    """Schema for text completion response"""
    id: str
    created: str
    text: str
    model: str
    usage: TokenUsage
    finish_reason: str
