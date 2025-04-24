"""
Tareas Celery para orquestar el flujo completo de análisis de propuestas
"""
import uuid
from typing import Dict, Any
from celery import shared_task, chain, group
from datetime import datetime

from database.session import get_sync_session_context
from database.models.document import Document, ProcessingStatus
from database.models.analysis import PipelineEmbedding
from core.events import get_event_manager
from tasks.base_tasks import update_task_status_sync
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

@shared_task(name="process_proposal_documents_async")
def process_proposal_documents_async(document_ids: list, pipeline_id: str, rfp_pipeline_id: str, user_id: str, task_id: str) -> Dict[str, Any]:
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
            "document_count": len(document_ids)
        }
    )
    
    # Verificar el estado de procesamiento de los documentos
    # Inicializar lista para documentos a procesar
    docs_to_process = []
    
    # Usar context manager para sesiones síncronas en Celery
    with get_sync_session_context() as db:
        for doc_id in document_ids:
            # Obtener el documento usando API síncrona
            document = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
            
            if not document:
                logger.warning(f"Documento {doc_id} no encontrado. Omitiendo.")
                continue
                
            # Verificar si el documento ya fue procesado
            if document.processing_status == ProcessingStatus.COMPLETED:
                logger.info(f"Documento {doc_id} ya fue procesado (status=COMPLETED). Omitiendo generación de embeddings.")
                continue
                    
            # Verificar si hay embeddings existentes como respaldo usando API síncrona
            existing_embeddings = db.query(func.count()).select_from(PipelineEmbedding).filter(
                PipelineEmbedding.pipeline_id == uuid.UUID(pipeline_id),
                func.json_extract_path_text(PipelineEmbedding.metadata_info, 'document_id') == str(doc_id)
            ).scalar()
                
            if existing_embeddings > 0:
                logger.info(f"Se encontraron {existing_embeddings} embeddings existentes para el documento {doc_id}. Omitiendo generación.")
            else:
                # Si no hay embeddings existentes y el documento no está marcado como COMPLETED, procesarlo
                logger.info(f"Documento {doc_id} requiere procesamiento. Estado actual: {document.processing_status}")
                docs_to_process.append(doc_id)
        
    # Si no hay documentos para procesar, usar los originales (para mantener la compatibilidad)
    if not docs_to_process:
        logger.info(f"Todos los documentos ya están procesados. Usando los existentes.")
        docs_to_process = document_ids
    
    # Importar las tareas necesarias usando Celery app
    from tasks.worker import celery_app
    
    # Crear grupo de tareas para procesar documentos en paralelo
    document_tasks = group(
        celery_app.signature('process_document_content', args=[doc_id, pipeline_id])
        for doc_id in docs_to_process
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
