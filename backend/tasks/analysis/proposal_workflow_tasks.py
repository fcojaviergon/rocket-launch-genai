"""
Tareas Celery para orquestar el flujo completo de análisis de propuestas
"""
import uuid
from typing import Dict, Any
from celery import shared_task, chain, group
from datetime import datetime

from database.session import get_sync_session_context
from database.models.document import Document, ProcessingStatus
from core.events import get_event_manager
from tasks.base_tasks import update_task_status_sync
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

@shared_task(name="process_proposal_documents")
def process_proposal_documents(document_ids: list, pipeline_id: str, rfp_pipeline_id: str, user_id: str, is_retry: bool = False, task_id: str = None) -> Dict[str, Any]:
    """
    Procesar documentos de propuesta de forma asíncrona
    
    Esta tarea orquesta el flujo completo de procesamiento:
    1. Procesar cada documento en paralelo
    2. Combinar los resultados
    3. Analizar el contenido combinado contra los criterios del RFP
    
    Args:
        document_ids: Lista de IDs de documentos
        pipeline_id: ID del pipeline de propuesta
        rfp_pipeline_id: ID del pipeline de RFP referenciado
        user_id: ID del usuario
        is_retry: Indica si es un reintento de análisis
        task_id: ID de la tarea
        
    Returns:
        Dict[str, Any]: Resultados del procesamiento
    """
    # Publicar evento de inicio
    event_manager = get_event_manager()
    event_manager.publish_realtime(
        f"pipeline:{pipeline_id}",
        "proposal_processing_started",
        {
            "pipeline_id": pipeline_id,
            "rfp_pipeline_id": rfp_pipeline_id,
            "document_count": len(document_ids),
            "is_retry": is_retry
        }
    )
    
    # Si es un reintento, limpiar el pipeline para empezar de nuevo
    if is_retry:
        with get_sync_session_context() as db:
            
            # Convertir pipeline_id a UUID
            pipeline_id_uuid = uuid.UUID(pipeline_id)
            
            # 1. Limpiar embeddings existentes
            from database.models.analysis import PipelineEmbedding
            db.query(PipelineEmbedding).filter(
                PipelineEmbedding.pipeline_id == pipeline_id_uuid
            ).delete(synchronize_session=False)
            
            # 2. Resetear el estado del pipeline
            from database.models.analysis import ProposalAnalysisPipeline
            pipeline = db.query(ProposalAnalysisPipeline).filter(
                ProposalAnalysisPipeline.id == pipeline_id_uuid
            ).first()
            
            from database.models.analysis import PipelineStatus
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
     
     
    # Importar las tareas necesarias usando Celery app
    from tasks.worker import celery_app
    
    # Crear grupo de tareas para procesar documentos en paralelo
    document_tasks = group(
        celery_app.signature('process_document_content', args=[doc_id, pipeline_id])
        for doc_id in document_ids
    )
    
    # Crear cadena de tareas: procesar documentos -> combinar resultados -> analizar
    workflow = chain(
        document_tasks,
        celery_app.signature('combine_document_results', args=[pipeline_id]),
        celery_app.signature('analyze_proposal_content', args=[pipeline_id, rfp_pipeline_id, user_id, task_id])
    )
    
    # Ejecutar flujo de trabajo
    result = workflow()
    
    # Convertir el resultado a un diccionario simple para evitar problemas de serialización
    if result is not None:
        # Crear un diccionario simple con los datos esenciales
        text_content = result.get("combined_text_content", "") if isinstance(result, dict) else ""
        overall_score = result.get("overall_score", 0) if isinstance(result, dict) else 0
        
        # Registrar información útil en los logs
        logger.info(f"Procesamiento de propuesta completado para pipeline {pipeline_id}: "
                   f"Longitud del texto: {len(text_content) if text_content else 0} caracteres, "
                   f"Puntuación general: {overall_score}")
        
        simple_result = {
            "success": True,
            "pipeline_id": pipeline_id,
            "rfp_pipeline_id": rfp_pipeline_id,
            "text_length": len(text_content) if text_content else 0,
            "overall_score": overall_score,
            "subtasks_completed": True
        }
        
        # Actualizar el estado de la tarea principal
        update_task_status_sync(
            task_id=task_id,
            status="COMPLETED",
            result={
                "pipeline_id": pipeline_id,
                "rfp_pipeline_id": rfp_pipeline_id,
                "document_count": len(document_ids),
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
            result={
                "success": False, 
                "pipeline_id": pipeline_id,
                "rfp_pipeline_id": rfp_pipeline_id
            }
        )
        
        return {
            "success": False, 
            "error": "No se obtuvo resultado del workflow",
            "pipeline_id": pipeline_id,
            "rfp_pipeline_id": rfp_pipeline_id
        }
