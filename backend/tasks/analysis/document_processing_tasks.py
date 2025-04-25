"""
Tareas Celery para el procesamiento de documentos
"""
import uuid
from typing import Dict, Any
from datetime import datetime
import asyncio

from database.session import get_sync_session_context
from database.models.document import Document, ProcessingStatus
from database.models.analysis import PipelineEmbedding
from core.events import get_event_manager
import logging
from sqlalchemy import func

from tasks.worker import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="process_document_content")
def process_document_content(document_id: str, pipeline_id: str, requester_user_id: str = None) -> Dict[str, Any]:
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
            
            # Lógica simplificada para procesar documentos
            # Cada pipeline es independiente y necesita sus propios embeddings
            
            # Verificar si ya existen embeddings para este documento en este pipeline
            existing_embeddings = db.query(func.count()).select_from(PipelineEmbedding).filter(
                PipelineEmbedding.pipeline_id == pipeline_id_uuid,
                func.json_extract_path_text(PipelineEmbedding.metadata_info, 'document_id') == str(document_id_uuid)
            ).scalar()
            
            logger.info(f"Encontrados {existing_embeddings} embeddings para el documento {document_id} en el pipeline {pipeline_id}")
            
            # Si es un reintento o no hay embeddings, eliminar los existentes para regenerarlos
            if existing_embeddings > 0:
                # Verificar si es un reintento (si el pipeline está en estado FAILED o PENDING)
                from database.models.analysis import PipelineStatus, RfpAnalysisPipeline
                pipeline = db.query(RfpAnalysisPipeline).filter(RfpAnalysisPipeline.id == pipeline_id_uuid).first()
                
                is_retry = pipeline and pipeline.status in [PipelineStatus.FAILED, PipelineStatus.PENDING]
                
                if is_retry:
                    logger.info(f"Reintento detectado para pipeline {pipeline_id}. Eliminando embeddings existentes.")
                    
                    # Eliminar embeddings existentes para este documento en este pipeline
                    db.query(PipelineEmbedding).filter(
                        PipelineEmbedding.pipeline_id == pipeline_id_uuid,
                        func.json_extract_path_text(PipelineEmbedding.metadata_info, 'document_id') == str(document_id_uuid)
                    ).delete(synchronize_session=False)
                    db.commit()
            
            # CASO 3: Generar embeddings normalmente (no hay embeddings o se eliminaron)
            # Usar el user_id del solicitante si está disponible, de lo contrario usar el del documento
            user_id_to_use = requester_user_id or (str(document.user_id) if document.user_id else None)
            logger.info(f"Generando embeddings para documento {document_id} usando user_id: {user_id_to_use}")
            
            # Usar el método síncrono en lugar de asyncio.run para evitar conflictos con el bucle de eventos
            embeddings_result = embedding_processor.generate_embeddings_sync(
                text_content=text_content,
                chunk_size=2000,
                overlap=200,
                user_id=user_id_to_use
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
        logger.error(f"Error al procesar documento {document_id}: {e}")
        
        # Actualizar estado del documento si es posible
        try:
            with get_sync_session_context() as db:
                document = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
                if document:
                    document.processing_status = ProcessingStatus.ERROR
                    document.processing_error = str(e)
                    db.commit()
                    
                # Marcar el pipeline como fallido si hay error en procesamiento de documento
                from database.models.analysis import PipelineStatus
                if pipeline_id:
                    try:
                        pipeline = db.query(RfpAnalysisPipeline).filter(
                            RfpAnalysisPipeline.id == uuid.UUID(pipeline_id)
                        ).first()
                        
                        if pipeline:
                            pipeline.status = PipelineStatus.FAILED
                            db.commit()
                            logger.info(f"Pipeline {pipeline_id} marcado como FAILED debido a error en documento {document_id}")
                    except Exception as pipeline_error:
                        logger.error(f"Error al actualizar estado del pipeline {pipeline_id}: {pipeline_error}")
        except Exception as db_error:
            logger.error(f"Error al actualizar estado del documento {document_id}: {db_error}")
        
        # Publicar evento de error
        try:
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "document_processing_error",
                {
                    "document_id": document_id,
                    "pipeline_id": pipeline_id,
                    "error": str(e)
                }
            )
        except Exception as event_error:
            logger.error(f"Error al publicar evento de error: {event_error}")
            
        # Devolver error
        return {
            "status": "error",
            "document_id": document_id,
            "pipeline_id": pipeline_id,
            "error": str(e)
        }