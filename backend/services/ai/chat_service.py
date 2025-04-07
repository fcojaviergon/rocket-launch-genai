from typing import Dict, Any, Optional, List, Tuple
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from openai import AsyncOpenAI
import httpx
import json
import logging

from core.config import settings
from database.models.conversation import Conversation, Message
from database.models.user import User
from database.models.document import Document
from modules.document.service import DocumentService
from core.llm_interface import LLMClientInterface, LLMMessage

logger = logging.getLogger(__name__)

class ChatService:
    """Service for chat with AI assistant, RAG, and conversation management."""
    
    def __init__(self, llm_client: Optional[LLMClientInterface] = None, document_service: Optional[DocumentService] = None):
        """
        Initialize ChatService.
        
        Args:
            llm_client: An optional pre-initialized client implementing LLMClientInterface.
            document_service: An optional pre-initialized DocumentService instance.
        """
        # Store injected dependencies or handle None if not provided
        self.llm_client = llm_client
        self.document_service = document_service
        self.default_model = settings.DEFAULT_CHAT_MODEL or "gpt-4"

        # Log a warning if the essential OpenAI client is missing
        if not self.llm_client:
            logger.warning("ChatService initialized without an OpenAI client. Chat functionalities will fail.")
        # Log a warning if DocumentService is missing, as RAG will fail
        if not self.document_service:
            logger.warning("ChatService initialized without a DocumentService. RAG functionalities will fail.")
        
    async def get_conversation(self, db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID):
        """Get a conversation by ID"""
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        return result.scalars().first()
    
    async def get_user_conversations(self, db: AsyncSession, user_id: uuid.UUID):
        """Get all conversations of a user"""
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
        )
        return result.scalars().all()
    
    async def create_conversation(self, db: AsyncSession, user_id: uuid.UUID, title: str):
        """Create a new conversation"""
        conversation = Conversation(
            title=title,
            user_id=user_id
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation
    
    async def update_conversation(self, db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID, title: str):
        """Update a conversation"""
        conversation = await self.get_conversation(db, conversation_id, user_id)
        if not conversation:
            return None
        
        conversation.title = title
        await db.commit()
        await db.refresh(conversation)
        return conversation
    
    async def delete_conversation(self, db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID):
        """Delete a conversation"""
        conversation = await self.get_conversation(db, conversation_id, user_id)
        if not conversation:
            return False
        
        await db.delete(conversation)
        await db.commit()
        return True
    
    async def add_message(self, db: AsyncSession, conversation_id: uuid.UUID, content: str, role: str):
        """Add a message to a conversation"""
        message = Message(
            content=content,
            role=role,
            conversation_id=conversation_id
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message
    
    async def get_conversation_messages(self, db: AsyncSession, conversation_id: uuid.UUID):
        """Get all messages of a conversation"""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
        )
        return result.scalars().all()
    
    async def generate_chat_response(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        message: str,
        conversation_id: Optional[uuid.UUID] = None,
        model: Optional[str] = None,
        temperature: float = 0.7
    ):
        """
        Generate a chat response based on the message and the conversation history
        """
        try:
            # Get or create conversation
            conversation = None
            is_new_conversation = False
            
            if conversation_id:
                conversation = await self.get_conversation(db, conversation_id, user_id)
                if not conversation:
                    raise ValueError(f"Conversation not found: {conversation_id}")
            else:
                # Create new conversation with the first message as title
                title = message[:30] + "..." if len(message) > 30 else message
                conversation = await self.create_conversation(db, user_id, title)
                is_new_conversation = True
                conversation_id = conversation.id
            
            # Save user message
            user_message = await self.add_message(db, conversation_id, message, "user")
            
            # Get conversation history if it is an existing conversation
            messages = []
            if not is_new_conversation:
                conversation_messages = await self.get_conversation_messages(db, conversation_id)
                messages = [{"role": msg.role, "content": msg.content} for msg in conversation_messages]
            else:
                messages = [{"role": "user", "content": message}]
            
            # Check if LLM client is available
            if not self.llm_client:
                raise RuntimeError("ChatService is not configured with an LLM client.")
            
            # Call the LLM client via the interface
            assistant_message_content = await self.llm_client.generate_chat_completion(
                messages=messages,
                model=model or self.default_model,
                temperature=temperature,
                stream=False # Not streaming here
            )
            
            # Save assistant response
            assistant_message = await self.add_message(
                db, conversation_id, assistant_message_content, "assistant"
            )
            
            return {
                "conversation_id": conversation_id,
                "message": assistant_message
            }
            
        except Exception as e:
            print(f"Error generating chat response: {str(e)}")
            raise

    async def generate_stream_response(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.7
    ):
        """
        Generate a streaming response using the OpenAI API
        """
        try:
            # Check if LLM client is available
            if not self.llm_client:
                raise RuntimeError("ChatService is not configured with an LLM client.")

            # Call the LLM client via the interface with stream=True
            return self.llm_client.generate_chat_completion(
                messages=messages,
                model=model or self.default_model,
                temperature=temperature,
                stream=True
            )
            
        except Exception as e:
            print(f"Error generating streaming response: {str(e)}")
            raise

    async def generate_rag_response(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        conversation_id: Optional[uuid.UUID] = None
    ) -> Dict:
        """
        Generate a response using RAG
        """
        try:
            # Ensure required services are available
            if not self.document_service:
                raise RuntimeError("DocumentService is not available in ChatService for RAG.")
            if not self.llm_client:
                raise RuntimeError("OpenAI client is not available in ChatService for RAG.")

            # Use DocumentService for semantic search
            # Use the injected DocumentService instance
            # Search relevant documents
            similar_docs = await self.document_service.rag_search(
                db=db, 
                query=query, 
                user_id=user_id,
                limit=3
            )
            
            # Format sources and build context
            sources = []
            context_parts = []
            
            for doc_info in similar_docs:
                document = doc_info["document"]
                similarity = doc_info["similarity"]
                chunks = doc_info.get("chunks", [])
                
                if similarity > 0.2:  # Only use documents with high similarity
                    # Use the text of the chunks if available, or the complete content
                    if chunks:
                        # Sort chunks by similarity and use the best ones
                        chunks.sort(key=lambda x: x["similarity"], reverse=True)
                        for chunk in chunks[:2]:  # Use the 2 most relevant chunks
                            context_parts.append(f"[{document['title']} - Extract {chunk['chunk_index']}]\n{chunk['chunk_text']}")
                    else:
                        context_parts.append(f"[{document['title']}]\n{document['content']}")
                    
                    sources.append({
                        "document_name": document["title"] or "No title",
                        "document_type": document["type"] or "UNKNOWN",  # Default value if None
                        "relevance": similarity
                    })
            
            if not context_parts:
                return {
                    "answer": "No encontré documentos relevantes para responder tu pregunta.",
                    "sources": [],
                    "conversation_id": conversation_id,
                    "created_at": datetime.now()
                }
                
            context = "\n\n".join(context_parts)
            
            # Generate response
            response = await self.llm_client.generate_chat_completion(
                model= self.default_model, # Use default model for RAG response generation for now
                messages=[
                    {"role": "system", "content": f"Responde la pregunta del usuario basándote únicamente en el siguiente contexto:\n\n{context}\n\nNo añadas información que no esté en el contexto. Si la respuesta no está en el contexto, indica que no puedes responder con la información proporcionada."},
                    {"role": "user", "content": query}
                ],
                temperature=0.3 # Lower temperature for more factual response
            )
            
            answer = response
            
            # If there is a conversation_id, save the exchange
            if conversation_id:
                await self.save_rag_exchange(db, conversation_id, query, answer, sources)
                
            return {
                "answer": answer,
                "sources": sources,
                "conversation_id": conversation_id,
                "created_at": datetime.now()
            }
        except Exception as e:
            print(f"Error in generate_rag_response: {str(e)}")
            raise

    async def save_rag_exchange(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        query: str,
        answer: str,
        sources: List[Dict]
    ):
        """
        Save a RAG exchange in the conversation
        """
        # User message
        user_message = Message(
            conversation_id=conversation_id,
            content=query,
            role="user"
        )
        db.add(user_message)
        
        # System message with sources
        system_message = Message(
            conversation_id=conversation_id,
            content=answer,
            role="assistant",
            metadata={"sources": sources}
        )
        db.add(system_message)
        
        await db.commit()

    async def stream_chat_response_full(self, db: AsyncSession, user: User, chat_request: Any):
        """Handles the full streaming chat logic including conversation and message management."""

        conversation_id = chat_request.conversation_id
        conversation = None
        
        # 1. Get or Create Conversation
        if conversation_id:
            conversation = await self.get_conversation(db, conversation_id, user.id)
            if not conversation:
                 # Raise an error the endpoint can catch
                 raise ValueError(f"Conversation {conversation_id} not found or access denied.")
        else:
            title = chat_request.content[:30] + "..." if len(chat_request.content) > 30 else chat_request.content
            conversation = await self.create_conversation(db, user.id, title)
            conversation_id = conversation.id
            logger.info(f"Created new conversation {conversation_id} for stream.")

        # 2. Save User Message
        await self.add_message(db, conversation_id, chat_request.content, "user")

        # 3. Get Message History
        db_messages = await self.get_conversation_messages(db, conversation_id)
        # TODO: Add system prompt if needed
        history = [{"role": msg.role, "content": msg.content} for msg in db_messages]
        
        # 4. Generate stream from AI
        try:
            stream = await self.generate_stream_response(
                messages=history,
                model=chat_request.model,
                temperature=chat_request.temperature
            )
        except Exception as ai_error:
             logger.error(f"Error calling OpenAI stream API: {ai_error}")
             # Yield an error message chunk or raise exception
             yield json.dumps({"error": "Failed to get response from AI model."})
             return # Stop generation

        # 5. Stream response chunks and collect full response
        full_assistant_response = ""
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_assistant_response += content
                # Yield chunk in desired format (e.g., JSON string)
                yield json.dumps({"content": content, "conversation_id": str(conversation_id)}) + "\n"
        
        # Add a final newline or marker if needed by client
        # yield "\n"

        # 6. Save Full Assistant Message (after stream is complete)
        if full_assistant_response:
             await self.add_message(db, conversation_id, full_assistant_response, "assistant")
             logger.info(f"Saved full assistant response to conversation {conversation_id}")
        else:
             logger.warning(f"No content received from assistant stream for conversation {conversation_id}")
