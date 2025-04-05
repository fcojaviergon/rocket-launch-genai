"""
Definición de tareas de Celery para procesamiento asíncrono
"""
import time
import logging
import asyncio
import json
import uuid
from .worker import celery_app
from .database import update_pipeline_execution_status
from database.models.pipeline import Pipeline
from database.models.document import Document
from modules.pipeline.executor import PipelineExecutor, create_processing_result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings
import os
import traceback

# Settings logging
logger = logging.getLogger('tasks.pipeline')

@celery_app.task(name="test_task")
def test_task(message="default"):
    """
    Task simple for Celery tests
    
    Args:
        message: Optional message to include in the response
    
    Returns:
        dict: Result of the task
    """
    logger.info(f"Executing test task with message: {message}")
    time.sleep(2)  # Simulate processing
    return {
        "message": f"Task completed: {message}",
        "status": "success"
    }

@celery_app.task(name="execute_pipeline")
def execute_pipeline(pipeline_id, document_id, execution_id=None):
    """
    Execute a processing pipeline for a document
    
    Args:
        pipeline_id (str): ID pipeline to execute
        document_id (str): ID of the document to process
        execution_id (str, optional): ID of the execution in the database
    
    Returns:
        dict: Result of the execution
    """
    logger.info(f"Starting pipeline execution {pipeline_id} for document {document_id}")
    
    
    # Update status to RUNNING if we have execution_id
    if execution_id:
        logger.info(f"Updating execution {execution_id} to RUNNING")
        update_pipeline_execution_status(execution_id, "RUNNING")
    
    # Start execution time
    start_time = time.time()
    
    try:
        # Execute the async logic using asyncio.run
        result = asyncio.run(_execute_pipeline_async(pipeline_id, document_id, execution_id))
        
        # Calculate total time
        elapsed = time.time() - start_time
        
        # Prepare final result - correct access to result fields
        final_result = {
            "status": result.get("status", "success"),
            "pipeline_id": pipeline_id,
            "document_id": document_id,
            "elapsed_time": elapsed,
            "message": result.get("message", ""),
            "results": result  # Save the complete result
        }
        
        # Update status in database if we have execution_id
        if execution_id:
            logger.info(f"Updating execution {execution_id} to COMPLETED")
            update_pipeline_execution_status(execution_id, "COMPLETED", results=final_result)
        
        logger.info(f"Pipeline completed successfully in {elapsed:.2f}s")
        return final_result
        
    except Exception as e:
        # Register error
        logger.error(f"Error in pipeline: {str(e)}")
        logger.error(traceback.format_exc())  # Add full stack trace
        
        # Prepare error result
        error_result = {
            "status": "error",
            "pipeline_id": pipeline_id,
            "document_id": document_id,
            "error": str(e)
        }
        
        # Update status in database if we have execution_id
        if execution_id:
            logger.info(f"Updating execution {execution_id} to FAILED")
            update_pipeline_execution_status(execution_id, "FAILED", error_message=str(e))
        
        return error_result

@celery_app.task(name="monitor_batch_process")
def monitor_batch_process(batch_id, execution_ids):
    """
    Monitors the progress of a batch process of documents
    
    Args:
        batch_id (str): ID of the batch process
        execution_ids (list): List of execution IDs to monitor
    
    Returns:
        dict: Status of the monitoring
    """
    logger.info(f"Monitoring batch process {batch_id} with {len(execution_ids)} executions")
    
    # In a real implementation, we would check the status of each execution
    # and update the status of the batch in the database
    
    return {
        "status": "success",
        "batch_id": batch_id,
        "total_executions": len(execution_ids),
        "completed": len(execution_ids),  # In a real implementation, we would count the completed ones
        "message": "Batch monitoring completed"
    }

