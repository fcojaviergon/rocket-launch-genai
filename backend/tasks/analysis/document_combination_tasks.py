"""
Tareas Celery para la combinación de resultados de documentos
"""
import uuid
import json
from typing import Dict, Any, List
from datetime import datetime

from database.session import get_sync_session_context
from database.models.analysis import AnalysisPipeline
from core.events import get_event_manager
import logging

from tasks.worker import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="combine_document_results")
def combine_document_results(pipeline_id: str) -> Dict[str, Any]:
    """
    Combinar los resultados de procesamiento de múltiples documentos
    
    Args:
        pipeline_id: ID del pipeline
        
    Returns:
        Dict[str, Any]: Resultados combinados
    """
    # Convertir a UUID
    pipeline_id_uuid = uuid.UUID(pipeline_id)
    
    try:
        # Usar context manager para sesiones síncronas en Celery
        with get_sync_session_context() as db:
            # Publicar evento de inicio de combinación
            event_manager = get_event_manager()
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "document_combination_started",
                {"pipeline_id": pipeline_id}
            )
            
            # Obtener pipeline
            pipeline = db.query(AnalysisPipeline).filter(AnalysisPipeline.id == pipeline_id_uuid).first()
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} no encontrado")
                
            # Obtener documentos asociados al pipeline
            from database.models.analysis_document import PipelineDocument
            pipeline_documents = db.query(PipelineDocument).filter(
                PipelineDocument.pipeline_id == pipeline_id_uuid
            ).order_by(PipelineDocument.processing_order).all()
            
            if not pipeline_documents:
                logger.warning(f"No hay documentos asociados al pipeline {pipeline_id}")
                return {
                    "status": "warning",
                    "pipeline_id": pipeline_id,
                    "message": "No hay documentos para combinar",
                    "combined_text_content": ""
                }
                
            # Obtener embeddings de los documentos
            from database.models.analysis import PipelineEmbedding
            embeddings = db.query(PipelineEmbedding).filter(
                PipelineEmbedding.pipeline_id == pipeline_id_uuid
            ).order_by(PipelineEmbedding.chunk_index).all()
            
            # Combinar texto de los chunks
            combined_text = ""
            for embedding in embeddings:
                combined_text += embedding.chunk_text + "\n\n"
                
            # Actualizar pipeline con el texto combinado
            pipeline.combined_text_content = combined_text
            
            # Guardar cambios
            db.commit()
            
            # Publicar evento de finalización
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "document_combination_completed",
                {
                    "pipeline_id": pipeline_id,
                    "document_count": len(pipeline_documents),
                    "embedding_count": len(embeddings),
                    "text_length": len(combined_text)
                }
            )
            
            return {
                "status": "success",
                "pipeline_id": pipeline_id,
                "document_count": len(pipeline_documents),
                "embedding_count": len(embeddings),
                "combined_text_content": combined_text,
                "documents_combined": True
            }
    except Exception as e:
        logger.error(f"Error en combine_document_results: {e}", exc_info=True)
        
        # Publicar evento de error
        try:
            event_manager = get_event_manager()
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "document_combination_error",
                {
                    "pipeline_id": pipeline_id,
                    "error": str(e)
                }
            )
        except Exception as event_error:
            logger.error(f"Error al publicar evento de error: {event_error}")
        
        return {
            "status": "error",
            "error": str(e),
            "pipeline_id": pipeline_id
        }

async def _combine_document_results_async(results: List[Dict[str, Any]], pipeline_id: str) -> Dict[str, Any]:
    """
    Combinar los resultados de procesamiento de múltiples documentos
    
    Args:
        results: Lista de resultados de procesamiento de documentos
        pipeline_id: ID del pipeline
        
    Returns:
        Dict[str, Any]: Resultados combinados
    """
    pipeline_id = uuid.UUID(pipeline_id)
    event_manager = get_event_manager()
    
    try:
        # Combinar texto y embeddings
        all_text_content = []
        all_embeddings = []
        embedding_model = "default"
        
        for result in results:
            # Verificar si el resultado es un diccionario o una cadena
            if isinstance(result, dict):
                if "text_content" in result:
                    all_text_content.append(result["text_content"])
                
                if "embeddings" in result:
                    all_embeddings.extend(result["embeddings"])
                
                # Usar el modelo de embeddings del primer resultado que lo tenga
                if "embedding_model" in result and embedding_model == "default":
                    embedding_model = result["embedding_model"]
            elif isinstance(result, str):
                # Intentar deserializar el resultado si es una cadena JSON
                try:
                    result_dict = json.loads(result)
                    if isinstance(result_dict, dict):
                        if "text_content" in result_dict:
                            all_text_content.append(result_dict["text_content"])
                        
                        if "embeddings" in result_dict:
                            all_embeddings.extend(result_dict["embeddings"])
                        
                        if "embedding_model" in result_dict and embedding_model == "default":
                            embedding_model = result_dict["embedding_model"]
                except json.JSONDecodeError:
                    # Si no es JSON, podría ser directamente contenido de texto
                    all_text_content.append(result)
        
        # Combinar todo el texto extraído
        combined_text_content = "\n\n".join(all_text_content) if all_text_content else ""
        
        # Verificar si hay contenido real
        if not combined_text_content.strip():
            logger.warning(f"No se encontró contenido de texto para combinar en pipeline {pipeline_id}")
        
        # Ya no guardamos embeddings aquí, se guardan al procesar cada documento individual
        # Esto evita la duplicación y reduce la carga de memoria
        embeddings_count = len(all_embeddings)
        logger.info(f"Usando {embeddings_count} embeddings para el pipeline {pipeline_id}")
        
        # Publicar evento de combinación completada de forma asíncrona
        await event_manager.publish_realtime_async(
            f"pipeline:{pipeline_id}",
            "documents_combined",
            {
                "text_length": len(combined_text_content),
                "embeddings_count": len(all_embeddings)
            }
        )
        
        # Registrar información clara en los logs
        logger.info(f"Documentos combinados exitosamente para pipeline {pipeline_id}. "
                   f"Texto: {len(combined_text_content)} caracteres, "
                   f"Embeddings: {len(all_embeddings)}, "
                   f"Modelo: {embedding_model}")
        
        return {
            "combined_text_content": combined_text_content,
            "embeddings": all_embeddings,
            "embedding_model": embedding_model,
            "documents_combined": True,
            "text_length": len(combined_text_content),
            "embeddings_count": len(all_embeddings)
        }
    except Exception as e:
        logger.error(f"Error al combinar resultados para pipeline {pipeline_id}: {e}")
        
        # Publicar evento de error de forma asíncrona
        await event_manager.publish_realtime_async(
            f"pipeline:{pipeline_id}",
            "documents_combination_error",
            {
                "error": str(e)
            }
        )
        
        # Re-lanzar excepción para que Celery la maneje
        raise
