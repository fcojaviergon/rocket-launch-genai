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
from backend.database.models.document import ProcessingStatus

# Settings logging
logger = logging.getLogger('tasks.pipeline')
# Configure specific logger for embedding task
embedding_logger = logging.getLogger('tasks.embeddings')

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
            error_msg = f"Pipeline {pipeline_id} or document {document_id} not found"
            logger.error(error_msg)
            # Update execution status if possible
            if execution_id:
                 update_pipeline_execution_status(execution_id, "FAILED", error_message=error_msg)
            raise ValueError(error_msg)

        logger.info(f"Executing pipeline '{pipeline.name}' (ID: {pipeline.id}) for document '{document.title}' (ID: {document.id})")    
        
        # Removed direct text extraction logic - it's now handled by TextExtractionProcessor
        # file_path = document.file_path ...
        # if file_ext == '.txt': ... etc ...

        # Instantiate and execute the pipeline executor
        # The executor will call processors, one of which should be TextExtractionProcessor
        # If an LLM client is needed by processors, it should be obtained here
        try:
             from backend.core.dependencies import get_llm_client # Get LLM client if needed
             llm_client = get_llm_client()
        except Exception as client_err:
             logger.warning(f"Could not get LLM Client for pipeline execution {execution_id}: {client_err}. Some steps might fail.")
             llm_client = None

        executor = PipelineExecutor(llm_client=llm_client) # Pass client to executor
        results = await executor.execute(uuid.UUID(execution_id), pipeline, document) # Pass full document

        # 3. Update execution with results and status COMPLETED
        # Check if the executor itself reported errors
        if results.get("errors"):
             error_message = "; ".join(results["errors"]) # Combine errors from steps
             logger.error(f"Pipeline execution {execution_id} completed with errors: {error_message}")
             update_pipeline_execution_status(execution_id, "FAILED", error_message=error_message, results=results)
             # Return the results dictionary which contains the errors
             return results 
        else:
            # Success case
            logger.info(f"Pipeline execution {execution_id} completed successfully.")
            # Create processing result record
            try:
                await create_processing_result(
                    session,
                    document.id, 
                    pipeline.name, 
                    results # Pass the whole result context
                )
                logger.info(f"Processing results saved for document {document.id} via pipeline {pipeline.id}")
            except Exception as e:
                # Log error but don't fail the whole task just for this
                logger.exception(f"Error saving processing results for pipeline execution {execution_id}: {str(e)}")

            update_pipeline_execution_status(execution_id, "COMPLETED", results=results)
            # Add status to returned results for consistency
            results["status"] = "success"
            return results

# --- NEW Embedding Processing Task ---

@celery_app.task(name="process_document_embeddings")
def process_document_embeddings_task(
    document_id_str: str,
    user_id_str: str, # Pass user_id for logging/context
    model: str,
    chunk_size: int,
    chunk_overlap: int
):
    """
    Celery task to trigger asynchronous embedding processing for a document.
    Calls an async helper function using asyncio.run().
    """
    embedding_logger.info(f"Received task to process embeddings for doc {document_id_str} by user {user_id_str}")
    start_time = time.time()
    try:
        # Run the asynchronous helper function
        asyncio.run(_process_document_embeddings_async(
            document_id_str,
            user_id_str,
            model,
            chunk_size,
            chunk_overlap
        ))
        elapsed = time.time() - start_time
        embedding_logger.info(f"Embedding processing task for doc {document_id_str} completed successfully in {elapsed:.2f}s")
        return {"status": "success", "document_id": document_id_str}
    except Exception as e:
        elapsed = time.time() - start_time
        embedding_logger.error(f"Embedding processing task for doc {document_id_str} failed after {elapsed:.2f}s: {e}", exc_info=True)
        # Optionally: update document status to FAILED here if not done in async part
        return {"status": "error", "document_id": document_id_str, "error": str(e)}

