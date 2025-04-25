"""
Tareas Celery para orquestar el flujo completo de análisis de RFP
"""
import uuid
from typing import Dict, Any, List
from celery import shared_task, chain, group
from datetime import datetime

from database.session import get_sync_session_context, get_celery_db_session
from database.models.document import Document, ProcessingStatus
from database.models.analysis import RfpAnalysisPipeline
from database.models.analysis_document import PipelineDocument

from utils.serialization import serialize_for_json
from core.events import get_event_manager
from tasks.base_tasks import update_task_status_sync
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

@shared_task(name="process_rfp_documents")
def process_rfp_documents(document_ids: list, pipeline_id: str, user_id: str, task_id: str, is_retry: bool = False) -> Dict[str, Any]:
    """
    Procesar documentos RFP de forma asíncrona
    
    Esta tarea orquesta el flujo completo de procesamiento:
    1. Procesar cada documento en paralelo
    2. Combinar los resultados
    3. Analizar el contenido combinado
    
    Args:
        document_ids: Lista de IDs de documentos
        pipeline_id: ID del pipeline
        user_id: ID del usuario
        task_id: ID de la tarea
        is_retry: Indica si es un reintento de análisis
        
    Returns:
        Dict[str, Any]: Resultados del procesamiento
    """
    # Publicar evento de inicio
    event_manager = get_event_manager()
    event_manager.publish_realtime(
        f"pipeline:{pipeline_id}",
        "processing_started",
        {
            "pipeline_id": pipeline_id,
            "document_count": len(document_ids),
            "is_retry": is_retry
        }
    )
    
    # Si es un reintento, limpiar el pipeline para empezar de nuevo
    if is_retry:
        with get_sync_session_context() as db:
            try:
                # Convertir pipeline_id a UUID
                pipeline_id_uuid = uuid.UUID(pipeline_id)
                
                # 1. Limpiar embeddings existentes
                from database.models.analysis import PipelineEmbedding
                db.query(PipelineEmbedding).filter(
                    PipelineEmbedding.pipeline_id == pipeline_id_uuid
                ).delete(synchronize_session=False)
                
                # 2. Resetear el estado del pipeline
                from database.models.analysis import PipelineStatus
                pipeline = db.query(RfpAnalysisPipeline).filter(
                    RfpAnalysisPipeline.id == pipeline_id_uuid
                ).first()
                
                if pipeline:
                    # Limpiar resultados anteriores
                    pipeline.extracted_criteria = None
                    pipeline.evaluation_framework = None
                    pipeline.results = None
                    pipeline.status = PipelineStatus.PROCESSING
                    db.commit()
                    
                    logger.info(f"Pipeline {pipeline_id} limpiado para reintento")
                else:
                    logger.error(f"No se encontró el pipeline {pipeline_id} para reintento")
                    
            except Exception as e:
                logger.error(f"Error al limpiar pipeline para reintento: {e}")
                db.rollback()
    
    # Importar las tareas necesarias usando Celery app
    from tasks.worker import celery_app
    
    # Verificar qué documentos necesitan procesamiento
    with get_sync_session_context() as db:
        # Actualizar la relación entre documentos y pipeline
        from database.models.analysis_document import PipelineDocument
        
        # Asegurar que todos los documentos estén asociados al pipeline
        for doc_id in document_ids:
            try:
                doc_uuid = uuid.UUID(doc_id)
                pipeline_uuid = uuid.UUID(pipeline_id)
                
                # Verificar si ya existe la relación
                existing = db.query(PipelineDocument).filter(
                    PipelineDocument.pipeline_id == pipeline_uuid,
                    PipelineDocument.document_id == doc_uuid
                ).first()
                
                if not existing:
                    # Crear relación si no existe
                    pipeline_doc = PipelineDocument(
                        pipeline_id=pipeline_uuid,
                        document_id=doc_uuid,
                        processing_order=0  # Orden por defecto
                    )
                    db.add(pipeline_doc)
                    db.commit()
                    logger.info(f"Asociado documento {doc_id} al pipeline {pipeline_id}")
            except Exception as e:
                logger.error(f"Error al asociar documento {doc_id} al pipeline {pipeline_id}: {e}")
    
    # Crear grupo para procesamiento paralelo de documentos
    # Pasar el user_id del solicitante a cada tarea de procesamiento de documentos
    document_tasks = group(
        celery_app.signature('process_document_content', args=[doc_id, pipeline_id, user_id])
        for doc_id in document_ids
    )
    
    # Crear cadena de tareas: procesar documentos -> combinar resultados -> analizar
    workflow = chain(
        document_tasks,
        celery_app.signature('combine_document_results', args=[pipeline_id]),
        celery_app.signature('analyze_rfp_content', args=[pipeline_id, user_id, task_id])
    )
    
    # Ejecutar flujo de trabajo
    result = workflow()
    
    # Actualizar explícitamente el estado de la tarea principal
    # Convertir el resultado a un diccionario simple para evitar problemas de serialización
    if result is not None:
        # Crear un diccionario simple con los datos esenciales
        text_content = result.get("combined_text_content", "") if isinstance(result, dict) else ""
        embedding_model = result.get("embedding_model", "") if isinstance(result, dict) else ""
        embeddings_count = len(result.get("embeddings", [])) if isinstance(result, dict) else 0
        
        # Registrar información útil en los logs
        logger.info(f"Procesamiento completado para pipeline {pipeline_id}: "
                   f"{embeddings_count} embeddings generados, "
                   f"longitud del texto: {len(text_content)} caracteres")
        
        simple_result = {
            "combined_text_content": text_content,
            "embeddings": [],  # No incluir embeddings en el resultado para evitar datos muy grandes
            "embedding_model": embedding_model,
            "embeddings_count": embeddings_count,
            "text_length": len(text_content),
            "success": True,
            "subtasks_completed": True
        }
        
        # Actualizar el estado de la tarea principal
        update_task_status_sync(
            task_id=task_id,
            status="COMPLETED",
            result={
                "pipeline_id": pipeline_id,
                "document_count": len(document_ids),
                "text_length": len(text_content),
                "embeddings_count": embeddings_count,
                "success": True,
                "workflow_completed": True
            }
        )
        
        return simple_result
    else:
        logger.warning(f"No se obtuvo resultado del workflow para pipeline {pipeline_id}")
        
        # Actualizar el estado de la tarea principal como fallida
        update_task_status_sync(
            task_id=task_id,
            status="FAILED",
            error_message="No se obtuvo resultado del workflow",
            result={"success": False, "pipeline_id": pipeline_id}
        )
        
        return {"success": False, "error": "No se obtuvo resultado del workflow"}