async def _execute_pipeline_async(pipeline_id, document_id, execution_id=None):
    """
    Real implementation of the pipeline execution
    
    Args:
        pipeline_id (str): ID of the pipeline to execute
        document_id (str): ID of the document to process
        
    Returns:
        dict: Result of the pipeline
    """
    logger.info(f"Executing pipeline {pipeline_id} for document {document_id}")
    
    logger.info(f"ENV POSTGRES_HOST={os.environ.get('POSTGRES_HOST')}")
    logger.info(f"ENV REDIS_URL={os.environ.get('REDIS_URL')}")

    try:
        # Use the centralized method in config to get the correct async URL
        database_url = settings.get_async_database_url()
        logger.info(f"Using database URL (sanitized): {database_url.replace(settings.POSTGRES_PASSWORD, '***')}")
    except Exception as e:
        logger.error(f"Error getting database URL: {e}")
        # In case of error, manually construct a secure URL
        database_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB.strip('/')}"
        logger.info("Using fallback database URL")
    
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Load pipeline and document
        pipeline = await session.get(Pipeline, uuid.UUID(pipeline_id))
        document = await session.get(Document, uuid.UUID(document_id))
            
        if not pipeline or not document:
            raise ValueError(f"Pipeline or document not found: {pipeline_id}, {document_id}")


        logger.info(f"Executing pipeline '{pipeline.name}' (ID: {pipeline.id}) for document '{document.title}' (ID: {document.id})")    
        # Use the existing executor
   
        # Get document file path and detect type
        file_path = document.file_path
        if not file_path or not os.path.exists(file_path):
            logger.error(f"Document file not found at path: {file_path}")
            update_pipeline_execution_status(execution_id, "FAILED", error_message="Document file not found")
       
            return {"status": "error", "result": "Document file not found"}

        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    document_content = f.read()
            elif file_ext in ['.doc', '.docx']:
                import docx
                doc = docx.Document(file_path)
                document_content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                logger.debug(f"Extracted DOCX content snippet (first 100 chars): {document_content[:100]}")
            elif file_ext == '.pdf':
                import pypdf
                with open(file_path, 'rb') as f:
                    reader = pypdf.PdfReader(f)
                    document_content = '\n'.join([page.extract_text() for page in reader.pages])
                logger.debug(f"Extracted PDF content snippet (first 100 chars): {document_content[:100]}")
            else:
                logger.error(f"Unsupported file type: {file_ext}")
                update_pipeline_execution_status(execution_id, "FAILED", error_message=f"Unsupported file type: {file_ext}")
                return {"status": "error", "result": f"Unsupported file type: {file_ext}"}
            
            document.content = document_content
   
        except Exception as e:
            logger.error(f"Error reading document file: {str(e)}")
            update_pipeline_execution_status(execution_id, "FAILED", error_message=f"Error reading document: {str(e)}")
            return {"status": "error", "result": f"Error reading document: {str(e)}"}

        if not document.content:
            document.content = "Content not available"
   
   
        executor = PipelineExecutor()
        results = await executor.execute(uuid.UUID(execution_id), pipeline, document)

        # 3. Update execution with results and status COMPLETED
        if results:

            # Create processing result record
            try:
                # Use the proper function from executor.py to create processing result
                await create_processing_result(
                    session,
                    document.id, 
                    pipeline.name, 
                    results
                )
                logger.info(f"Processing results saved for document {document.id}")
            except Exception as e:
                logger.exception(f"Error saving processing results: {str(e)}")
            logger.info(f"Pipeline completed successfully: {execution_id}")
            
            update_pipeline_execution_status(execution_id, "COMPLETED", results=results)
            return {
                "status": "success", 
                "execution_id": execution_id,
                "pipeline_id": str(pipeline.id),
                "document_id": str(document.id),
                "message": f"Processed pipeline {pipeline_id} for document {document_id}",
                "timestamp": time.time(),
            }
        
            
        else:
            update_pipeline_execution_status(execution_id, "FAILED", error_message="No results from pipeline")
            return {"status": "error", "result": "No results from pipeline"}



logger.info("Celery tasks module loaded (using direct SQLAlchemy).")

  
