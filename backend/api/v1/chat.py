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

from core.deps import get_db, get_current_user
from database.models.user import User
from database.models.conversation import Conversation, Message
from services.ai.chat_service import ChatService
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

router = APIRouter()
chat_service = ChatService()

@router.post("", response_model=ChatResponse)
async def create_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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

@router.post("/stream", response_class=StreamingResponse)
async def stream_chat_message(
    chat_request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Check if we have a conversation ID
        conversation_id = chat_request.conversation_id
        conversation = None
        
        # If there's no conversation ID, create a new one
        if not conversation_id:
            # Create title based on message content
            title = chat_request.content[:30] + "..." if len(chat_request.content) > 30 else chat_request.content
            new_conversation = Conversation(
                title=title,
                user_id=current_user.id
            )
            session.add(new_conversation)
            await session.commit()
            await session.refresh(new_conversation)
            conversation_id = new_conversation.id
            conversation = new_conversation
        else:
            # Verify that the conversation exists and belongs to the user
            conversation_query = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            )
            result = await session.execute(conversation_query)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Save user message
        user_message = Message(
            content=chat_request.content,
            role="user",
            conversation_id=conversation_id
        )
        session.add(user_message)
        await session.commit()
        await session.refresh(user_message)
        
        # Get message history for this conversation context
        messages_query = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at)
        result = await session.execute(messages_query)
        messages = result.scalars().all()
        
        # Format messages for OpenAI
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Create generator for streaming response
        async def generate_stream():
            # Using a new session context to avoid issues with open connections
            async with AsyncSession(session.bind) as stream_session:
                try:
                    # Send conversation information at the beginning
                    conversation_info = {
                        "type": "conversation_info",
                        "conversation_id": str(conversation_id),
                        "user_message_id": str(user_message.id)
                    }
                    yield f"data: {json.dumps(conversation_info)}\n\n"
                    
                    # Variable to build the complete response
                    full_content = ""
                    assistant_message = None
                    
                    # Get streaming response
                    stream = await chat_service.generate_stream_response(
                        formatted_messages,
                        model=chat_request.model,
                        temperature=chat_request.temperature or 0.7
                    )
                    
                    async for chunk in stream:
                        if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta.content is not None:
                            content = chunk.choices[0].delta.content
                            full_content += content
                            yield f"data: {json.dumps({'type': 'content', 'delta': content})}\n\n"
                            await asyncio.sleep(0)  # Avoid blocking
                
                    # Save complete message in the database
                    if full_content:
                        assistant_message = Message(
                            content=full_content,
                            role="assistant",
                            conversation_id=conversation_id
                        )
                        stream_session.add(assistant_message)
                        await stream_session.commit()
                        await stream_session.refresh(assistant_message)
                        
                        # Send saved message information
                        message_info = {
                            "type": "message_info",
                            "id": str(assistant_message.id),
                            "timestamp": assistant_message.created_at.isoformat()
                        }
                        yield f"data: {json.dumps(message_info)}\n\n"
                    
                    # Mark end of stream
                    yield f"data: [DONE]\n\n"
                except Exception as e:
                    print(f"Error in streaming: {str(e)}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    yield f"data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        print(f"Error in stream_chat_message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing streaming message: {str(e)}")

@router.post("/rag", response_model=RagResponse)
async def query_documents(
    request: RagRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
