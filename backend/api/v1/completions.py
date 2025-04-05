import uuid
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from services.ai.completion_service import CompletionService
from core.deps import get_current_user
from database.models.user import User
from schemas.completion import CompletionRequest, CompletionResponse

router = APIRouter()

@router.post("", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    current_user: User = Depends(get_current_user),
    completion_service: CompletionService = Depends(lambda: CompletionService())
):
    """
    Generates a text completion based on the provided prompt.
    """
    try:
        result = await completion_service.generate_completion(
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            stop=request.stop
        )
        
        return {
            "id": f"cmpl-{uuid.uuid4()}",
            "created": datetime.datetime.now().isoformat(),
            "text": result["text"],
            "model": result["model"],
            "usage": result["usage"],
            "finish_reason": result["finish_reason"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating completion: {str(e)}"
        )
