import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import numpy as np
from pgvector.sqlalchemy import Vector
from openai import AsyncOpenAI
import logging
import httpx
import json # Import json for serialization check
from datetime import datetime # Import datetime
from sqlalchemy.sql import text
from sqlalchemy.sql.expression import bindparam
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
import asyncio
import aiofiles

# Import the LLM interface
from core.llm_interface import LLMClientInterface
from database.models.document import Document, DocumentEmbedding, DocumentProcessingResult # Ensure ProcessingResult model is imported
from database.models.pipeline import PipelineExecution, Pipeline # Import pipeline models
from schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse, DocumentProcessingResultResponse, PipelineExecutionResponse # Import necessary schemas
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
        
        # --- Trigger asynchronous embedding processing --- 
        # This section is removed as processing is now triggered via a separate API endpoint
        # try:
        #     await self.process_document_embeddings_async(document.id)
        #     logger.info(f"Successfully enqueued embedding task for document {document.id}")
        # except Exception as task_error:
        #     logger.error(f"Failed to enqueue embedding task for document {document.id}: {task_error}", exc_info=True)
        # --- End Trigger --- 
        
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
    
    async def get_document_with_details(self, db: AsyncSession, document_id: UUID) -> Optional[DocumentResponse]:
        """
        Get a document by its ID, with related data, and synthesize processing results.
        Returns a DocumentResponse Pydantic model, not the ORM object.

        Args:
            db: Asynchronous database session
            document_id: ID of the document to get

        Returns:
            Optional[DocumentResponse]: Populated response schema or None if not found.
        """
        # Fetch the ORM object with eager loading
        query = (
            select(Document)
            .filter(Document.id == document_id)
            .options(
                selectinload(Document.embeddings),
                selectinload(Document.processing_results),
                selectinload(Document.pipeline_executions).options(
                    selectinload(PipelineExecution.pipeline)
                )
            )
        )
        result = await db.execute(query)
        document_orm = result.scalar_one_or_none()

        if not document_orm:
            return None

        # --- Start Synthesis Logic --- 
        final_processing_results: Optional[List[DocumentProcessingResultResponse]] = None

        # 1. Check for existing results in the database
        if document_orm.processing_results:
            logger.debug(f"Document {document_id}: Using DB processing results.")
            # Convert ORM results to Pydantic response models
            final_processing_results = [
                DocumentProcessingResultResponse.model_validate(res)
                for res in document_orm.processing_results
            ]
        # 2. If no DB results, try synthesizing from executions
        elif document_orm.pipeline_executions:
            logger.debug(f"Document {document_id}: No DB results, attempting synthesis from executions.")
            # Convert ORM executions to Pydantic response models for easier handling
            executions_data = [
                 PipelineExecutionResponse.model_validate(exec)
                 for exec in document_orm.pipeline_executions
            ]
            completed_executions = [
                exec_data for exec_data in executions_data
                if exec_data.status == "completed" and isinstance(exec_data.results, dict)
            ]
            if completed_executions:
                logger.debug(f"Document {document_id}: Found {len(completed_executions)} completed executions with dict results.")
                try:
                    latest_execution = max(
                        completed_executions,
                        key=lambda x: x.completed_at or x.created_at or datetime.min
                    )
                    logger.debug(f"Document {document_id}: Latest execution {latest_execution.id} completed at {latest_execution.completed_at}")

                    # Parse nested Celery task results
                    celery_task_output = latest_execution.results or {}
                    pipeline_executor_output = celery_task_output.get("results", {})
                    pipeline_summary_obj = pipeline_executor_output.get("summary", {})
                    extracted_info = pipeline_summary_obj.get("extracted_info", {})

                    if not extracted_info and not pipeline_executor_output.get("errors"):
                        logger.warning(f"Document {document_id}, Execution {latest_execution.id}: No extracted_info found, cannot synthesize.")
                    elif pipeline_executor_output.get("errors"):
                         logger.warning(f"Document {document_id}, Execution {latest_execution.id}: Pipeline execution failed, not synthesizing.")
                    else:
                        # Extract data for synthesized result
                        summary = extracted_info.get("summary")
                        keywords = extracted_info.get("keywords")
                        token_count = pipeline_executor_output.get("total_tokens_used")
                        process_metadata = {}
                        for key, value in extracted_info.items():
                             if key not in ["summary", "keywords"] and value is not None:
                                  try: json.dumps(value); process_metadata[key] = value
                                  except (TypeError, OverflowError): process_metadata[key] = f"[Unserializable: {type(value).__name__}]"

                        # Construct the Pydantic model for the synthesized result
                        synthesized_result = DocumentProcessingResultResponse(
                            id=None,
                            document_id=document_id,
                            pipeline_name=pipeline_executor_output.get("pipeline_name", "Unknown Pipeline"),
                            summary=summary,
                            keywords=keywords,
                            token_count=token_count,
                            process_metadata=process_metadata,
                            created_at=latest_execution.completed_at or latest_execution.created_at or datetime.now(),
                            updated_at=latest_execution.completed_at or latest_execution.created_at or datetime.now(),
                        )
                        logger.debug(f"Document {document_id}: Synthesized result created.")
                        final_processing_results = [synthesized_result]
                except Exception as e:
                     logger.error(f"Document {document_id}: Error during synthesis logic in service: {e}", exc_info=True)
            else:
                 logger.debug(f"Document {document_id}: No suitable completed executions found for synthesis.")
        else:
             logger.debug(f"Document {document_id}: No DB results and no pipeline executions found for synthesis.")
        # --- End Synthesis Logic --- 

        # Manually construct the DocumentResponse Pydantic model
        document_response = DocumentResponse.model_validate(document_orm)
        # Assign the final (DB or synthesized) processing results
        document_response.processing_results = final_processing_results
        # Ensure pipeline executions are also assigned (model_validate should handle this via from_attributes)
        # document_response.pipeline_executions = [PipelineExecutionResponse.model_validate(e) for e in document_orm.pipeline_executions] if document_orm.pipeline_executions else None

        return document_response
    
    async def get_user_documents(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        type: Optional[str] = None
    ) -> List[DocumentResponse]:
        """
        Get all documents of a user
        
        Args:
            db: Asynchronous database session
            user_id: ID of the user
            skip: Number of records to skip
            limit: Limit of records to get
            type: Document type to filter
            
        Returns:
            List[DocumentResponse]: List of documents
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
        documents_orm = result.scalars().all()
        # Convert ORM objects to Pydantic models before returning
        return [DocumentResponse.model_validate(doc) for doc in documents_orm]
    
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
        embeddings: List[List[float]], # Be specific: List of float lists
        chunks_text: List[str],      # Be specific: List of strings
        model: str,                  # Add model parameter
        batch_size: int = 100
    ) -> List[DocumentEmbedding]: # Return the saved ORM objects
        """
        Save the embeddings of a document in the database, replacing existing ones for the same model.
        
        Args:
            db: Asynchronous database session
            document_id: ID of the document
            embeddings: List of embedding vectors
            chunks_text: List of corresponding text chunks
            model: Name of the embedding model used
            batch_size: Number of embeddings to save in each batch (currently unused)
            
        Returns:
            List[DocumentEmbedding]: List of the created DocumentEmbedding ORM objects.
        """
        # Verify that the document exists
        document = await db.get(Document, document_id) # Use db.get for primary key lookup
        if not document:
            raise ValueError(f"The document with ID {document_id} does not exist")
        
        # Verify that there is the same number of embeddings and chunks of text
        if len(embeddings) != len(chunks_text):
            raise ValueError(f"Number of embeddings ({len(embeddings)}) does not match chunks_text ({len(chunks_text)})")
            
        # Delete previous embeddings for the same document and model
        # Use await db.execute with delete() - more efficient for bulk deletes
        delete_stmt = delete(DocumentEmbedding).where(
            (DocumentEmbedding.document_id == document_id) &
            (DocumentEmbedding.model == model) # Use the provided model
        )
        await db.execute(delete_stmt)
        logger.info(f"Deleted existing embeddings for document {document_id} and model '{model}'")
        
        # Save the new embeddings
        saved_embeddings = []
        new_embedding_objects = [] # Collect objects to add in bulk
        for i, (embedding, chunk_text) in enumerate(zip(embeddings, chunks_text)):
            # Create the embedding model
            db_embedding = DocumentEmbedding(
                document_id=document_id,
                model=model, # Use the provided model
                embedding=embedding,
                chunk_index=i,
                chunk_text=chunk_text
            )
            new_embedding_objects.append(db_embedding)
            
        db.add_all(new_embedding_objects) # Use add_all for efficiency
        await db.flush() # Flush to assign IDs if needed before returning
        # No need to commit here if called within a transaction (like from the Celery task)
        # The caller (Celery task context manager) should handle the commit.
        logger.info(f"Added {len(new_embedding_objects)} new embeddings for document {document_id} model '{model}'")
        
        # Return the newly created objects (they have IDs after flush)
        return new_embedding_objects
    
    async def search_similar_documents(
        self, 
        db: AsyncSession, 
        query_embedding: List[float], 
        user_id: UUID, 
        limit: int = 5, 
        min_similarity: float = 0.5,
        model: str = "text-embedding-3-small",
        document_id: Optional[UUID] = None # Add optional document_id filter
    ) -> List[Dict[str, Any]]: # Return list of dicts representing chunks
        """
        Search similar document chunks based on embedding vector.
        Returns a list of chunks with their document info and similarity.
        """
        if not query_embedding:
            raise ValueError("The query embedding vector cannot be empty")

        try:
            embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
            from sqlalchemy.sql import text

            # Select individual chunks and join document info
            sql = text("""
            SELECT 
                de.id as embedding_id,
                de.document_id, 
                de.model,
                de.chunk_index,
                de.chunk_text,
                d.id as doc_id,
                d.title as doc_title,
                d.file_path as doc_file_path,
                d.type as doc_type,
                d.user_id as doc_user_id,
                1 - (de.embedding <=> :embedding_vector) AS similarity
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            WHERE de.model = :model
            AND 1 - (de.embedding <=> :embedding_vector) >= :min_similarity
            """)

            params = {
                "embedding_vector": embedding_str,
                "model": model,
                "min_similarity": min_similarity
            }

            if user_id:
                sql = text(sql.text + " AND d.user_id = :user_id")
                params["user_id"] = user_id

            if document_id:
                sql = text(sql.text + " AND d.id = :document_id")
                params["document_id"] = document_id

            sql = text(sql.text + " ORDER BY similarity DESC LIMIT :limit")
            params["limit"] = limit

            result = await db.execute(sql, params)
            rows = result.mappings().all()

            # Format results as a list of chunks with document info
            results = []
            for row in rows:
                results.append({
                    "chunk_text": row["chunk_text"],
                    "chunk_index": row["chunk_index"],
                    "similarity": float(row["similarity"]),
                    "document": {
                        "id": str(row["doc_id"]),
                        "title": row["doc_title"],
                        "file_path": row["doc_file_path"],
                        "type": row["doc_type"],
                        "user_id": str(row["doc_user_id"])
                        # Add other document fields if needed by frontend
                    }
                })

            return results
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
    
    # --- Async Document Processing Trigger --- 
    async def process_document_embeddings_async(self, document_id: UUID):
        """Triggers the Celery task for processing embeddings asynchronously."""
        from tasks.tasks import process_document_embeddings_task
        try:
            logger.info(f"Sending embedding processing task for document ID: {document_id}")
            process_document_embeddings_task.delay(str(document_id))
            logger.info(f"Celery task process_document_embeddings enqueued for document {document_id}.")
        except Exception as e:
            logger.error(f"Failed to send Celery task for document {document_id}: {e}", exc_info=True)
            # Optionally update document status to failed here
            # await self.update_document_status(db, document_id, ProcessingStatus.FAILED)
            raise
            
    async def update_document_status(self, db: AsyncSession, document_id: UUID, status: str):
        """Updates the processing status of a document."""
        stmt = select(Document).filter(Document.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if doc:
            doc.processing_status = status
            await db.commit()
            logger.info(f"Updated document {document_id} status to {status}")
        else:
            logger.warning(f"Attempted to update status for non-existent document {document_id}")
    