"""
Celery tasks for proposal document analysis
"""
import uuid
from typing import Dict, Any
from celery import shared_task
from datetime import datetime

from database.session import get_sync_db
from modules.pipelines.proposal.processor import ProposalPipeline
from database.models.task import TaskStatus, Task
from database.models.document import Document
from database.models.analysis import ProposalAnalysisPipeline, RfpAnalysisPipeline
from utils.serialization import serialize_for_json
from core.openai_client import OpenAIClient
from core.config import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(name="process_proposal_document")
def process_proposal_document(document_id: str, pipeline_id: str, rfp_pipeline_id: str, user_id: str, task_id: str) -> Dict[str, Any]:
    # Usar la función de serialización del módulo de utilidades
    """
    Process a proposal document against an RFP
    
    Args:
        document_id: Document ID
        pipeline_id: Analysis pipeline ID
        rfp_pipeline_id: RFP pipeline ID
        user_id: User ID
        task_id: Task ID
        
    Returns:
        Dict[str, Any]: Analysis results
    """
    # Convert string IDs to UUIDs
    document_id = uuid.UUID(document_id)
    pipeline_id = uuid.UUID(pipeline_id)
    rfp_pipeline_id = uuid.UUID(rfp_pipeline_id)
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
        pipeline = db.query(ProposalAnalysisPipeline).filter(ProposalAnalysisPipeline.id == pipeline_id).first()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        
        # Get RFP pipeline
        rfp_pipeline = db.query(RfpAnalysisPipeline).filter(RfpAnalysisPipeline.id == rfp_pipeline_id).first()
        if not rfp_pipeline:
            raise ValueError(f"RFP pipeline {rfp_pipeline_id} not found")
        
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
        
        # 2. Luego procesar la propuesta usando el texto extraído y los embeddings generados
        from modules.pipelines.proposal.processor import ProposalPipeline
        
            
        proposal_processor = ProposalPipeline(llm_client=llm_client)
        
        # Ejecutar el procesamiento de la propuesta pasando el texto ya extraído y los embeddings
        results = proposal_processor.process_sync(
            pipeline_id=pipeline_id, 
            document=document,
            rfp_pipeline=rfp_pipeline,
            text_content=doc_results.get("text_content", ""),
            embeddings=doc_results.get("embeddings", []),
            db=db
        )
        
        # Update pipeline with results
        pipeline.evaluation_results = results.get("evaluation_results")
        pipeline.technical_evaluation = results.get("technical_evaluation")
        pipeline.grammar_evaluation = results.get("grammar_evaluation")
        pipeline.consistency_evaluation = results.get("consistency_evaluation")
        
        # Actualizar el estado del pipeline
        if pipeline.results is None:
            pipeline.results = {}
            
        pipeline.results.update({
            "proposal_processing": {
                "processed_at": results.get("processed_at"),
                "evaluation_completed": results.get("evaluation_results") is not None,
                "technical_score": results.get("technical_evaluation", {}).get("score", 0),
                "grammar_score": results.get("grammar_evaluation", {}).get("score", 0),
                "consistency_score": results.get("consistency_evaluation", {}).get("score", 0)
            }
        })
        
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
                "rfp_pipeline_id": str(rfp_pipeline_id),
                "results": serialized_results
            }
            db.commit()
        
        # Asegurarse de que todos los UUIDs se conviertan a strings para el retorno
        serialized_results = serialize_for_json(results)
        
        return {
            "success": True,
            "pipeline_id": str(pipeline_id),
            "document_id": str(document_id),
            "rfp_pipeline_id": str(rfp_pipeline_id),
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
