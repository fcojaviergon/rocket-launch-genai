"""
Celery tasks for RFP document analysis
"""
import uuid
from typing import Dict, Any
from celery import shared_task

from database.session import get_sync_db
from database.models.task import TaskStatus, Task
from database.models.document import Document
from database.models.analysis import RfpAnalysisPipeline
from utils.serialization import serialize_for_json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@shared_task(name="process_rfp_document")
def process_rfp_document(document_id: str, pipeline_id: str, user_id: str, task_id: str) -> Dict[str, Any]:
    # Usar la función de serialización del módulo de utilidades
    """
    Process an RFP document
    
    Args:
        document_id: Document ID
        pipeline_id: Analysis pipeline ID
        user_id: User ID
        task_id: Task ID
        
    Returns:
        Dict[str, Any]: Analysis results
    """
    # Convert string IDs to UUIDs
    document_id = uuid.UUID(document_id)
    pipeline_id = uuid.UUID(pipeline_id)
    user_id = uuid.UUID(user_id)
    task_id = uuid.UUID(task_id)
    
    # Get database session
    db = next(get_sync_db())
    
    try:
        # Update task status to running
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = TaskStatus.RUNNING
            if not task.started_at:
                task.started_at = datetime.utcnow()
            db.commit()
        
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get pipeline
        pipeline = db.query(RfpAnalysisPipeline).filter(RfpAnalysisPipeline.id == pipeline_id).first()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        
        # Inicializar el cliente LLM para el procesador de RFP
        try:
            # Usar la función singleton para obtener la instancia del cliente LLM
            from core.dependencies import get_llm_client_instance
            llm_client = get_llm_client_instance()
            if llm_client:
                logger.info(f"LLM client initialized successfully for RFP processing: {type(llm_client).__name__}")
            else:
                logger.error("LLM client is None. Check AI provider configuration.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            llm_client = None
            
        # 1. Primero procesar el documento para extraer texto y generar embeddings
        from modules.pipelines.document.processor import DocumentPipeline
        doc_processor = DocumentPipeline(llm_client=llm_client)
        
        # Procesar el documento y generar embeddings
        doc_results = doc_processor.process_sync(pipeline_id=pipeline_id, document=document)
        
        # Guardar resultados del procesamiento del documento y embeddings
        doc_processor.save_processing_results(db, pipeline_id, document_id, doc_results)
        
        # Guardar embeddings si se generaron
        if doc_results.get("embeddings"):
            doc_processor.save_embeddings(
                db=db, 
                pipeline_id=pipeline_id, 
                embeddings=doc_results.get("embeddings", []),
                embedding_model=doc_results.get("embedding_model", "default")
            )
        
        # 2. Luego procesar el RFP usando el texto extraído
        from modules.pipelines.rfp.processor import RfpPipeline
        
        rfp_processor = RfpPipeline(llm_client=llm_client)
        
        # Convertir el documento a un diccionario para la nueva interfaz
        document_dict = {
            "id": document.id,
            "title": document.title,
            "file_path": document.file_path,
            "filename": document.filename
        }
        logger.info(f"Document text content: {doc_results.get('text_content', '')}")
        # Ejecutar el procesamiento de RFP pasando el texto ya extraído
        results = rfp_processor.process_sync(
            pipeline_id=pipeline_id, 
            document=document_dict,
            text_content=doc_results.get("text_content", "")
        )
        
        # Update pipeline with results
        pipeline.extracted_criteria = results.get("extracted_criteria")
        pipeline.evaluation_framework = results.get("evaluation_framework")
        
        # Actualizar el estado del pipeline
        if pipeline.results is None:
            pipeline.results = {}
            
        pipeline.results.update({
            "rfp_processing": {
                "processed_at": results.get("processed_at"),
                "criteria_extracted": len(results.get("extracted_criteria", {}).get("criteria", [])) > 0,
                "framework_generated": len(results.get("evaluation_framework", {}).get("weighted_criteria", [])) > 0
            }
        })
        
        # Guardar el estado del pipeline
        pipeline.status = "completed"
        pipeline.completed_at = datetime.utcnow()
        
        db.commit()
        
        # Update task status to completed
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            # Asegurarse de que todos los UUIDs se conviertan a strings
            # Clonar y serializar los resultados para evitar problemas de JSON
            serialized_results = serialize_for_json(results)
            
            task.result = {
                "success": True,
                "pipeline_id": str(pipeline_id),
                "document_id": str(document_id),
                "results": serialized_results
            }
            db.commit()
        
        # Asegurarse de que todos los UUIDs se conviertan a strings para el retorno
        serialized_results = serialize_for_json(results)
        
        return {
            "success": True,
            "pipeline_id": str(pipeline_id),
            "document_id": str(document_id),
            "results": serialized_results
        }
    except Exception as e:
        # Update task status to failed
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.error_message = str(e)
            db.commit()
        
        # Re-raise exception
        raise
    finally:
        db.close()
