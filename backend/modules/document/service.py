import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import numpy as np
from pgvector.sqlalchemy import Vector
from openai import AsyncOpenAI
import logging
import httpx
from sqlalchemy.sql import text
from sqlalchemy.sql.expression import bindparam
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from database.models.document import Document, DocumentEmbedding
from schemas.document import DocumentCreate, DocumentUpdate
from core.config import settings
# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


# Ensure that the storage directory exists
os.makedirs(settings.DOCUMENT_STORAGE_PATH, exist_ok=True)

class DocumentService:
    async def create_document(
        self,
        db: AsyncSession,
        document_data: DocumentCreate,
        content: bytes,
        user_id: UUID
    ) -> Document:
        """
        Create a new document in the database and save the file physically
        
        Args:
            db: Asynchronous database session
            document_data: Document data to create
            content: Binary content of the file
            user_id: ID of the owner user
            
        Returns:
            Document: Created document
        """
        # Generate a unique file name
        file_id = str(uuid.uuid4())
        file_ext = Path(document_data.name).suffix if document_data.name else ".bin"
        file_name = f"{file_id}{file_ext}"
        
        # Use the global storage path from settings, converting to Path object
        storage_path = Path(settings.DOCUMENT_STORAGE_PATH)
        file_path = storage_path / file_name
        
        # Ensure the storage directory exists
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Make sure content is bytes before writing
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        # Save the file physically
        with open(file_path, "wb") as f:
            f.write(content)
            
        # For binary files like PDF, only save metadata, not the content
        file_size = len(content)
        file_ext = Path(document_data.name).suffix.lower() if document_data.name else ".bin"
        
        # For known binary files, do not attempt to decode the content
        binary_extensions = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif"]
        
        if file_ext in binary_extensions:
            # For binary files, only save metadata
            decoded_content = f"[Archivo {file_ext} - {file_size} bytes - Guardado en {file_name}]"
        else:
            # Try to decode only for text files
            try:
                # Limit the content size to avoid database problems
                preview_size = min(10000, len(content))  # Only save up to 10KB as preview
                decoded_content = content[:preview_size].decode('utf-8', errors='ignore')
                if len(content) > preview_size:
                    decoded_content += "\n... [content truncated]"
            except Exception as e:
                # If it fails, save a description of the file
                decoded_content = f"[Binary content - {file_size} bytes - Saved in {file_name}]"
            
        document = Document(
            title=document_data.name,
            content=decoded_content,
            file_path=str(file_path),
            type=file_ext.lstrip('.').upper(),  # Save extension without point and in uppercase
            user_id=user_id
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return document
    
    async def get_document(self, db: AsyncSession, document_id: UUID) -> Optional[Document]:
        """
        Get a document by its ID
        
        Args:
            db: Asynchronous database session
            document_id: ID of the document to get
            
        Returns:
            Optional[Document]: Document found or None
        """
        result = await db.execute(
            select(Document)
            .filter(Document.id == document_id)
            .options(
                selectinload(Document.processing_results),
                selectinload(Document.pipeline_executions)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_documents(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        type: Optional[str] = None
    ) -> List[Document]:
        """
        Get all documents of a user
        
        Args:
            db: Asynchronous database session
            user_id: ID of the user
            skip: Number of records to skip
            limit: Limit of records to get
            type: Document type to filter
            
        Returns:
            List[Document]: List of documents
        """
        query = select(Document).filter(Document.user_id == user_id)
        
        # Load relations explicitly to avoid lazy loading
        query = query.options(
            selectinload(Document.processing_results),
            selectinload(Document.pipeline_executions)
        )
        
        # Apply type filter if provided
        if type:
            query = query.filter(Document.type == type)
            
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def update_document(
        self,
        db: AsyncSession,
        document_id: UUID,
        document_data: DocumentUpdate
    ) -> Optional[Document]:
        """
        Update a document
        
        Args:
            db: Asynchronous database session
            document_id: ID of the document to update
            document_data: Document data to update
            
        Returns:
            Optional[Document]: Updated document or None
        """
        document = await self.get_document(db, document_id)
        if not document:
            return None
        
        # Update the fields
        for key, value in document_data.dict(exclude_unset=True).items():
            setattr(document, key, value)
        
        await db.commit()
        await db.refresh(document)
        return document
    
    async def delete_document(self, db: AsyncSession, document_id: UUID) -> bool:
        """
        Delete a document
        
        Args:
            db: Asynchronous database session
            document_id: ID of the document to delete
            
        Returns:
            bool: True if deleted correctly, False if not
        """
        document = await self.get_document(db, document_id)
        if not document:
            return False
        
        await db.delete(document)
        await db.commit()
        return True
    
    async def update_document_metadata(
        self,
        db: AsyncSession,
        document_id: UUID,
        metadata: Dict[str, Any]
    ) -> Optional[Document]:
        """
        Update the processing metadata of a document
        
        Args:
            db: Asynchronous database session
            document_id: ID of the document to update
            metadata: Metadata to update
            
        Returns:
            Optional[Document]: Updated document or None
        """
        document = await self.get_document(db, document_id)
        if not document:
            return None
        
        # If there is already metadata, update instead of replacing
        if document.process_metadata:
            document.process_metadata.update(metadata)
        else:
            document.process_metadata = metadata
        
        await db.commit()
        await db.refresh(document)
        return document
    
    async def save_embeddings(
        self,
        db: AsyncSession,
        document_id: UUID,
        embeddings: List[List[float]],
        chunks_text: List[str],
        model: str = "text-embedding-3-small"
    ) -> List[DocumentEmbedding]:
        """
        Save the embeddings of a document in the database
        
        Args:
            db: Asynchronous database session
            document_id: ID of the document
            embeddings: List of embedding vectors
            chunks_text: List of texts corresponding to each embedding
            model: Model used to generate the embeddings
            
        Returns:
            List[DocumentEmbedding]: List of saved embeddings
        """
        # Verify that the document exists
        query = select(Document).where(Document.id == document_id)
        result = await db.execute(query)
        document = result.scalars().first()
        
        if not document:
            raise ValueError(f"The document with ID {document_id} does not exist")
        
        # Verify that there is the same number of embeddings and chunks of text
        if len(embeddings) != len(chunks_text):
            raise ValueError(f"Number of embeddings ({len(embeddings)}) does not match chunks_text ({len(chunks_text)})")
        
        # Delete previous embeddings for the same model
        # To avoid duplicates if processed again
        delete_query = select(DocumentEmbedding).where(
            (DocumentEmbedding.document_id == document_id) &
            (DocumentEmbedding.model == model)
        )
        result = await db.execute(delete_query)
        existing_embeddings = result.scalars().all()
        for emb in existing_embeddings:
            await db.delete(emb)
        
        # Save the new embeddings
        saved_embeddings = []
        for i, (embedding, chunk_text) in enumerate(zip(embeddings, chunks_text)):
            # Create the embedding model
            db_embedding = DocumentEmbedding(
                document_id=document_id,
                model=model,
                embedding=embedding,
                chunk_index=i,
                chunk_text=chunk_text
            )
            
            db.add(db_embedding)
            saved_embeddings.append(db_embedding)
        
        # Save changes in the database
        await db.commit()
        
        return saved_embeddings
    
    async def search_similar_documents(
        self,
        db: AsyncSession,
        query_embedding: List[float],
        model: str = "text-embedding-3-small",
        limit: int = 5,
        min_similarity: float = 0.7,
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Search similar documents to an embedding vector
        
        Args:
            db: Asynchronous database session
            query_embedding: Embedding vector of the query
            model: Embedding model to use
            limit: Maximum number of results
            min_similarity: Minimum similarity to consider a result (0-1)
            user_id: ID of the owner user (to filter by user)
            
        Returns:
            List[Dict[str, Any]]: List of similar documents with their score
        """
        if not query_embedding:
            raise ValueError("The query embedding vector cannot be empty")
        
        try:
            # Convert the vector to its representation as a string for PostgreSQL
            embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
            
            # Use SQLAlchemy with text() for parameterized queries
            from sqlalchemy.sql import text
            
            sql = text("""
            SELECT 
                document_embeddings.id,
                document_embeddings.document_id, 
                document_embeddings.model,
                document_embeddings.chunk_index,
                document_embeddings.chunk_text,
                documents.id as doc_id,
                documents.title,
                documents.content,
                documents.file_path,
                documents.type,
                documents.user_id,
                1 - (document_embeddings.embedding <=> :embedding_vector) AS similarity
            FROM document_embeddings
            JOIN documents ON document_embeddings.document_id = documents.id
            WHERE document_embeddings.model = :model
            AND 1 - (document_embeddings.embedding <=> :embedding_vector) >= :min_similarity
            """)
            
            # Prepare parameters
            params = {
                "embedding_vector": embedding_str,
                "model": model,
                "min_similarity": min_similarity
            }
            
            # Add user filter if specified
            if user_id:
                sql = text(sql.text + " AND documents.user_id = :user_id")
                params["user_id"] = user_id
            
            # Add sorting and limit
            sql = text(sql.text + """
            ORDER BY similarity DESC
            LIMIT :limit
            """)
            params["limit"] = limit
            
            # Execute query with SQLAlchemy
            result = await db.execute(sql, params)
            rows = result.mappings().all()
            
            # Group by document
            docs_dict = {}
            for row in rows:
                doc_id = str(row["doc_id"])
                
                if doc_id not in docs_dict:
                    docs_dict[doc_id] = {
                        "document": {
                            "id": doc_id,
                            "title": row["title"],
                            "content": row["content"],
                            "file_path": row["file_path"],
                            "type": row["type"],
                            "user_id": str(row["user_id"])
                        },
                        "similarity": float(row["similarity"]),
                        "chunks": []
                    }
                
                # Add chunk to the list
                docs_dict[doc_id]["chunks"].append({
                    "chunk_text": row["chunk_text"],
                    "chunk_index": row["chunk_index"],
                    "similarity": float(row["similarity"])
                })
            
            # Convert to list of results
            results = []
            for doc_id, data in docs_dict.items():
                results.append({
                    "document": data["document"],
                    "similarity": data["similarity"],
                    "chunks": data["chunks"]
                })
            
            # Sort by similarity
            results.sort(key=lambda x: x["similarity"], reverse=True)
            
            return results[:limit]
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            raise
    
    async def generate_query_embedding(
        self,
        query_text: str,
        model: str = "text-embedding-3-small"
    ) -> List[float]:
        """
        Generate an embedding for a text query using OpenAI
        
        Args:
            query_text: Text of the query
            model: Model to use to generate the embedding
            
        Returns:
            List[float]: Embedding vector
        """
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured in the environment variables")
        
        try:
            # Create an AsyncClient without proxies
            http_client = httpx.AsyncClient()
            
            # Initialize AsyncOpenAI with the HTTP client
            client = AsyncOpenAI(
                api_key=api_key,
                http_client=http_client
            )
            
            response = await client.embeddings.create(
                input=query_text,
                model=model
            )
            
            # Extract the embedding vector
            embedding_vector = response.data[0].embedding
            
            # Close the HTTP client
            await http_client.aclose()
            
            return embedding_vector
        except Exception as e:
            logger.error(f"Error generating embedding for query: {str(e)}")
            raise
    
    async def rag_search(
        self,
        db: AsyncSession,
        query: str,
        model: str = "text-embedding-3-small",
        limit: int = 5,
        min_similarity: float = 0.2,
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform a RAG (Retrieval Augmented Generation) search
        
        Args:
            db: Asynchronous database session
            query: Text of the query
            model: Embedding model to use
            limit: Maximum number of results
            min_similarity: Minimum similarity to consider a result (0-1)
            user_id: ID of the owner user (to filter by user)
            
        Returns:
            List[Dict[str, Any]]: List of similar documents with their score
        """
        try:
            # Generate embedding for the query
            logger.info(f"Generating embedding for query: {query}")
            query_embedding = await self.generate_query_embedding(query, model)
            
            # Search similar documents
            logger.info(f"Searching similar documents")
            similar_docs = await self.search_similar_documents(
                db=db,
                query_embedding=query_embedding,
                model=model,
                limit=limit,
                min_similarity=min_similarity,
                user_id=user_id
            )
            
            logger.info(f"Found {len(similar_docs)} similar results")
            return similar_docs
        except Exception as e:
            logger.error(f"Error in RAG search: {str(e)}")
            raise
    
    async def search_documents_raw(
        self,
        db: AsyncSession,
        query: str,
        model: str,
        limit: int,
        min_similarity: float,
        user_id: UUID,
        document_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Search chunks of documents based on semantic similarity using pgvector.
        """
        logger.info(f"Starting raw search with query='{query}', model='{model}', limit={limit}, min_similarity={min_similarity}")
        api_key = settings.OPENAI_API_KEY
        try:
            # 1. Generate embedding for the query
            try:
                http_client = httpx.AsyncClient()
            
                # Initialize AsyncOpenAI with the HTTP client
                client = AsyncOpenAI(
                    api_key=api_key,
                    http_client=http_client
                )

                response = await client.embeddings.create(
                    input=query,
                    model=model,
                )
                query_embedding = response.data[0].embedding
                logger.info(f"Embedding generated with {len(query_embedding)} dimensions")

                # --- IMPORTANT: Close the httpx client explicitly ---
                await http_client.aclose()
                # -----------------------------------------------------

            except Exception as e:
                 logger.error(f"Error generating embedding for query '{query}' using model '{model}': {e}", exc_info=True)
                 # If httpx was created, try to close it before re-raising
                 if 'httpClient' in locals() and hasattr(http_client, 'aclose'):
                     try:
                         await http_client.aclose()
                     except Exception as close_err:
                         logger.error(f"Error closing httpClient after embedding failure: {close_err}")
                 raise ValueError(f"Could not generate embedding for query: {e}") from e

            # Convert embedding to string format pgvector '[f1,f2,...]'
            embedding_vector_string = "[" + ",".join(map(str, query_embedding)) + "]"

            # 2. Prepare the SQL query (no changes from the previous correction)
            query_sql = text("""
                SELECT
                    de.document_id,
                    d.title as document_title,
                    de.chunk_text,
                    de.chunk_index,
                    (1 - (de.embedding <=> :embedding_vector)) as similarity
                FROM
                    document_embeddings de
                JOIN
                    documents d ON de.document_id = d.id
                WHERE
                    de.model = :model
                    AND d.user_id = :user_id
                    AND (1 - (de.embedding <=> :embedding_vector)) >= :min_similarity
                    AND de.document_id = :document_id
                ORDER BY
                    similarity DESC
                LIMIT :limit
            """)

            # 3. Create the parameters dictionary (no changes)
            params_dict = {
                "embedding_vector": embedding_vector_string,
                "model": model,
                "user_id": user_id,
                "min_similarity": min_similarity,
                "limit": limit,
                "document_id": document_id
            }
            safe_params_log = {k: (v[:80] + '...' if k == 'embedding_vector' else v) for k, v in params_dict.items()}
            logger.info(f"Executing semantic search query")

            # 4. Execute the query (no changes)
            result = await db.execute(query_sql, params_dict)

            # 5. Get the results (no changes)
            search_results_raw = result.mappings().all()
            logger.info(f"Raw search found {len(search_results_raw)} results.")

            # 6. Convert to a list of dictionaries (no changes)
            search_results = [dict(row) for row in search_results_raw]

            return search_results

        except Exception as e:
            logger.error(f"Fatal error during raw document search: {str(e)}", exc_info=True)
            raise e # Re-raise to let the endpoint handle it
    