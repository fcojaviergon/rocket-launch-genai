"""
Utilidades compartidas para tareas de análisis
"""
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from database.session import get_sync_session_context, get_celery_db_session
from database.models.task import TaskStatus, Task
from database.models.document import Document
from database.models.analysis_document import PipelineDocument
from database.models.analysis import PipelineEmbedding
from core.events import get_event_manager
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

def update_task_status(
    task_id: str, 
    status: str, 
    result: Optional[Dict[str, Any]] = None, 
    error_message: Optional[str] = None
) -> None:
    """
    Actualizar el estado de una tarea en la base de datos
    
    Args:
        task_id: ID de la tarea
        status: Nuevo estado (PENDING, RUNNING, COMPLETED, FAILED)
        result: Resultados de la tarea (opcional)
        error_message: Mensaje de error (opcional)
    """
    task_id_uuid = uuid.UUID(task_id)
    
    # Usar context manager para sesión síncrona
    with get_sync_session_context() as db:
        try:
            # Obtener tarea
            task = db.query(Task).filter(Task.id == task_id_uuid).first()
            if not task:
                logger.error(f"Tarea {task_id} no encontrada")
                return
                
            # Actualizar estado
            task.status = TaskStatus(status)
            
            # Actualizar campos según el estado
            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.utcnow()
                
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.utcnow()
                
            # Actualizar resultado
            if result is not None:
                task.result = result
                
            # Actualizar mensaje de error
            if error_message is not None:
                task.error_message = error_message
                
            # Guardar cambios
            db.commit()
            
            # Publicar evento de actualización de tarea
            event_manager = get_event_manager()
            event_manager.publish_realtime(
                f"task:{task_id}",
                "task_updated",
                {
                    "task_id": task_id,
                    "status": status,
                    "has_error": error_message is not None
                }
            )
        except Exception as e:
            logger.error(f"Error al actualizar tarea {task_id}: {e}")
            db.rollback()
        
def get_pipeline_documents(pipeline_id: str, db=None) -> List[Document]:
    """
    Obtener documentos asociados a un pipeline
    
    Args:
        pipeline_id: ID del pipeline
        db: Sesión de base de datos (opcional)
        
    Returns:
        List[Document]: Lista de documentos
    """
    pipeline_id_uuid = uuid.UUID(pipeline_id)
    
    # Si no se proporciona una sesión, crear una nueva con context manager
    if db is None:
        with get_sync_session_context() as db:
            # Obtener documentos asociados
            pipeline_documents = db.query(PipelineDocument).filter(
                PipelineDocument.pipeline_id == pipeline_id_uuid
            ).order_by(PipelineDocument.processing_order).all()
            
            documents = []
            for pd in pipeline_documents:
                doc = db.query(Document).filter(Document.id == pd.document_id).first()
                if doc:
                    documents.append(doc)
                    
            return documents
    else:
        # Usar la sesión proporcionada
        pipeline_documents = db.query(PipelineDocument).filter(
            PipelineDocument.pipeline_id == pipeline_id_uuid
        ).order_by(PipelineDocument.processing_order).all()
        
        documents = []
        for pd in pipeline_documents:
            doc = db.query(Document).filter(Document.id == pd.document_id).first()
            if doc:
                documents.append(doc)
                
        return documents
            
def check_embeddings_exist(pipeline_id: str, document_id: str, db=None) -> bool:
    """
    Verificar si existen embeddings para un documento en un pipeline
    
    Args:
        pipeline_id: ID del pipeline
        document_id: ID del documento
        db: Sesión de base de datos (opcional)
        
    Returns:
        bool: True si existen embeddings, False en caso contrario
    """
    pipeline_id_uuid = uuid.UUID(pipeline_id)
    
    # Si no se proporciona una sesión, crear una nueva con context manager
    if db is None:
        with get_sync_session_context() as db:
            # Consultar embeddings existentes
            existing_embeddings = db.query(func.count()).select_from(PipelineEmbedding).filter(
                PipelineEmbedding.pipeline_id == pipeline_id_uuid,
                func.json_extract_path_text(PipelineEmbedding.metadata_info, 'document_id') == str(document_id)
            ).scalar()
            
            return existing_embeddings > 0
    else:
        # Usar la sesión proporcionada
        existing_embeddings = db.query(func.count()).select_from(PipelineEmbedding).filter(
            PipelineEmbedding.pipeline_id == pipeline_id_uuid,
            func.json_extract_path_text(PipelineEmbedding.metadata_info, 'document_id') == str(document_id)
        ).scalar()
        
        return existing_embeddings > 0
