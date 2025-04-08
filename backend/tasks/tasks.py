"""
Definición de tareas de Celery para procesamiento asíncrono
"""
import time
import logging
import asyncio
import json
import uuid
from .worker import celery_app
from database.models.pipeline import Pipeline, PipelineExecution
from database.models.document import Document
from modules.pipeline.executor import PipelineExecutor, create_processing_result
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_async_session_context
from core.config import settings
import os
import traceback
from datetime import datetime

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
def execute_pipeline(pipeline_id: str, document_id: str, execution_id: str | None = None):
    """
    Execute a processing pipeline for a document. Wraps the async logic.
    
    Args:
        pipeline_id (str): ID pipeline to execute
        document_id (str): ID of the document to process
        execution_id (str, optional): ID of the execution in the database (MUST be provided)
    
    Returns:
        dict: Result of the execution, including final status and elapsed time.
    """
    if not execution_id:
        logger.error("FATAL: execute_pipeline task called without execution_id. Cannot track status.")
        # Decide how to handle this - fail task, return error, etc.
        # For now, return error immediately.
        return {
            "status": "error",
            "pipeline_id": pipeline_id,
            "document_id": document_id,
            "error": "Missing execution_id for tracking.",
            "elapsed_time": 0
        }
        
    logger.info(f"Starting pipeline task {execution_id} for pipeline {pipeline_id}, doc {document_id}")
    start_time = time.time()
    loop = asyncio.get_event_loop() # Get the current event loop for this worker process
    
    try:
        # Execute the async logic using loop.run_until_complete
        result_data = loop.run_until_complete(
            _execute_pipeline_async(pipeline_id, document_id, execution_id)
        )
        
        elapsed = time.time() - start_time
        
        # Prepare final result based on what _execute_pipeline_async returns
        final_status = result_data.get("status", "error") # Default to error if status missing
        final_result = {
            "status": final_status,
            "pipeline_id": pipeline_id,
            "document_id": document_id,
            "execution_id": execution_id,
            "elapsed_time": elapsed,
            "message": result_data.get("message", ""),
            "results": result_data # Include the full results from the async function
        }
        
        if final_status == "error" and "error" not in final_result:
            final_result["error"] = result_data.get("error", "Unknown error during async execution")
            
        logger.info(f"Pipeline task {execution_id} finished with status '{final_status}' in {elapsed:.2f}s")
        return final_result
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"FATAL Error in pipeline task {execution_id}: {str(e)}", exc_info=True)
        
        # Attempt ASYNC fallback using the SAME loop
        try:
            async def fallback_update():
                # Note: Re-getting context might be needed if main one failed badly
                async with get_async_session_context() as error_session:
                    logger.warning(f"Attempting asynchronous fallback to mark execution {execution_id} as FAILED.")
                    await _async_update_pipeline_execution_status(
                        error_session, 
                        uuid.UUID(execution_id), 
                        "FAILED", 
                        error_message=f"Task failed unexpectedly: {str(e)}"
                    )
            # Run fallback on the same loop
            loop.run_until_complete(fallback_update())
        except Exception as fallback_err:
            logger.error(f"Failed ASYNCHRONOUS fallback status update for {execution_id}: {fallback_err}", exc_info=True)
             
        # Prepare error result for Celery
        return {
            "status": "error",
            "pipeline_id": pipeline_id,
            "document_id": document_id,
            "execution_id": execution_id,
            "error": f"Task failed unexpectedly: {str(e)}",
            "elapsed_time": elapsed
        }

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

