"""
Tareas Celery para el análisis de RFP
"""
import uuid
from typing import Dict, Any
from datetime import datetime
import json

from database.session import get_sync_session_context
from database.models.task import TaskStatus, Task
from database.models.document import Document
from database.models.analysis import RfpAnalysisPipeline
from database.models.analysis_document import PipelineDocument
from utils.serialization import serialize_for_json
from core.events import get_event_manager
import logging

from tasks.worker import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="analyze_rfp_content")
def analyze_rfp_content(pipeline_id: str, user_id: str, task_id: str) -> Dict[str, Any]:
    """
    Analizar el contenido combinado de RFP para extraer criterios y generar framework de evaluación
    
    Args:
        pipeline_id: ID del pipeline
        user_id: ID del usuario
        task_id: ID de la tarea
        
    Returns:
        Dict[str, Any]: Resultados del análisis
    """
    pipeline_id_uuid = uuid.UUID(pipeline_id)
    user_id_uuid = uuid.UUID(user_id)
    task_id_uuid = uuid.UUID(task_id)
    
    # Función síncrona para actualizar el estado de la tarea en caso de error
    def update_task_error(e):
        try:
            # Obtener nueva sesión síncrona para actualizar estado
            with get_sync_session_context() as error_db:
                task = error_db.query(Task).filter(Task.id == task_id_uuid).first()
                if task:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.utcnow()
                    task.error_message = str(e)
                    task.result = {
                        "success": False,
                        "pipeline_id": pipeline_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    error_db.commit()
        except Exception as task_error:
            logger.error(f"Error al actualizar tarea con error: {task_error}")
    
    # Obtener gestor de eventos
    event_manager = get_event_manager()
    
    try:
        # Usar sesión síncrona para operaciones de base de datos
        with get_sync_session_context() as db:
            # Actualizar estado de la tarea a "running"
            task = db.query(Task).filter(Task.id == task_id_uuid).first()
            if task:
                task.status = TaskStatus.RUNNING
                if not task.started_at:
                    task.started_at = datetime.utcnow()
                db.commit()
            else:
                logger.error(f"Task with ID {task_id} not found")
                return {"error": f"Task with ID {task_id} not found"}
                
            # Obtener pipeline
            pipeline = db.query(RfpAnalysisPipeline).filter(RfpAnalysisPipeline.id == pipeline_id_uuid).first()
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} no encontrado")
                
            # Publicar evento de inicio de análisis
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "rfp_analysis_started",
                {"pipeline_id": pipeline_id}
            )
            
            # Obtener documentos asociados para información
            pipeline_documents = db.query(PipelineDocument)\
                .filter(PipelineDocument.pipeline_id == pipeline_id_uuid)\
                .order_by(PipelineDocument.processing_order)\
                .all()
            
            associated_documents = []
            for pd in pipeline_documents:
                doc = db.query(Document).filter(Document.id == pd.document_id).first()
                if doc:
                    associated_documents.append(doc)
    
            # Verificar que hay documentos asociados
            if not associated_documents:
                raise ValueError(f"No se encontraron documentos asociados al pipeline {pipeline_id}")
                
            # Inicializar procesador de RFP
            from modules.analysis.processors.rfp_processor import RfpProcessor
            from core.dependencies import get_llm_client_instance
            
            # Obtener el documento principal (primero en orden de procesamiento)
            primary_document = associated_documents[0] if associated_documents else None
            if not primary_document:
                raise ValueError("No se encontró un documento principal para el análisis")
                
            # Inicializar procesador con cliente LLM
            llm_client = get_llm_client_instance()
            rfp_processor = RfpProcessor(llm_client=llm_client)
            
            # Obtener texto combinado del pipeline
            combined_text = pipeline.combined_text_content
            
            # Verificar que hay texto combinado
            if not combined_text:
                raise ValueError("No hay contenido de texto combinado para analizar")
            
            # Ejecutar el análisis síncrono
            # Pasar el ID del usuario para seguimiento de tokens
            results = rfp_processor.analyze_rfp_content(
                combined_text=combined_text,
                user_id=str(user_id_uuid)
            )
            
            # Registrar información sobre el uso de tokens
            token_usage = results.get("token_usage", {})
            if token_usage:
                logger.info(f"Uso de tokens para análisis de RFP: {token_usage.get('input_tokens', 0)} tokens de entrada, "
                          f"truncado: {token_usage.get('truncated', False)}")
            
            # Actualizar pipeline con resultados
            pipeline.extracted_criteria = results.get("extracted_criteria")
            pipeline.evaluation_framework = results.get("evaluation_framework")
            pipeline.results = results
            
            # Actualizar el pipeline con los resultados
            pipeline.processing_metadata = pipeline.processing_metadata or {}
            pipeline.processing_metadata.update({
                "rfp_analysis": {
                    "completed_at": datetime.utcnow().isoformat(),
                    "criteria_count": len(results.get("criteria", [])),
                    "framework_generated": True
                }
            })
            
            # Guardar cambios en el pipeline
            db.commit()
            
            # Actualizar tarea a completada
            task = db.query(Task).filter(Task.id == task_id_uuid).first()
            if task:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow().isoformat()
                
                # Serializar resultados para evitar problemas de JSON
                serialized_results = serialize_for_json(results)
                
                task.result = {
                    "success": True,
                    "pipeline_id": pipeline_id,
                    "principal_document_id": str(primary_document.id),
                    "results": serialized_results,
                    "analysis_completed": True,
                    "criteria_count": len(results.get("extracted_criteria", {}).get("criteria", [])),
                    "framework_criteria_count": len(results.get("evaluation_framework", {}).get("evaluation_criteria", []))
                }
                db.commit()
        
            # Publicar evento de análisis completado
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "rfp_analysis_completed",
                {
                    "pipeline_id": pipeline_id,
                    "criteria_count": len(results.get("extracted_criteria", {}).get("criteria", [])),
                    "framework_generated": True
                }
            )
            
            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "results": results,
                "analysis_completed": True
            }
    except Exception as e:
        logger.error(f"Error en analyze_rfp_content: {e}")
        
        # Actualizar tarea como fallida
        update_task_error(e)
        
        # Publicar evento de error
        try:
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "rfp_analysis_error",
                {
                    "pipeline_id": pipeline_id,
                    "error": str(e)
                }
            )
        except Exception as event_error:
            logger.error(f"Error al publicar evento de error: {event_error}")

        # Devolver error en lugar de relanzar excepción
        return {
            "success": False,
            "error": str(e),
            "pipeline_id": pipeline_id
        }
