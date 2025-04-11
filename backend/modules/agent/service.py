"""
Service layer for Agent module, encapsulates CRUD operations and business logic.
"""
import logging
from typing import AsyncGenerator, Dict, List, Optional, Union
from uuid import UUID
import json

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models.agent import AgentConversation, AgentMessage
from modules.agent.core import run_agent_loop
from modules.agent.state import AgentState
from schemas.agent import (
    AgentConversation as AgentConversationSchema,
    AgentMessage as AgentMessageSchema,
    AgentConversationCreate,
    AgentMessageCreate
)


logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing agent conversations and executing agent logic."""

    def __init__(self) -> None:
        """Initialize the AgentService."""
        pass

    async def get_conversation(
        self, 
        db: AsyncSession, 
        conversation_id: UUID,
        user_id: Optional[int] = None
    ) -> Optional[AgentConversationSchema]:
        """
        Get a conversation by ID with its messages loaded.
        If user_id is provided, ensures the conversation belongs to the user.
        """
        result = await db.execute(
            select(AgentConversation)
            .options(selectinload(AgentConversation.messages))
            .where(AgentConversation.id == conversation_id)
        )
        db_conversation = result.scalars().first()
        
        # If no conversation found or user_id doesn't match
        if not db_conversation or (user_id and db_conversation.user_id != user_id):
            if user_id and db_conversation and db_conversation.user_id != user_id:
                logger.warning(f"User {user_id} attempted to access conversation {conversation_id} belonging to user {db_conversation.user_id}")
            return None
            
        # Convert SQLAlchemy model to Pydantic model
        return AgentConversationSchema.model_validate(db_conversation)

    async def get_conversations_by_user(
        self, 
        db: AsyncSession, 
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentConversationSchema]:
        """Get all conversations for a specific user with pagination."""
        result = await db.execute(
            select(AgentConversation)
            .where(AgentConversation.user_id == user_id)
            .options(selectinload(AgentConversation.messages))
            .order_by(AgentConversation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        db_conversations = list(result.scalars().all())
        
        # Initialize an empty list for conversations
        conversations = []
        
        # Convert each SQLAlchemy model to a Pydantic model
        for conversation in db_conversations:
            try:
                pydantic_conversation = AgentConversationSchema.model_validate(conversation)
                conversations.append(pydantic_conversation)
            except Exception as e:
                # Log the error but continue processing
                logger.error(f"Error converting conversation {conversation.id}: {str(e)}")
                # Create a simplified version without messages as fallback
                try:
                    conversations.append(AgentConversationSchema(
                        id=conversation.id,
                        user_id=conversation.user_id,
                        title=conversation.title,
                        started_at=conversation.created_at,
                        messages=[]
                    ))
                except Exception as inner_e:
                    logger.error(f"Failed to create simplified conversation: {str(inner_e)}")
                continue
                
        return conversations

    async def create_conversation(
        self, 
        db: AsyncSession, 
        conversation_create: AgentConversationCreate
    ) -> AgentConversationSchema:
        """Create a new agent conversation."""
        db_conversation = AgentConversation(
            user_id=conversation_create.user_id,
            title=conversation_create.title
        )
        db.add(db_conversation)
        await db.flush()
        await db.refresh(db_conversation)
        await db.commit()
        
        # Return a simplified version that doesn't trigger lazy loading
        # The full conversation with messages is loaded later when needed
        return AgentConversationSchema(
            id=db_conversation.id,
            user_id=db_conversation.user_id,
            title=db_conversation.title,
            started_at=db_conversation.created_at,
            messages=[] # Explicitly set messages to empty list
        )

    async def update_conversation_title(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        title: str,
        user_id: Optional[UUID] = None
    ) -> Optional[AgentConversationSchema]:
        """Update the title of a conversation."""
        # Directly get the SQLAlchemy model
        result = await db.execute(
            select(AgentConversation).where(AgentConversation.id == conversation_id)
        )
        db_conversation = result.scalars().first()
        
        if not db_conversation:
            return None
            
        # Verify ownership if user_id is provided
        if user_id and db_conversation.user_id != user_id:
            return None
        
        # Update the title
        db_conversation.title = title
        await db.commit()
        await db.refresh(db_conversation)
        
        # Convert to Pydantic model before returning
        return AgentConversationSchema.model_validate(db_conversation)

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None
    ) -> bool:
        """Delete a conversation and all its messages."""
        # Verify ownership if user_id is provided
        if user_id:
            result = await db.execute(
                select(AgentConversation)
                .where(AgentConversation.id == conversation_id)
            )
            db_conversation = result.scalars().first()
            
            # If no conversation found or user doesn't own it
            if not db_conversation or db_conversation.user_id != user_id:
                if db_conversation and db_conversation.user_id != user_id:
                    logger.warning(f"User {user_id} attempted to delete conversation {conversation_id} belonging to user {db_conversation.user_id}")
                return False
        
        # First delete all messages associated with the conversation
        await db.execute(
            delete(AgentMessage)
            .where(AgentMessage.conversation_id == conversation_id)
        )
        
        # Then delete the conversation itself
        result = await db.execute(
            delete(AgentConversation)
            .where(AgentConversation.id == conversation_id)
        )
        
        await db.flush()
        await db.commit()
        # Check if any rows were deleted
        return result.rowcount > 0

    async def create_message(
        self, 
        db: AsyncSession, 
        conversation_id: UUID, 
        role: str, 
        content: str,
        visible: bool = True
    ) -> AgentMessageSchema:
        """
        Create a new message in an agent conversation with direct parameters.
        
        This is an overload of the create_message method that accepts role and content
        directly without requiring a AgentMessageCreate object.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            role: Role of the message sender (user, assistant, system, tool)
            content: Content of the message
            visible: Whether the message should be visible to users
            
        Returns:
            The created message as a Pydantic schema
        """
        message_create = AgentMessageCreate(
            role=role,
            content=content,
            visible=visible
        )
        
        # We just delegate to the other method - caller handles transaction
        return await self.create_message_from_model(db, conversation_id, message_create)

    async def create_message_from_model(
        self, 
        db: AsyncSession, 
        conversation_id: UUID, 
        message_create: AgentMessageCreate
    ) -> AgentMessageSchema:
        """Create a new message in an agent conversation from a model."""
        db_message = AgentMessage(
            conversation_id=conversation_id,
            role=message_create.role,
            content=message_create.content,
            visible=message_create.visible
        )
        
        try:
            db.add(db_message)
            await db.flush()
            await db.refresh(db_message)
            # Don't commit here - let the caller handle transaction management
            # This prevents connection leaks by letting the owner of the session control its lifecycle
            
            # Convert to Pydantic model
            return AgentMessageSchema(
                id=db_message.id,
                conversation_id=db_message.conversation_id,
                role=db_message.role,
                content=db_message.content,
                visible=message_create.visible,
                created_at=db_message.created_at
            )
        except Exception as e:
            logger.error(f"Error creating message: {e}", exc_info=True)
            # Let the caller handle rollback
            raise

    async def get_messages_by_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        skip: int = 0, 
        limit: int = 1000
    ) -> List[AgentMessageSchema]:
        """Get all messages for a specific conversation."""
        # Verify ownership if user_id is provided
        if user_id:
            conversation = await self.get_conversation(db, conversation_id, user_id)
            if not conversation:
                return []
        
        result = await db.execute(
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation_id)
            .order_by(AgentMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        db_messages = list(result.scalars().all())
        
        # Initialize an empty list for messages
        messages = []
        
        # Convert each SQLAlchemy model to a Pydantic model with error handling
        for message in db_messages:
            try:
                pydantic_message = AgentMessageSchema.model_validate(message)
                messages.append(pydantic_message)
            except Exception as e:
                # Log the error but continue processing
                logger.error(f"Error converting message {message.id}: {str(e)}")
                continue
                
        return messages

    async def run_agent_with_streaming(
        self,
        db: AsyncSession,
        conversation_id: Optional[UUID],
        query: str,
        user_id: Optional[UUID] = None
    ) -> AsyncGenerator[str, None]:
        """
        Run the agent with streaming response and persist messages to DB.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation or None to create a new one
            query: User query to process
            user_id: Optional user ID for ownership verification
            
        Yields:
            Chunks of the assistant's response
        """
        try:
            # If conversation_id is None, create a new conversation
            if conversation_id is None and user_id is not None:
                # Use first few words of query as title (up to 30 chars)
                title = query.strip()[:30]
                if len(title) < 10:  # If too short, use default
                    title = "New Conversation"
                
                conversation_create = AgentConversationCreate(
                    user_id=user_id,
                    title=title
                )
                new_conversation = await self.create_conversation(db, conversation_create)
                conversation_id = new_conversation.id
                
                logger.info(f"Created new conversation {conversation_id} for user {user_id}")
            # Verify conversation ownership if user_id is provided and conversation_id exists
            elif user_id and conversation_id:
                # Query the conversation directly
                result = await db.execute(
                    select(AgentConversation)
                    .where(AgentConversation.id == conversation_id)
                )
                db_conversation = result.scalars().first()
                
                # If no conversation found or user doesn't own it
                if not db_conversation or db_conversation.user_id != user_id:
                    if db_conversation and db_conversation.user_id != user_id:
                        logger.warning(f"User {user_id} attempted to access conversation {conversation_id} belonging to user {db_conversation.user_id}")
                    raise ValueError(f"Conversation {conversation_id} not found or not owned by user {user_id}")
            elif conversation_id is None:
                # This should not happen, but handle it just in case
                raise ValueError("Cannot create a conversation without a user_id")
            
            # Initialize agent state using the factory method to load history
            agent_state = await AgentState.create(
                conversation_id=conversation_id,
                db=db,
                agent_service=self
            )
            
            # Create and persist user message
            await agent_state.add_message("user", query)
            # Make sure we commit the user message before running the agent
            await db.commit()
            logger.info(f"Persisted user message to conversation {conversation_id}")
            
            # Run agent loop with streaming
            collected_response = ""
            async for chunk in run_agent_loop(agent_state, db):
                # Accumulate the response for consistency checks
                if isinstance(chunk, str):
                    collected_response += chunk
                yield chunk 
                
                
        except Exception as e:
            # Log the error
            logger.error(f"Error in run_agent_with_streaming: {str(e)}", exc_info=True)
            # Yield an error message in a format the frontend can handle
            yield json.dumps({"error": str(e), "done": True})
        finally:
            # Ensure connections are always properly closed regardless of success or failure
            try:
                # The db session in run_agent_loop might already be closed, but we'll close this one too just to be safe
                await db.close()
                logger.debug(f"Database connection properly closed in run_agent_with_streaming")
            except Exception as close_error:
                logger.error(f"Error closing database connection: {close_error}") 