async def _execute_pipeline_async(pipeline_id: str, document_id: str, execution_id: str):
    """
    Async core logic for pipeline execution. Uses shared session context.
    Handles intermediate status updates.
    
    Args:
        pipeline_id (str): ID of the pipeline.
        document_id (str): ID of the document.
        execution_id (str): ID of the database execution record (UUID as string).
        
    Returns:
        dict: Results of the pipeline execution, including status and any errors.
    """
    exec_id_uuid = uuid.UUID(execution_id)
    pipeline_id_uuid = uuid.UUID(pipeline_id)
    document_id_uuid = uuid.UUID(document_id)
    
    logger.info(f"[_execute_pipeline_async] Running for exec {execution_id}")
    
    # Default return values in case of early exit or unhandled error
    final_result_context = {"status": "error", "error": "Pipeline execution failed unexpectedly."}

    try:
        # Use the shared async session context
        async with get_async_session_context() as session:
            logger.debug(f"[_execute_pipeline_async] Acquired session {id(session)} for exec {execution_id}")
            
            # 1. Mark as RUNNING
            await _async_update_pipeline_execution_status(session, exec_id_uuid, "RUNNING")

            # 2. Load pipeline and document using the session
            pipeline = await session.get(Pipeline, pipeline_id_uuid)
            document = await session.get(Document, document_id_uuid)
                
            if not pipeline or not document:
                error_msg = f"Pipeline {pipeline_id} or document {document_id} not found"
                logger.error(f"[_execute_pipeline_async] {error_msg} for exec {execution_id}")
                await _async_update_pipeline_execution_status(session, exec_id_uuid, "FAILED", error_message=error_msg)
                # Return error context
                final_result_context["error"] = error_msg
                return final_result_context # Exit async function

            logger.info(f"[_execute_pipeline_async] Executing pipeline '{pipeline.name}' (ID: {pipeline.id}) for doc '{document.title}' (ID: {document.id}) - Exec ID: {execution_id}")    
            
            # 3. Get LLM Client (optional, based on pipeline steps)
            try:
                 from core.dependencies import get_llm_client
                 llm_client = get_llm_client()
            except Exception as client_err:
                 logger.warning(f"Could not get LLM Client for pipeline execution {execution_id}: {client_err}. Some steps might fail.")
                 llm_client = None

            # 4. Execute pipeline steps
            executor = PipelineExecutor(llm_client=llm_client)
            # Execute and get the results dictionary
            results_context = await executor.execute(exec_id_uuid, pipeline, document) 

            # 5. Update execution status based on results_context
            if results_context.get("status") == "error" or results_context.get("errors"):
                 error_message = "; ".join(results_context.get("errors", ["Unknown execution error"]))
                 logger.error(f"[_execute_pipeline_async] Pipeline execution {execution_id} completed with errors: {error_message}")
                 await _async_update_pipeline_execution_status(session, exec_id_uuid, "FAILED", error_message=error_message, results=results_context)
                 final_result_context = results_context # Pass back the context with errors
                 final_result_context["status"] = "error" # Ensure status is error
            else:
                # Success case
                logger.info(f"[_execute_pipeline_async] Pipeline execution {execution_id} completed successfully.")
                
                # 6. Save processing result record (optional, but good practice)
                try:
                    await create_processing_result(
                        session,         # Pass session as first positional argument
                        document_id=document.id, 
                        pipeline_name=pipeline.name, 
                        results=results_context # Pass results as 'results' keyword arg
                    )
                    logger.info(f"[_execute_pipeline_async] Processing results saved for doc {document.id} via pipeline {pipeline.id} (Exec ID: {execution_id})")
                except Exception as pr_err:
                    logger.exception(f"[_execute_pipeline_async] Error saving processing results for exec {execution_id}: {str(pr_err)}")
                    # Log error but don't fail the task just for this

                # 7. Mark execution as COMPLETED
                await _async_update_pipeline_execution_status(session, exec_id_uuid, "COMPLETED", results=results_context)
                final_result_context = results_context # Pass back success context
                final_result_context["status"] = "success" # Ensure status is success
        
        # Session commits/closes automatically via context manager

    except Exception as e:
         # Catch exceptions during the async execution itself
         logger.error(f"[_execute_pipeline_async] Unhandled exception during pipeline execution {execution_id}: {e}", exc_info=True)
         final_result_context = {"status": "error", "error": f"Unhandled exception: {str(e)}"}
         # Attempt to mark as FAILED within a NEW session, as the old one might be invalid
         try:
            async with get_async_session_context() as error_session:
                 logger.warning(f"[_execute_pipeline_async] Attempting final FAILED status update for {execution_id} in new session.")
                 await _async_update_pipeline_execution_status(error_session, exec_id_uuid, "FAILED", error_message=final_result_context["error"])
         except Exception as final_update_err:
            logger.error(f"[_execute_pipeline_async] Failed to update status to FAILED after unhandled exception for {execution_id}: {final_update_err}", exc_info=True)
            
    logger.debug(f"[_execute_pipeline_async] Returning context for exec {execution_id}: {final_result_context.get('status')}")
    return final_result_context # Return the results/error context

