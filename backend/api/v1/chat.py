import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy import desc
import asyncio
from datetime import datetime
from typing import List, Optional

from core.dependencies import get_db, get_current_user
from database.models.user import User
from database.models.conversation import Conversation, Message
from services.ai.chat_service import ChatService
from core.dependencies import get_chat_service
from schemas.chat import (
    ChatRequest, 
    ChatResponse, 
    ConversationCreate, 
    ConversationUpdate, 
    ConversationResponse,
    ConversationListResponse,
    MessageResponse,
    RagRequest,
    RagResponse
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("", response_model=ChatResponse)
async def create_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Send a message to the assistant and receive a response
    """
    try:
        result = await chat_service.generate_chat_response(
            db=db,
            user_id=current_user.id,
            message=request.get_message(),
            conversation_id=request.conversation_id,
            model=request.model,
            temperature=request.temperature
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating response: {str(e)}"
        )

@router.get("/conversations", response_model=list[ConversationListResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    List all user conversations
    """
    try:
        conversations = await chat_service.get_user_conversations(db, current_user.id)
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing conversations: {str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Get a conversation by ID with all its messages
    """
    conversation = await chat_service.get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get messages
    messages = await chat_service.get_conversation_messages(db, conversation_id)
    
    # Create a dictionary with the necessary data instead of modifying the object directly
    result = {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": messages
    }
    
    return result

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Create a new conversation
    """
    try:
        new_conversation = await chat_service.create_conversation(
            db, current_user.id, conversation.title
        )
        
        # Prepare structured response as in get_conversation
        result = {
            "id": new_conversation.id,
            "title": new_conversation.title,
            "created_at": new_conversation.created_at,
            "updated_at": new_conversation.updated_at,
            "messages": []  # New conversation without messages
        }
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating conversation: {str(e)}"
        )

@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    conversation: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Update an existing conversation
    """
    if not conversation.title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    updated_conversation = await chat_service.update_conversation(
        db, conversation_id, current_user.id, conversation.title
    )
    
    if not updated_conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Prepare structured response as in get_conversation
    messages = await chat_service.get_conversation_messages(db, conversation_id)
    
    result = {
        "id": updated_conversation.id,
        "title": updated_conversation.title,
        "created_at": updated_conversation.created_at,
        "updated_at": updated_conversation.updated_at,
        "messages": messages
    }
    
    return result

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Delete a conversation
    """
    result = await chat_service.delete_conversation(db, conversation_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return None

# Define media type for streaming JSON lines
STREAMING_JSON_MEDIA_TYPE = "application/x-ndjson"

@router.post("/stream", response_class=StreamingResponse, responses={200: {"content": {STREAMING_JSON_MEDIA_TYPE: {}}}}) 
async def stream_chat_message(
    chat_request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    try:
        # Delegate the entire streaming logic to the service
        stream_generator = chat_service.stream_chat_response_full(
            db=session, 
            user=current_user, 
            chat_request=chat_request
        )
        
        # Return the async generator from the service within StreamingResponse
        return StreamingResponse(stream_generator, media_type=STREAMING_JSON_MEDIA_TYPE)

    except ValueError as e:
        # Handle known errors like conversation not found from service
        logger.error(f"Value error during chat stream: {e}")
        # Cannot raise HTTPException directly here as headers are already sent.
        # Client needs to handle potential error messages within the stream.
        async def error_stream():
             yield json.dumps({"error": str(e)}) + "\n"
        return StreamingResponse(error_stream(), media_type=STREAMING_JSON_MEDIA_TYPE, status_code=404)
    except Exception as e:
        logger.error(f"Error during chat stream: {e}", exc_info=True)
        # General error - attempt to stream an error message
        async def error_stream():
             yield json.dumps({"error": "An internal server error occurred during streaming."}) + "\n"
        return StreamingResponse(error_stream(), media_type=STREAMING_JSON_MEDIA_TYPE, status_code=500)

@router.post("/rag", response_model=RagResponse)
async def query_documents(
    request: RagRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Generates a response using RAG on the user's documents
    """
    try:
        result = await chat_service.generate_rag_response(
            db=db,
            user_id=current_user.id,
            query=request.query,
            conversation_id=request.conversation_id
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating RAG response: {str(e)}"
        )