async def _process_document_embeddings_async(
    document_id_str: str,
    user_id_str: str, 
    model: str,
    chunk_size: int,
    chunk_overlap: int
):
    """
    Asynchronous helper function containing the core logic for embedding processing.
    Uses the shared async session context manager.
    """
    document_id = uuid.UUID(document_id_str)
    user_id = uuid.UUID(user_id_str)

    embedding_logger.info(f"[Async Helper] Starting embedding processing for doc {document_id}")
    
    # Import necessary components here to avoid circular dependencies at module level
    from backend.database.session import get_async_session_context
    from backend.modules.document.service import DocumentService
    from backend.database.models.document import ProcessingStatus # Import Enum
    from backend.core.dependencies import get_llm_client # Correct import path
    from backend.modules.pipeline.processors import get_processor # Assuming processor registry

    final_status = ProcessingStatus.FAILED # Default to failed unless explicitly completed
    try:
        async with get_async_session_context() as session:
            embedding_logger.debug(f"[Async Helper] Acquired DB session {id(session)} for doc {document_id}")
            
            # Instantiate DocumentService
            try:
                llm_client = get_llm_client()
                doc_service = DocumentService(llm_client=llm_client)
                embedding_logger.debug(f"[Async Helper] DocumentService instantiated for doc {document_id}")
            except Exception as client_err:
                embedding_logger.error(f"[Async Helper] Failed to get LLM client for doc {document_id}: {client_err}", exc_info=True)
                raise # Let outer try handle status update

            # 1. Get document and set status to PROCESSING
            document = await session.get(Document, document_id) # Use session directly
            if not document:
                embedding_logger.error(f"[Async Helper] Document {document_id} not found during processing.")
                return # Exit task gracefully
            
            # Check if already processed or currently processing to avoid redundant work
            if document.processing_status in [ProcessingStatus.COMPLETED, ProcessingStatus.PROCESSING]:
                 embedding_logger.warning(f"[Async Helper] Document {document_id} is already {document.processing_status.value}. Skipping task.")
                 return

            document.processing_status = ProcessingStatus.PROCESSING
            await session.flush() # Flush to make status update visible if needed, commit happens later
            embedding_logger.info(f"[Async Helper] Set doc {document_id} status to PROCESSING")
            
            # Optional: Re-verify permissions? 
            # if document.user_id != user_id: ...
            
            # 2. Get the processor
            try:
                embedding_processor = get_processor(
                    "embedding", 
                    config={
                        "model": model,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap
                    }
                )
                embedding_logger.debug(f"[Async Helper] Embedding processor obtained for doc {document_id}")
            except (ImportError, ValueError) as proc_err:
                 embedding_logger.error(f"[Async Helper] Error getting embedding processor for doc {document_id}: {proc_err}", exc_info=True)
                 raise proc_err # Let outer try handle status update

            embedding_logger.info(f"[Async Helper] Calling embedding_processor.process() for doc {document_id}...")
            
            # 3. Call the process method
            result = await embedding_processor.process(document, {}) 
            embedding_logger.debug(f"[Async Helper] Processor result for doc {document_id}: {result}")
            
            # 4. Verify result and save embeddings
            if "error" in result:
                embedding_logger.error(f"[Async Helper] Processor returned error for doc {document_id}: {result['error']}")
                final_status = ProcessingStatus.FAILED
                document.error_message = result['error'][:1024] # Store error if field exists
            else:
                embeddings_data = result.get("embeddings")
                chunks_text_data = result.get("chunks_text")

                if embeddings_data and chunks_text_data:
                    saved_model = result.get("model", model)
                    try:
                        saved_list = await doc_service.save_embeddings(
                            db=session, # Pass the session
                            document_id=document_id,
                            embeddings=embeddings_data,
                            chunks_text=chunks_text_data, 
                            model=saved_model
                        )
                        embedding_logger.info(f"[Async Helper] Successfully saved {len(saved_list)} embeddings for doc {document_id}.")
                        final_status = ProcessingStatus.COMPLETED # Mark as completed only on full success
                        document.error_message = None # Clear previous errors if field exists
                    except Exception as save_err:
                        embedding_logger.error(f"[Async Helper] Failed to save embeddings for doc {document_id}: {save_err}", exc_info=True)
                        final_status = ProcessingStatus.FAILED
                        document.error_message = f"Failed to save embeddings: {save_err}"[:1024]
                        # Do not re-raise here, let finally block handle status update
                elif "chunk_count" in result and result["chunk_count"] == 0:
                     embedding_logger.warning(f"[Async Helper] No embeddings generated for doc {document_id} (0 chunks).")
                     final_status = ProcessingStatus.COMPLETED # Consider it completed, but with 0 embeddings
                     document.error_message = "No content found for embedding processing."
                else:
                    embedding_logger.error(f"[Async Helper] Unexpected processor result (no embeddings/chunks) for doc {document_id}: {result}")
                    final_status = ProcessingStatus.FAILED
                    document.error_message = "Unexpected processor result."
            
            # Update final status - commit happens automatically via context manager on success
            document.processing_status = final_status
            embedding_logger.info(f"[Async Helper] Setting final status for doc {document_id} to {final_status.value}")

    except Exception as task_exc:
        embedding_logger.error(f"[Async Helper] Unhandled exception in embedding task for doc {document_id}: {task_exc}", exc_info=True)
        # Attempt to update status to FAILED in a new session if the main one failed
        try:
            async with get_async_session_context() as error_session:
                doc_to_fail = await error_session.get(Document, document_id)
                if doc_to_fail:
                    doc_to_fail.processing_status = ProcessingStatus.FAILED
                    doc_to_fail.error_message = f"Task failed: {task_exc}"[:1024]
                    await error_session.flush() # Commit happens on context exit
                    embedding_logger.info(f"[Async Helper] Updated doc {document_id} status to FAILED due to exception.")
        except Exception as update_err:
            embedding_logger.error(f"[Async Helper] Failed to update document status to FAILED after task exception for doc {document_id}: {update_err}", exc_info=True)
        # Re-raise the original exception so Celery knows the task failed
        raise task_exc

# --- End NEW Embedding Processing Task ---

logger.info("Celery tasks module loaded (using direct SQLAlchemy).")

  
