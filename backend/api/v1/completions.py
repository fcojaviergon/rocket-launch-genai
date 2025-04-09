import uuid
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from services.ai.completion_service import CompletionService
from core.dependencies import get_current_user, get_completion_service
from database.models.user import User
from schemas.completion import CompletionRequest, CompletionResponse
from core.config import settings

router = APIRouter()

@router.post("", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    current_user: User = Depends(get_current_user),
    completion_service: CompletionService = Depends(get_completion_service)
):
    """
    Generates a text completion based on the provided prompt.
    """
    try:
        # Call the service, which returns only the text
        completion_text = await completion_service.generate_completion(
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
            # Note: Other parameters like top_p, frequency_penalty, presence_penalty, stop
            # are currently not passed to completion_service.generate_completion.
            # You might need to update CompletionService if these are required.
        )
        
        # Manually construct the response object
        # TODO: Get actual usage, model used, and finish_reason if the service/LLM client can provide them.
        # For now, using placeholders or deriving from the request.
        response_id = f"cmpl-{uuid.uuid4()}"
        created_time = datetime.datetime.now().isoformat()
        model_used = request.model or settings.DEFAULT_CHAT_MODEL or "unknown" # Derive model used
        
        # Placeholder for usage and finish_reason as the service doesn't return them
        usage_placeholder = {"prompt_tokens": -1, "completion_tokens": -1, "total_tokens": -1} 
        finish_reason_placeholder = "unknown" 

        return {
            "id": response_id,
            "created": created_time,
            "text": completion_text,
            "model": model_used,
            "usage": usage_placeholder,
            "finish_reason": finish_reason_placeholder
        }
        
    except Exception as e:
        # Log the detailed error for debugging
        # Consider using a proper logging framework
        print(f"Error in create_completion: {type(e).__name__}: {e}") 
        raise HTTPException(
            status_code=500,
            detail=f"Error generating completion: {str(e)}"
        )
