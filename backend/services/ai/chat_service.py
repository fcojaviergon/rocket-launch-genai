from typing import Dict, Any, Optional, List, Tuple
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
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
            # AWAIT the call to get the async generator
            stream_generator = await self.llm_client.generate_chat_completion(
                messages=messages,
                model=model or self.default_model,
                temperature=temperature,
                stream=True
            )
            # Return the generator itself
            return stream_generator
            
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
                raise RuntimeError("LLM client is not available in ChatService for RAG.")

            # Search relevant document CHUNKS across all user documents
            # search_similar_documents now returns List[Dict] where each Dict is a CHUNK
            similar_chunks = await self.document_service.search_similar_documents(
                db=db,
                query_embedding=await self.document_service.generate_query_embedding(query), # Generate query embedding
                user_id=user_id,
                limit=5,  # Fetch top 5 chunks across all docs
                min_similarity=0.2, # Filter at DB level
                model="text-embedding-3-small" # Ensure model consistency
                # document_id is None here, searching all docs
            )

            # Format sources and build context directly from the returned chunks
            sources = []
            context_parts = []
            processed_docs = set() # Keep track of documents included in sources

            # No need to sort again by similarity here, DB already did it.
            # Directly iterate over the chunks returned by the search service.
            for chunk_info in similar_chunks: # Each item is a chunk dictionary
                similarity = chunk_info["similarity"]
                chunk_text = chunk_info.get("chunk_text")
                document_meta = chunk_info.get("document", {}) # Get nested document metadata

                # Add chunk to context if text exists and similarity is sufficient
                # (DB already filtered by min_similarity, but keep check just in case)
                if chunk_text and similarity > 0.2:
                    # Limit context length if needed, e.g., by number of chunks or total chars
                    if len(context_parts) < 3: # Example: Use top 3 chunks for context
                       context_parts.append(f"[{document_meta.get('title', 'Unknown Title')} - Chunk {chunk_info.get('chunk_index', 'N/A')}]\n{chunk_text}")

                # Add document to sources only once, using the highest similarity chunk for that doc
                doc_id = document_meta.get("id")
                if doc_id and doc_id not in processed_docs:
                     sources.append({
                         "document_name": document_meta.get("title", "No title"),
                         "document_type": document_meta.get("type", "UNKNOWN"),
                         "relevance": similarity, # Use similarity of the first chunk encountered for this doc
                         "document_id": doc_id
                     })
                     processed_docs.add(doc_id)


            if not context_parts:
                # This happens if search_similar_documents returned 0 items
                # or if all returned items had null/empty chunk_text
                logger.warning(f"RAG context is empty for query: '{query}' and user {user_id}.")
                return {
                    "answer": "I did not find relevant information in the documents to answer your question.",
                    "sources": [],
                    "conversation_id": conversation_id,
                    "created_at": datetime.now()
                }

            context = "\n\n".join(context_parts)

            # Generate response
            # Use the LLM client interface
            answer = await self.llm_client.generate_chat_completion(
                model= self.default_model, # Use default model for RAG response generation for now
                messages=[
                    {"role": "system", "content": f"Answer the user's question based solely on the following context:\n\n{context}\n\nDo not add information that is not in the context. If the answer is not in the context, indicate that you cannot respond with the information provided."},
                    {"role": "user", "content": query}
                ],
                temperature=0.3, # Lower temperature for more factual response
                stream=False # Ensure stream is False for this method
            )

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
            logger.error(f"Error in generate_rag_response: {str(e)}", exc_info=True) # Log full traceback
            raise # Re-raise exception for endpoint handler

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
        async for content_chunk in stream:
            if content_chunk:
                full_assistant_response += content_chunk
                # Yield chunk in desired format (e.g., JSON string)
                yield json.dumps({"content": content_chunk, "conversation_id": str(conversation_id)}) + "\n"
        
        # Add a final newline or marker if needed by client
        # yield "\n"

        # 6. Save Full Assistant Message (after stream is complete)
        if full_assistant_response:
             await self.add_message(db, conversation_id, full_assistant_response, "assistant")
             logger.info(f"Saved full assistant response to conversation {conversation_id}")
        else:
             logger.warning(f"No content received from assistant stream for conversation {conversation_id}")