# --- NEW Async Status Update Helper ---
async def _async_update_pipeline_execution_status(
    session: AsyncSession, 
    execution_id: uuid.UUID, 
    status: str, 
    results: dict | None = None, 
    error_message: str | None = None
):
    """Asynchronously update pipeline execution status using the provided session."""
    if not execution_id:
        logger.error("Cannot update status: Execution ID is missing.")
        return False
        
    try:
        execution = await session.get(PipelineExecution, execution_id)
        if not execution:
            logger.error(f"Cannot update status: Execution {execution_id} not found.")
            return False

        # Update common fields
        execution.status = status
        execution.updated_at = datetime.now()

        # Update status-specific fields
        if status == "RUNNING" and not execution.started_at:
            execution.started_at = datetime.now()
        elif status == "COMPLETED":
            execution.completed_at = datetime.now()
            execution.error_message = None # Clear error on completion
            if results:
                # Ensure results are JSON serializable - PipelineExecutor results should be
                try:
                    execution.results = json.dumps(results)
                except TypeError as json_err:
                    logger.error(f"Failed to serialize results for execution {execution_id}: {json_err}")
                    execution.results = json.dumps({"error": "Result serialization failed"})
        elif status == "FAILED":
            execution.error_message = error_message[:1024] if error_message else "Unknown error" # Truncate error

        await session.flush() # Make changes visible within the transaction
        logger.info(f"Updated execution {execution_id} status to {status} in session {id(session)}")
        return True
    except Exception as e:
        logger.error(f"Error updating execution {execution_id} status to {status}: {e}", exc_info=True)
        # Don't let status update failure stop the main task flow easily,
        # but log it thoroughly. Consider raising if critical.
        return False

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
    loop = asyncio.get_event_loop() # Get the current event loop
    try:
        # Run the asynchronous helper function using loop.run_until_complete
        loop.run_until_complete(_process_document_embeddings_async(
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
    Now allows reprocessing for COMPLETED/FAILED documents.
    """
    document_id = uuid.UUID(document_id_str)
    user_id = uuid.UUID(user_id_str)

    embedding_logger.info(f"[Async Helper] Starting embedding processing/reprocessing for doc {document_id} with model '{model}'")
    
    # Import necessary components here to avoid circular dependencies at module level
    from database.session import get_async_session_context
    from modules.document.service import DocumentService # Keep for save_embeddings
    from database.models.document import Document, ProcessingStatus # Import Enum and Document Model
    from core.dependencies import get_llm_client
    # Import processors directly or via get_processor
    from modules.pipeline.processors import TextExtractionProcessor, EmbeddingProcessor, get_processor

    final_status = ProcessingStatus.FAILED # Default to failed
    error_message_final = "Unknown processing error"

    try:
        async with get_async_session_context() as session:
            embedding_logger.debug(f"[Async Helper] Acquired DB session {id(session)} for doc {document_id}")
            
            # 1. Get document and set status to PROCESSING
            document = await session.get(Document, document_id)
            if not document:
                embedding_logger.error(f"[Async Helper] Document {document_id} not found.")
                return # Exit task gracefully
            
            # Check if already processing to avoid redundant work
            # Allow reprocessing for COMPLETED or FAILED states
            if document.processing_status == ProcessingStatus.PROCESSING:
                 embedding_logger.warning(f"[Async Helper] Document {document_id} is already {document.processing_status.value}. Skipping task.")
                 return
            elif document.processing_status == ProcessingStatus.PENDING:
                 embedding_logger.info(f"[Async Helper] Document {document_id} is PENDING. Proceeding to PROCESSING.")
            elif document.processing_status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                embedding_logger.info(f"[Async Helper] Document {document_id} status is {document.processing_status.value}. Reprocessing allowed.")
            # Add other states if needed, e.g. NOT_PROCESSED
            elif document.processing_status == ProcessingStatus.NOT_PROCESSED:
                embedding_logger.info(f"[Async Helper] Document {document_id} is NOT_PROCESSED. Starting initial processing.")
            else:
                # Should not happen with current enum, but good practice
                embedding_logger.warning(f"[Async Helper] Document {document_id} has unexpected status {document.processing_status.value}. Attempting to process anyway.")

            # Set status to PROCESSING and clear any previous error message
            document.processing_status = ProcessingStatus.PROCESSING
            document.error_message = None # Clear previous errors on new attempt
            await session.flush() # Flush to make status update visible
            embedding_logger.info(f"[Async Helper] Set doc {document_id} status to PROCESSING and cleared error message.")
            
            # --- START TEXT EXTRACTION ---
            context = {} # Initialize context
            text_processor = TextExtractionProcessor() # Instantiate text processor
            embedding_logger.info(f"[Async Helper] Running TextExtractionProcessor for doc {document_id}")
            context = await text_processor.process(document, context) # Run text extraction
            document_content = context.get("document_content")
            extraction_error = context.get("text_extraction_error")
            
            if extraction_error or not document_content:
                error_message_final = f"Text extraction failed: {extraction_error or 'No content extracted'}"
                embedding_logger.error(f"[Async Helper] {error_message_final} for doc {document_id}")
                # Status will remain FAILED (default)
                # Update error message in DB before exiting try block
            else:
                embedding_logger.info(f"[Async Helper] Text extracted successfully for doc {document_id}. Length: {len(document_content)}")
                # --- END TEXT EXTRACTION ---
                
                # --- START EMBEDDING PROCESSING (only if text extraction succeeded) ---
                try:
                    llm_client = get_llm_client()
                    embedding_processor = get_processor(
                        "embedding", 
                        config={
                            "model": model,
                            "chunk_size": chunk_size,
                            "chunk_overlap": chunk_overlap
                        },
                        llm_client=llm_client
                    )
                    embedding_logger.debug(f"[Async Helper] Embedding processor obtained for doc {document_id}")

                    embedding_logger.info(f"[Async Helper] Calling embedding_processor.process() for doc {document_id}...")
                    
                    # Pass the context containing the extracted text
                    result = await embedding_processor.process(document, context) 
                    embedding_logger.debug(f"[Async Helper] Processor result for doc {document_id}: {result}")
                    
                    # 4. Verify result and save embeddings
                    if "error" in result:
                        error_message_final = f"Embedding processor failed: {result['error']}"
                        embedding_logger.error(f"[Async Helper] Processor returned error for doc {document_id}: {result['error']}")
                        # Status remains FAILED
                    else:
                        embeddings_data = result.get("embeddings")
                        chunks_text_data = result.get("chunks_text")

                        if embeddings_data and chunks_text_data:
                            saved_model = result.get("model", model)
                            try:
                                # Need DocumentService to save embeddings
                                doc_service = DocumentService(llm_client=llm_client) # Instantiate service
                                # Call updated save_embeddings with necessary args
                                saved_list = await doc_service.save_embeddings(
                                    db=session,
                                    document_id=document_id,
                                    embeddings=embeddings_data,
                                    chunks_text=chunks_text_data, 
                                    model=saved_model # Pass the model used
                                )
                                embedding_logger.info(f"[Async Helper] Successfully saved/updated {len(saved_list)} embeddings for doc {document_id}.")
                                final_status = ProcessingStatus.COMPLETED # Mark as completed only on full success
                                error_message_final = None # Clear error message on success
                            except Exception as save_err:
                                error_message_final = f"Failed to save embeddings: {save_err}"[:1024]
                                embedding_logger.error(f"[Async Helper] {error_message_final} for doc {document_id}", exc_info=True)
                                # Status remains FAILED
                        elif result.get("chunk_count") == 0:
                             error_message_final = "No content found for embedding processing."
                             embedding_logger.warning(f"[Async Helper] No embeddings generated for doc {document_id} (0 chunks). Status set to FAILED.")
                             # Status remains FAILED (as no embeddings were generated/saved)
                        else:
                            error_message_final = "Embedding processor returned unexpected result (no embeddings/chunks)."
                            embedding_logger.error(f"[Async Helper] {error_message_final} for doc {document_id}: {result}")
                            # Status remains FAILED
                except Exception as emb_exc:
                     error_message_final = f"Embedding processing step failed: {emb_exc}"
                     embedding_logger.error(f"[Async Helper] Error during embedding processing for doc {document_id}: {emb_exc}", exc_info=True)
                     # Status remains FAILED
                 # --- END EMBEDDING PROCESSING ---
            
            # Update final status and error message outside the inner try,
            # ensuring it reflects extraction or embedding failure
            document.processing_status = final_status
            document.error_message = error_message_final
            embedding_logger.info(f"[Async Helper] Setting final status for doc {document_id} to {final_status.value} with error: {error_message_final}")
            # Commit happens automatically via context manager 'async with' on successful exit

    except Exception as task_exc:
        embedding_logger.error(f"[Async Helper] Unhandled exception in embedding task for doc {document_id}: {task_exc}", exc_info=True)
        # Attempt to update status to FAILED in a new session if the main one failed
        try:
            async with get_async_session_context() as error_session:
                doc_to_fail = await error_session.get(Document, document_id)
                if doc_to_fail and doc_to_fail.processing_status != ProcessingStatus.COMPLETED: # Avoid overwriting completed status
                    doc_to_fail.processing_status = ProcessingStatus.FAILED
                    doc_to_fail.error_message = f"Task failed: {task_exc}"[:1024]
                    await error_session.flush() # Commit happens on context exit
                    embedding_logger.info(f"[Async Helper] Updated doc {document_id} status to FAILED due to task exception.")
        except Exception as update_err:
            embedding_logger.error(f"[Async Helper] Failed to update document status to FAILED after task exception for doc {document_id}: {update_err}", exc_info=True)
        # No need to re-raise here, Celery will mark failed based on return/exception

# --- End NEW Embedding Processing Task ---

logger.info("Celery tasks module adapted to use get_event_loop().run_until_complete().")

  
