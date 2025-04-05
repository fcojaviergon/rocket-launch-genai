from typing import Dict, Any, Optional, List, Tuple
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from openai import AsyncOpenAI
import httpx

from core.config import settings
from database.models.conversation import Conversation, Message
from database.models.user import User
from database.models.document import Document
from modules.document.service import DocumentService

class ChatService:
    """Service for chat with AI assistant with history"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.default_model = "gpt-4"
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            http_client=httpx.AsyncClient()
        )
        
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
            
            # Configure parameters for the API
            chat_params = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
            }
            
            # Call the OpenAI API
            response = await self.client.chat.completions.create(**chat_params)
            
            # Extract response
            assistant_message_content = response.choices[0].message.content
            
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
            # Configure parameters for the API
            chat_params = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,  # Activate streaming
            }
            
            # Call the OpenAI API with streaming
            return await self.client.chat.completions.create(**chat_params)
            
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
            # Use DocumentService for semantic search
            doc_service = DocumentService()
            
            # Search relevant documents
            similar_docs = await doc_service.rag_search(
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
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert assistant that answers questions based on provided documents. "
                                  "Use only the information from the documents to answer. "
                                  "If the information is not sufficient, indicate it clearly."
                    },
                    {
                        "role": "user", 
                        "content": f"Based on the following documents:\n\n{context}\n\n"
                                  f"Answer this question: {query}"
                    }
                ],
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
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
