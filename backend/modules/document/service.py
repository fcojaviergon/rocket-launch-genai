import os
import uuid
from pathlib import Path
from sqlalchemy import select, func, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging
import json
from datetime import datetime
from sqlalchemy.orm import selectinload
import aiofiles

from database.models.document import Document
from database.models.analysis import PipelineEmbedding, AnalysisPipeline
from schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse
from core.config import settings

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
# load_dotenv() # Removed, should be handled centrally if needed

# Ensure that the storage directory exists - REMOVED as it caused permission errors in worker
# and is handled within create_document method.
# os.makedirs(settings.DOCUMENT_STORAGE_PATH, exist_ok=True)

class DocumentService:
    def __init__(self, llm_client=None):
        """
        Initialize DocumentService.
        
        Args:
            llm_client: Optional LLM client for generating embeddings
        """
        self.llm_client = llm_client

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
        
        logger.info(f"File name: {file_name}")

        # Use the global storage path from settings, converting to Path object
        storage_path = Path(settings.DOCUMENT_STORAGE_PATH)
        file_path = storage_path / file_name
        
        logger.info(f"File name: {file_name}, File path: {file_path}")
        
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
            
        # Determine file size and extension
        file_size = len(content)
        file_ext = Path(document_data.name).suffix.lower() if document_data.name else ".bin"
        
        # NEVER store binary content in the database
        # Instead, store a description of the file and its location
        decoded_content = f"[Documento {file_ext} - {file_size} bytes]"
            
        document = Document(
            title=document_data.name,
            filename=decoded_content,
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

        )
        return result.scalar_one_or_none()
    
    
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
    
    
    async def search_similar_documents(
        self, 
        db: AsyncSession, 
        query_embedding: List[float], 
        user_id: UUID, 
        limit: int = 5, 
        min_similarity: float = 0.5,
        model: str = "text-embedding-3-small",
        analysis_id: Optional[UUID] = None # Add optional analysis_id filter
    ) -> List[Dict[str, Any]]: # Return list of dicts representing chunks
        """
        Busca fragmentos de documentos similares basados en vectores de embedding.
        Retorna una lista de fragmentos con información del documento y similitud.
        Ahora usa PipelineEmbedding en lugar de DocumentEmbedding.
        """
        logger.info(f"Buscando documentos similares con {len(query_embedding)} dimensiones, min_similarity={min_similarity}")
        
        try:
            # Preparar la consulta
            # Convertir el embedding a un array de NumPy para pgvector
            from pgvector.sqlalchemy import Vector
            import numpy as np
            
            # Convertir a array numpy y luego al formato pgvector
            query_vector = np.array(query_embedding, dtype=np.float32)
            
            # Calcular similitud de coseno
            from sqlalchemy import func
            similarity = func.cosine_similarity(PipelineEmbedding.embedding_vector, query_vector)
            
            # Comenzar a construir la consulta
            query = (
                select(
                    PipelineEmbedding,
                    AnalysisPipeline,
                    Document,
                    similarity.label("similarity")
                )
                .join(AnalysisPipeline, PipelineEmbedding.pipeline_id == AnalysisPipeline.id)
                .join(Document, AnalysisPipeline.document_id == Document.id)
                .where(similarity >= min_similarity)
            )
            
            # Añadir filtro por model si se especifica (ahora en metadata_info)
            if model:
                # En PipelineEmbedding, el modelo está en el campo metadata_info
                # Usamos la función JSON -> para acceder a la propiedad 'model'
                query = query.where(PipelineEmbedding.metadata_info['model'].astext == model)
                
            # Añadir filtro por user_id si se proporciona
            if user_id:
                query = query.where(Document.user_id == user_id)
                
            # Añadir filtro por analysis_id si se proporciona
            if analysis_id:
                # Ahora podemos filtrar directamente por el scenario_id en AnalysisPipeline
                query = query.where(AnalysisPipeline.scenario_id == analysis_id)
                
            # Ordenar por similitud descendente y limitar resultados
            query = query.order_by(similarity.desc()).limit(limit)
            
            # Ejecutar la consulta
            result = await db.execute(query)
            rows = result.all()
            
            # Procesar los resultados
            results = []
            for row in rows:
                embedding, pipeline, document, similarity_score = row
                
                # Formatear el resultado
                result_item = {
                    "document_id": str(document.id),
                    "document_title": document.title,
                    "pipeline_id": str(pipeline.id),
                    "pipeline_type": pipeline.pipeline_type.value,
                    "chunk_text": embedding.chunk_text,
                    "chunk_index": embedding.chunk_index,
                    "similarity": float(similarity_score),
                    "model": embedding.metadata_info.get("model", "unknown")
                }
                
                results.append(result_item)
                
            logger.info(f"Encontrados {len(results)} documentos similares")
            return results
            
        except Exception as e:
            logger.error(f"Error buscando documentos similares: {e}", exc_info=True)
            raise
    
    async def generate_query_embedding(
        self,
        query_text: str,
        model: str = "text-embedding-3-small"
    ) -> List[float]:
        """
        Generate an embedding for a text query using the configured LLM client
        
        Args:
            query_text: Text of the query
            model: Model to use to generate the embedding
            
        Returns:
            List[float]: Embedding vector
        """
        if not self.llm_client:
            logger.error("LLM client not available in DocumentService.")
            raise RuntimeError("LLM client is not configured for DocumentService.")

        effective_model = model or "text-embedding-3-small"
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
    
    async def search_documents_by_analysis_id(
        self,
        db: AsyncSession,
        query: str,
        model: str,
        limit: int,
        min_similarity: float,
        user_id: UUID,
        analysis_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Busca fragmentos dentro de un escenario de análisis específico basado en similitud semántica.
        Reutiliza la lógica de búsqueda principal pero se enfoca en un escenario específico.
        """
        logger.info(f"Iniciando búsqueda semántica en el escenario {analysis_id} con query='{query}', model='{model}', limit={limit}, min_similarity={min_similarity}")
        try:
            # 1. Generar embedding para la consulta usando el método del servicio
            query_embedding = await self.generate_query_embedding(query, model)
            logger.info(f"Embedding generado con {len(query_embedding)} dimensiones")

            # 2. Llamar al método search_similar_documents con el ID del escenario
            search_results = await self.search_similar_documents(
                db=db,
                query_embedding=query_embedding,
                model=model,
                limit=limit,
                min_similarity=min_similarity,
                user_id=user_id,
                analysis_id=analysis_id # Pasar el ID del escenario específico
            )

            logger.info(f"Búsqueda encontró {len(search_results)} resultados en el escenario {analysis_id}.")

            return search_results

        except ValueError as ve:
            # Manejo específico para errores de generación de embeddings
            logger.error(f"Error generando embedding para la consulta '{query}': {ve}", exc_info=True)
            raise ValueError(f"No se pudo generar embedding para la consulta: {ve}") from ve
        except Exception as e:
            logger.error(f"Error fatal durante la búsqueda en el escenario {analysis_id}: {str(e)}", exc_info=True)
            raise e # Re-lanzar para que el endpoint lo maneje
    
   