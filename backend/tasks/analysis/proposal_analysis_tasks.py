"""
Tareas Celery para el análisis de propuestas
"""
import uuid
from typing import Dict, Any
from datetime import datetime
from sqlalchemy import func, desc, asc

from database.session import get_sync_session_context
from database.models.task import TaskStatus, Task
from database.models.document import Document
from database.models.analysis import ProposalAnalysisPipeline, RfpAnalysisPipeline
from database.models.analysis_document import PipelineDocument
from utils.serialization import serialize_for_json
from core.events import get_event_manager
import logging

from tasks.worker import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="analyze_proposal_content")
def analyze_proposal_content(previous_result=None, pipeline_id: str = None, rfp_pipeline_id: str = None, user_id: str = None, task_id: str = None) -> Dict[str, Any]:
    """
    Analizar el contenido combinado de la propuesta contra los criterios del RFP
    
    Args:
        previous_result: Resultado previo (debe contener combined_text_content)
        pipeline_id: ID del pipeline de propuesta
        rfp_pipeline_id: ID del pipeline de RFP referenciado
        user_id: ID del usuario
        task_id: ID de la tarea
        
    Returns:
        Dict[str, Any]: Resultados del análisis
    """
    pipeline_id_uuid = uuid.UUID(pipeline_id)
    rfp_pipeline_id_uuid = uuid.UUID(rfp_pipeline_id)
    user_id_uuid = uuid.UUID(user_id)
    task_id_uuid = uuid.UUID(task_id)
    
    # Obtener el gestor de eventos
    event_manager = get_event_manager()
    
        # Manejar el caso cuando se recibe el resultado anterior como primer argumento
    if pipeline_id is None and isinstance(previous_result, str):
        # Si el primer argumento es un string y no se proporcionó pipeline_id, asumimos que es el pipeline_id
        pipeline_id = previous_result
        previous_result = None
    elif isinstance(previous_result, dict) and pipeline_id is None:
        # Si el primer argumento es un diccionario (resultado de combine_document_results)
        # y no se proporcionó pipeline_id, intentamos extraerlo del resultado
        pipeline_id = previous_result.get("pipeline_id")
        
    # Verificar que tenemos todos los argumentos necesarios
    if not pipeline_id or not user_id:
        error_msg = f"Faltan argumentos requeridos: pipeline_id={pipeline_id}, user_id={user_id}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    try:
        # Usar context manager para sesiones síncronas en Celery
        with get_sync_session_context() as db:
            # Actualizar estado de la tarea a "running"
            task = db.query(Task).filter(Task.id == task_id_uuid).first()
            if task:
                task.status = TaskStatus.RUNNING
                if not task.started_at:
                    task.started_at = datetime.utcnow()
                db.commit()
            
            # Obtener pipeline de propuesta
            pipeline = db.query(ProposalAnalysisPipeline).filter(ProposalAnalysisPipeline.id == pipeline_id_uuid).first()
            if not pipeline:
                raise ValueError(f"Pipeline de propuesta {pipeline_id} no encontrado")
            
            # Obtener pipeline de RFP
            rfp_pipeline = db.query(RfpAnalysisPipeline).filter(RfpAnalysisPipeline.id == rfp_pipeline_id_uuid).first()
            if not rfp_pipeline:
                raise ValueError(f"Pipeline de RFP {rfp_pipeline_id} no encontrado")
            
            # Publicar evento de inicio de análisis
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "proposal_analysis_started",
                {
                    "pipeline_id": pipeline_id,
                    "rfp_pipeline_id": rfp_pipeline_id
                }
            )
            
            # Obtener documentos asociados para información
            pipeline_documents = db.query(PipelineDocument).filter(
                PipelineDocument.pipeline_id == pipeline_id_uuid
            ).all()
            
            associated_documents = []
            for pd in pipeline_documents:
                doc = db.query(Document).filter(Document.id == pd.document_id).first()
                if doc:
                    associated_documents.append(doc)
            
            # Si no hay documentos, lanzar error
            if not associated_documents:
                raise ValueError(f"No se encontraron documentos asociados al pipeline {pipeline_id}")

            # Obtener texto combinado del resultado anterior o de los embeddings almacenados
            combined_text = ""
            
            if isinstance(previous_result, dict) and "combined_text_content" in previous_result:
                combined_text = previous_result.get("combined_text_content", "")
                logger.info(f"Usando texto combinado del resultado anterior: {len(combined_text)} caracteres")
            
            # Verificar que hay texto combinado
            if not combined_text:
                logger.error("No se pudo obtener texto combinado para analizar")
                return {
                    "success": False,
                    "pipeline_id": pipeline_id,
                    "error": "No se pudo obtener texto combinado para analizar"
                }
                
            # Obtener texto combinado de la propuesta
            proposal_text = combined_text
            
            if not proposal_text:
                raise ValueError("No hay contenido de texto combinado para analizar")
            
            # Inicializar procesadores
            from modules.analysis.processors.proposal_processor import ProposalProcessor
            from modules.document.service import DocumentService
            from core.dependencies import get_llm_client_instance
            
            # Obtener cliente LLM
            llm_client = get_llm_client_instance()
            document_service = DocumentService(llm_client=llm_client)
            proposal_processor = ProposalProcessor(llm_client=llm_client, document_service=document_service)
            
            # Ejecutar el análisis de la propuesta
            logger.info(f"Analizando propuesta contra criterios del RFP {rfp_pipeline_id}")
            
            # Llamar directamente al método síncrono
            analysis_results = proposal_processor.analyze_proposal_content(
                proposal_text=proposal_text,
                extracted_criteria=rfp_pipeline.extracted_criteria,
                evaluation_framework=rfp_pipeline.evaluation_framework,
                pipeline_id=pipeline_id_uuid,
                db=db,  # Usamos la sesión síncrona directamente
                user_id=str(user_id_uuid)
            )
            
            # Actualizar pipeline con resultados
            pipeline.evaluation_results = analysis_results.get("criteria_evaluations")
            pipeline.technical_evaluation = analysis_results.get("technical_evaluation")
            pipeline.grammar_evaluation = analysis_results.get("grammar_evaluation")
            pipeline.final_report = analysis_results.get("final_report")
            pipeline.analysis_status = "COMPLETED"
            pipeline.analyzed_at = datetime.utcnow()
            
            # Guardar resultados en la base de datos
            db.commit()
            
            # Publicar evento de finalización
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "proposal_analysis_completed",
                {
                    "pipeline_id": pipeline_id,
                    "rfp_pipeline_id": rfp_pipeline_id,
                    "success": True,
                    "results": serialize_for_json(analysis_results)
                }
            )
            
            # Actualizar tarea como completada
            if task:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                task.result = serialize_for_json(analysis_results)
                db.commit()
            
            return analysis_results
            
    except Exception as e:
        logger.error(f"Error en analyze_proposal_content: {e}")
        
        # Actualizar tarea como fallida
        try:
            with get_sync_session_context() as db:
                task = db.query(Task).filter(Task.id == task_id_uuid).first()
                if task:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    task.completed_at = datetime.utcnow()
                    task.result = serialize_for_json({
                        "success": False,
                        "pipeline_id": pipeline_id,
                        "rfp_pipeline_id": rfp_pipeline_id,
                        "error": str(e)
                    })
                    db.commit()
        except Exception as db_error:
            logger.error(f"Error al actualizar tarea fallida: {db_error}")
        
        # Publicar evento de error
        try:
            event_manager.publish_realtime(
                f"pipeline:{pipeline_id}",
                "proposal_analysis_error",
                {
                    "pipeline_id": pipeline_id,
                    "rfp_pipeline_id": rfp_pipeline_id,
                    "error": str(e)
                }
            )
        except Exception as event_error:
            logger.error(f"Error al publicar evento de error: {event_error}")
        
        # Devolver error en lugar de relanzar excepción
        return {
            "success": False,
            "error": str(e),
            "pipeline_id": pipeline_id,
            "rfp_pipeline_id": rfp_pipeline_id
        }
