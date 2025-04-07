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
import asyncio
import aiofiles

# Import the LLM interface
from core.llm_interface import LLMClientInterface
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
    def __init__(self, llm_client: Optional[LLMClientInterface] = None):
        """
        Initialize DocumentService.
        
        Args:
            llm_client: An optional pre-initialized client implementing LLMClientInterface.
        """
        self.llm_client = llm_client # Store the generic client
        self.default_embedding_model = "text-embedding-3-small"
        
        if not self.llm_client:
             logger.warning("DocumentService initialized without an OpenAI client. Embedding generation will fail.")

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
        
        # Save the file physically (async)
        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
            logger.info(f"Successfully saved document file to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save document file to {file_path}: {e}", exc_info=True)
            # Decide if we should raise an error or continue without the file
            # For now, let's raise to signal the failure clearly
            raise IOError(f"Could not write document file to storage: {e}") from e
            
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
    
    async def get_document_with_details(self, db: AsyncSession, document_id: UUID) -> Optional[Document]:
        """
        Get a document by its ID, eagerly loading relationships needed for detailed views.

        Args:
            db: Asynchronous database session
            document_id: ID of the document to get

        Returns:
            Optional[Document]: Document found with details, or None
        """
        # Import PipelineExecution here if not already imported globally or locally
        from database.models.pipeline import PipelineExecution, Pipeline

        # Define the query with eager loading options
        query = (
            select(Document)
            .filter(Document.id == document_id)
            .options(
                selectinload(Document.embeddings), # Eager load embeddings
                selectinload(Document.processing_results), # Eager load processing results
                selectinload(Document.pipeline_executions).options( # Eager load executions...
                    selectinload(PipelineExecution.pipeline) # ...and their related pipeline
                )
            )
        )

        # Execute the query
        result = await db.execute(query)

        # Return the single result or None
        document = result.scalar_one_or_none()

        # Potentially synthesize processing_results here if needed as part of the service logic
        # Or leave it to the schema/API layer if preferred
        if document:
             # --- Synthesize processing_results from latest pipeline execution if needed ---
             if (not document.processing_results or len(document.processing_results) == 0) and document.pipeline_executions:
                 
                 # Create dictionaries from execution objects for easier processing
                 executions_data = []
                 for execution in document.pipeline_executions:
                      pipeline_name = execution.pipeline.name if execution.pipeline else "Unknown"
                      executions_data.append({
                         "id": execution.id,
                         "pipeline_id": execution.pipeline_id,
                         "document_id": execution.document_id,
                         "user_id": execution.user_id,
                         "status": execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
                         "started_at": execution.started_at,
                         "completed_at": execution.completed_at,
                         "created_at": execution.created_at,
                         "updated_at": execution.updated_at,
                         "pipeline_name": pipeline_name,
                         "results": execution.results, # Keep results as they are (likely dict)
                         "parameters": execution.parameters,
                         "error_message": execution.error_message
                     })

                 completed_executions = [exec_dict for exec_dict in executions_data 
                                          if exec_dict["status"] == "completed" and exec_dict.get("results")]

                 if completed_executions:
                     latest_execution = max(completed_executions, key=lambda x: x["completed_at"] if x["completed_at"] else x["created_at"])
                     
                     if latest_execution.get("results"):
                         # We need a ProcessingResult object or something compatible with the schema
                         # Let's assume we need to construct a dictionary matching ProcessingResultResponse
                         # Import necessary types/models if needed
                         import uuid # Ensure uuid is imported
                         import json # Ensure json is imported
                         # DocumentProcessingResult ORM class is not needed here as we create a dict

                         result_data = latest_execution.get("results") or {}
                         summary = None
                         keywords = None
                         token_count = None
                         process_metadata = {}

                         if isinstance(result_data.get("summary"), dict):
                             summary = result_data["summary"].get("summary")
                             process_metadata["summary_info"] = result_data["summary"]
                         elif isinstance(result_data.get("summary"), str):
                             summary = result_data["summary"]
                         
                         if isinstance(result_data.get("keywords"), list):
                             keywords = result_data["keywords"]

                         if "tokens_used" in result_data:
                             token_count = result_data.get("tokens_used")

                         for key, value in result_data.items():
                             if key not in ["summary", "keywords", "tokens_used"] and value is not None:
                                 try:
                                     json.dumps(value)
                                     process_metadata[key] = value
                                 except TypeError:
                                     process_metadata[key] = str(value)

                         # IMPORTANT: We need to create an object that matches the expected type 
                         # for the 'processing_results' relationship in the Document model.
                         # If it expects ProcessingResult ORM objects, we might need to create one.
                         # If the schema just expects dicts, creating a dict is fine.
                         # Let's assume for now we are creating a dict structure similar to the schema.
                         # This might need adjustment based on the actual ORM relationship type. 
                         synthesized_result = {
                              # "id": uuid.uuid4(), # ORM usually handles ID generation 
                              "document_id": document.id,
                              "pipeline_name": latest_execution["pipeline_name"],
                              "summary": summary,
                              "keywords": keywords or [],
                              "token_count": token_count,
                              "process_metadata": process_metadata,
                              # Timestamps might need conversion if expected as datetime objects
                              "created_at": latest_execution["completed_at"] or latest_execution["created_at"],
                              "updated_at": latest_execution["updated_at"]
                         }
                         
                         # If the relationship expects ORM objects:
                         # temp_processing_result = ProcessingResult(**synthesized_result)
                         # document.processing_results = [temp_processing_result] 
                         
                         # If the schema/relationship can handle dicts directly (less common for ORM relationships):
                         # We might need to adjust how this is assigned based on DocumentResponse schema definition
                         document.processing_results = [synthesized_result] # Assign list with synthesized dict
                         logger.info(f"Synthesized processing_results for document {document_id} from pipeline execution.")
             # -----------------------------------------------------------------------------

             logger.debug(f"Retrieved document {document_id} with details.")
             # Example: Synthesize logic could go here or be called from here
             # document = self._synthesize_processing_results(document)

        return document
    
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
        
        file_path_to_delete = Path(document.file_path) # Store path before deleting record
        
        await db.delete(document)
        await db.commit()
        
        # Attempt to delete the physical file after successful DB deletion
        try:
            if file_path_to_delete.exists() and file_path_to_delete.is_file():
                os.remove(file_path_to_delete)
                logger.info(f"Successfully deleted physical file: {file_path_to_delete}")
            else:
                logger.warning(f"Physical file not found or is not a file, skipping deletion: {file_path_to_delete}")
        except OSError as e:
            logger.error(f"Error deleting physical file {file_path_to_delete}: {e}", exc_info=True)
            # Do not re-raise; the primary goal (DB deletion) succeeded.
        
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
        user_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None
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
            document_id: Optional ID of a specific document to search within
            
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
            
            # Add document filter if specified
            if document_id:
                sql = text(sql.text + " AND documents.id = :document_id")
                params["document_id"] = document_id
            
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
        if not self.llm_client:
             logger.error("LLM client not available in DocumentService.")
             raise RuntimeError("LLM client is not configured for DocumentService.")

        effective_model = model or self.default_embedding_model
        logger.debug(f"Generating query embedding using model: {effective_model}")

        try:
            # Use the interface method
            embeddings_list = await self.llm_client.generate_embeddings(
                texts=[query_text], # Interface expects a list
                model=effective_model,
            )
            
            if not embeddings_list or not embeddings_list[0]:
                raise ValueError("LLM client did not return valid embeddings.")

            embedding = embeddings_list[0] # Get the first (and only) embedding
            logger.debug(f"Successfully generated query embedding. Dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}", exc_info=True)
            # Re-raise a more specific or generic error
            raise RuntimeError(f"Failed to generate query embedding via LLM client: {e}") from e
    
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
        Search chunks within a specific document based on semantic similarity using pgvector.
        Reuses the core search logic but targets a single document.
        """
        logger.info(f"Starting raw search within document {document_id} with query='{query}', model='{model}', limit={limit}, min_similarity={min_similarity}")
        try:
            # 1. Generate embedding for the query using the service method
            query_embedding = await self.generate_query_embedding(query, model)
            logger.info(f"Embedding generated with {len(query_embedding)} dimensions")

            # 2. Call the extended search_similar_documents method
            search_results = await self.search_similar_documents(
                db=db,
                query_embedding=query_embedding,
                model=model,
                limit=limit,
                min_similarity=min_similarity,
                user_id=user_id, # Pass user_id for potential filtering within search_similar_documents
                document_id=document_id # Pass the specific document_id
            )

            logger.info(f"Raw search found {len(search_results)} results within document {document_id}.")

            return search_results

        except ValueError as ve:
            # Specific handling for embedding generation errors
            logger.error(f"Error generating embedding for raw search query '{query}': {ve}", exc_info=True)
            raise ValueError(f"Could not generate embedding for query: {ve}") from ve
        except Exception as e:
            logger.error(f"Fatal error during raw document search within document {document_id}: {str(e)}", exc_info=True)
            raise e # Re-raise to let the endpoint handle it
    