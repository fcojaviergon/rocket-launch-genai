"""
Tareas Celery para el procesamiento de documentos
"""
import uuid
from typing import Dict, Any
from datetime import datetime

from database.session import get_sync_session_context
from database.models.document import Document, ProcessingStatus
from database.models.analysis import PipelineEmbedding
from core.events import get_event_manager
import logging
from sqlalchemy import func

from tasks.worker import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="process_document_content")
def process_document_content(document_id: str, pipeline_id: str) -> Dict[str, Any]:
    """
    Procesar el contenido de un documento y generar embeddings
    
    Args:
        document_id: ID del documento
        pipeline_id: ID del pipeline
        
    Returns:
        Dict[str, Any]: Resultados del procesamiento
    """
    # Convertir a UUID
    document_id_uuid = uuid.UUID(document_id)
    pipeline_id_uuid = uuid.UUID(pipeline_id)
    
    try:
        # Usar context manager para sesiones síncronas en Celery
        with get_sync_session_context() as db:
            # Publicar evento de inicio de procesamiento
            event_manager = get_event_manager()
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id_uuid}",
                "document_processing_started",
                {"document_id": str(document_id_uuid)}
            )
            
            # Obtener documento usando API síncrona
            document = db.query(Document).filter(Document.id == document_id_uuid).first()
            if not document:
                raise ValueError(f"Documento {document_id_uuid} no encontrado")
                
            # Inicializar procesadores
            from modules.analysis.processors.document_processor import DocumentProcessor
            from modules.analysis.processors.embedding_processor import EmbeddingProcessor
            from core.dependencies import get_llm_client_instance
            
            llm_client = get_llm_client_instance()
            doc_processor = DocumentProcessor()
            embedding_processor = EmbeddingProcessor(llm_client=llm_client)
            
            # Procesar el documento
            doc_results = doc_processor.process_document(document)
            
            # Generar embeddings
            text_content = doc_results.get("text_content", "")
            
            # Verificar si ya existen embeddings para este documento en este pipeline
            existing_embeddings = db.query(func.count()).select_from(PipelineEmbedding).filter(
                PipelineEmbedding.pipeline_id == pipeline_id_uuid,
                func.json_extract_path_text(PipelineEmbedding.metadata_info, 'document_id') == str(document_id_uuid)
            ).scalar()
            
            if existing_embeddings > 0:
                logger.info(f"Ya existen {existing_embeddings} embeddings para el documento {document_id} en el pipeline {pipeline_id}. Omitiendo generación.")
                
                # Actualizar el estado del documento a COMPLETED si no lo está ya
                if document.processing_status != ProcessingStatus.COMPLETED:
                    document.processing_status = ProcessingStatus.COMPLETED
                    document.processed_at = datetime.utcnow()
                    db.commit()
                
                # Publicar evento de finalización
                event_manager.publish_realtime(
                    f"pipeline:{pipeline_id}",
                    "document_processing_completed",
                    {
                        "document_id": str(document_id),
                        "embeddings_count": existing_embeddings,
                        "reused": True
                    }
                )
                
                return {
                    "status": "success",
                    "document_id": str(document_id),
                    "embeddings_count": existing_embeddings,
                    "reused": True
                }
            
            # Generar embeddings con el procesador
            embeddings_result = llm_client.generate_embeddings(
                texts=[text_content],
                chunk_size=2000,
                overlap=200,
                user_id=str(document.user_id) if document.user_id else None
            )
            
            # Guardar embeddings
            if embeddings_result and "embeddings" in embeddings_result and embeddings_result["embeddings"]:
                try:
                    # Guardar embeddings en la base de datos
                    saved_embeddings = embedding_processor.save_embeddings_sync(
                        db=db,
                        pipeline_id=pipeline_id_uuid,
                        embeddings=embeddings_result["embeddings"],
                        embedding_model=embeddings_result.get("embedding_model", "text-embedding-3-small")
                    )
                    
                    saved_count = len(saved_embeddings)
                    
                    # Actualizar metadatos de los embeddings con el ID del documento
                    for embedding in saved_embeddings:
                        if embedding.metadata_info is None:
                            embedding.metadata_info = {}
                        
                        embedding.metadata_info.update({
                            "document_id": str(document_id),
                            "chunk_size": embeddings_result.get("chunk_size", 2000),
                            "overlap": embeddings_result.get("overlap", 200)
                        })
                    
                    # Actualizar el estado del documento
                    document.processing_status = ProcessingStatus.COMPLETED
                    document.processed_at = datetime.utcnow()
                    
                    # Guardar cambios
                    db.commit()
                    
                    logger.info(f"Guardados {saved_count} embeddings para el documento {document_id}")
                    
                    # Publicar evento de finalización
                    event_manager.publish_realtime(
                        f"pipeline:{pipeline_id}",
                        "document_processing_completed",
                        {
                            "document_id": str(document_id),
                            "embeddings_count": saved_count,
                            "reused": False
                        }
                    )
                    
                    return {
                        "status": "success",
                        "document_id": str(document_id),
                        "embeddings_count": saved_count,
                        "reused": False
                    }
                except Exception as save_error:
                    db.rollback()
                    logger.error(f"Error al guardar embeddings: {save_error}")
                    
                    # Actualizar estado a FAILED
                    document.processing_status = ProcessingStatus.FAILED
                    document.error_message = f"Error al guardar embeddings: {str(save_error)}"
                    db.commit()
                    
                    # Publicar evento de error
                    event_manager.publish_realtime(
                        f"pipeline:{pipeline_id}",
                        "document_processing_error",
                        {
                            "document_id": str(document_id),
                            "error": str(save_error)
                        }
                    )
                    
                    raise save_error
            else:
                logger.warning(f"No hay embeddings para guardar para el documento {document_id}")
                
                # Actualizar el estado del documento a COMPLETED
                document.processing_status = ProcessingStatus.COMPLETED
                document.processed_at = datetime.utcnow()
                db.commit()
                
                # Publicar evento de finalización
                event_manager.publish_realtime(
                    f"pipeline:{pipeline_id}",
                    "document_processing_completed",
                    {
                        "document_id": str(document_id),
                        "embeddings_count": 0,
                        "reused": False
                    }
                )
                
                return {
                    "status": "success",
                    "document_id": str(document_id),
                    "embeddings_count": 0,
                    "reused": False
                }
    except Exception as e:
        logger.error(f"Error al procesar documento {document_id}: {e}", exc_info=True)
        
        # Publicar evento de error
        try:
            event_manager = get_event_manager()
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "document_processing_error",
                {
                    "document_id": str(document_id),
                    "error": str(e)
                }
            )
        except Exception as event_error:
            logger.error(f"Error al publicar evento de error: {event_error}")
        
        return {
            "status": "error",
            "error": str(e),
            "document_id": document_id
        }