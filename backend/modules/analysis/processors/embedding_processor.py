"""
Procesador de embeddings para documentos
"""
from typing import Dict, Any, List, Optional, Union, TypeVar, Generic
import uuid
import logging
import asyncio
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from core.llm_interface import LLMClientInterface

logger = logging.getLogger(__name__)

# Definir un tipo genérico para las sesiones de base de datos
T = TypeVar('T', Session, AsyncSession)

class EmbeddingProcessor(Generic[T]):
    """Procesador para la generación de embeddings de documentos"""
    
    def __init__(self, llm_client: LLMClientInterface):
        self.llm_client = llm_client
        self.default_embedding_model = "text-embedding-3-small"
        
    async def generate_embeddings(
        self, 
        text_content: str, 
        chunk_size: int = 2000, 
        overlap: int = 200,
        model: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generar embeddings para el contenido de texto
        
        Args:
            text_content: Contenido de texto
            chunk_size: Tamaño de cada chunk
            overlap: Superposición entre chunks
            model: Modelo de embedding a usar (opcional)
            
        Returns:
            Dict[str, Any]: Resultados con embeddings y metadatos
        """
        # Verificar que hay contenido
        if not text_content:
            logger.warning("No hay contenido de texto para generar embeddings")
            return {
                "embeddings": [],
                "embedding_model": self.default_embedding_model,
                "chunk_count": 0
            }
        
        # Dividir texto en chunks
        chunks = self._split_text_into_chunks(text_content, chunk_size, overlap)
        
        # Modelo a usar
        embedding_model = model or self.default_embedding_model
        
        # Generar embeddings para cada chunk
        embeddings = []
        for chunk in chunks:
            try:
                # Generar embedding con el cliente LLM
                embedding_vector = await self.llm_client.generate_embeddings(
                    texts=[chunk],
                    model=embedding_model,
                    user_id=user_id
                )
                
                logger.info(f"Embedding generado para chunk (longitud: {len(chunk)})")
                
                # Asegurarse de que el vector sea una lista de Python, no un array de NumPy
                if isinstance(embedding_vector, np.ndarray):
                    embedding_vector = embedding_vector.tolist()
                
                # Añadir a la lista de embeddings
                embeddings.append({
                    "chunk_text": chunk,
                    "embedding_vector": embedding_vector
                })
            except Exception as e:
                logger.error(f"Error al generar embedding: {e}")
                # Continuar con el siguiente chunk
        
        return {
            "embeddings": embeddings,
            "embedding_model": embedding_model,
            "chunk_count": len(chunks),
            "token_usage": {
                "input_tokens": len(chunks) * self.llm_client.token_counter.count_tokens(chunks[0], embedding_model) if chunks else 0,
                "model": embedding_model,
                "user_id": user_id
            }
        }
    
    def save_embeddings_sync(
        self, 
        db: Session, 
        pipeline_id: uuid.UUID, 
        embeddings: List[Dict[str, Any]], 
        embedding_model: str = "default"
    ) -> List:
        """
        Guardar embeddings en la base de datos asociados a un pipeline (versión síncrona para Celery)
        
        Args:
            db: Sesión de base de datos síncrona
            pipeline_id: ID del pipeline de análisis
            embeddings: Lista de embeddings con texto de chunk
            embedding_model: Nombre del modelo de embedding
            
        Returns:
            List: Objetos de embedding creados
        """
        # Importar aquí para evitar importaciones circulares
        from database.models.analysis import PipelineEmbedding
        
        # Serializar embeddings para JSON
        from utils.serialization import serialize_for_json
        serialized_embeddings = serialize_for_json(embeddings)
        
        # Crear objetos de embedding
        db_embeddings = []
        for idx, embedding_data in enumerate(serialized_embeddings):
            embedding_vector = embedding_data["embedding_vector"]
            chunk_text = embedding_data["chunk_text"]
            
            # Asegurarse de que el vector sea una lista de Python, no un array de NumPy
            if isinstance(embedding_vector, np.ndarray):
                embedding_vector = embedding_vector.tolist()
            
            # Crear objeto de embedding
            db_embedding = PipelineEmbedding(
                pipeline_id=pipeline_id,
                embedding_vector=embedding_vector,
                chunk_text=chunk_text,
                chunk_index=idx,
                metadata_info={
                    "embedding_model": embedding_model,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            db.add(db_embedding)
            db_embeddings.append(db_embedding)
        
        # Guardar cambios con API síncrona
        try:
            db.commit()
            
            # Actualizar objetos
            for db_embedding in db_embeddings:
                db.refresh(db_embedding)
                
            return db_embeddings
        except Exception as e:
            logger.error(f"Error al guardar embeddings: {str(e)}")
            db.rollback()
            raise
            
    async def save_embeddings_async(
        self, 
        db: AsyncSession, 
        pipeline_id: uuid.UUID, 
        embeddings: List[Dict[str, Any]], 
        embedding_model: str = "default"
    ) -> List:
        """
        Guardar embeddings en la base de datos asociados a un pipeline (versión asíncrona para FastAPI)
        
        Args:
            db: Sesión de base de datos asíncrona
            pipeline_id: ID del pipeline de análisis
            embeddings: Lista de embeddings con texto de chunk
            embedding_model: Nombre del modelo de embedding
            
        Returns:
            List: Objetos de embedding creados
        """
        # Importar aquí para evitar importaciones circulares
        from database.models.analysis import PipelineEmbedding
        
        # Serializar embeddings para JSON
        from utils.serialization import serialize_for_json
        serialized_embeddings = serialize_for_json(embeddings)
        
        # Crear objetos de embedding
        db_embeddings = []
        for idx, embedding_data in enumerate(serialized_embeddings):
            embedding_vector = embedding_data["embedding_vector"]
            chunk_text = embedding_data["chunk_text"]
            
            # Asegurarse de que el vector sea una lista de Python, no un array de NumPy
            if isinstance(embedding_vector, np.ndarray):
                embedding_vector = embedding_vector.tolist()
            
            # Crear objeto de embedding
            db_embedding = PipelineEmbedding(
                pipeline_id=pipeline_id,
                embedding_vector=embedding_vector,
                chunk_text=chunk_text,
                chunk_index=idx,
                metadata_info={
                    "embedding_model": embedding_model,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            db.add(db_embedding)
            db_embeddings.append(db_embedding)
        
        # Guardar cambios con API asíncrona
        try:
            await db.commit()
            
            # Actualizar objetos
            for db_embedding in db_embeddings:
                await db.refresh(db_embedding)
                
            return db_embeddings
        except Exception as e:
            logger.error(f"Error al guardar embeddings: {str(e)}")
            await db.rollback()
            raise
            
    # Método de compatibilidad para código existente
    def save_embeddings(
        self, 
        db: Union[Session, AsyncSession], 
        pipeline_id: uuid.UUID, 
        embeddings: List[Dict[str, Any]], 
        embedding_model: str = "default"
    ) -> List:
        """
        Guardar embeddings en la base de datos asociados a un pipeline
        (método de compatibilidad que detecta el tipo de sesión)
        
        Args:
            db: Sesión de base de datos (síncrona o asíncrona)
            pipeline_id: ID del pipeline de análisis
            embeddings: Lista de embeddings con texto de chunk
            embedding_model: Nombre del modelo de embedding
            
        Returns:
            List: Objetos de embedding creados
        """
        if isinstance(db, AsyncSession):
            logger.warning("Usando save_embeddings con AsyncSession. Considere usar save_embeddings_async en su lugar.")
            # Ejecutar la versión asíncrona en un bucle de eventos
            return asyncio.run(self.save_embeddings_async(db, pipeline_id, embeddings, embedding_model))
        else:
            return self.save_embeddings_sync(db, pipeline_id, embeddings, embedding_model)
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Dividir texto en chunks
        
        Args:
            text: Texto a dividir
            chunk_size: Tamaño de cada chunk
            overlap: Superposición entre chunks
            
        Returns:
            List[str]: Lista de chunks de texto
        """
        # Chunking simple por conteo de caracteres
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks
