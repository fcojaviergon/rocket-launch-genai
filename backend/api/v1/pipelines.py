from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
import logging
from sqlalchemy import select

import uuid
from uuid import UUID

from core.dependencies import get_current_user, get_db, get_current_admin_user
from database.models.user import User
from database.models.pipeline import Pipeline, PipelineExecution, ExecutionStatus
from schemas.pipeline import (
    PipelineConfigCreate, 
    PipelineConfigUpdate, 
    PipelineConfigResponse,
    PipelineExecutionCreate,
    PipelineExecutionResponse,
    ProcessBatchRequest,
    BatchJobResponse
)
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from modules.pipeline.service import PipelineService
from core.dependencies import get_pipeline_service, get_db, get_current_user, get_current_admin_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Endpoints for pipeline configurations
@router.post("/configs", response_model=PipelineConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline_config(
    pipeline: PipelineConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Create a new pipeline configuration"""
    try:
        # Delegate to service layer
        created_pipeline = await pipeline_service.create_pipeline(
            db=db, 
            pipeline_data=pipeline, 
            user=current_user
        )
        return created_pipeline
    except ValueError as e:
        # Handle potential validation/creation errors from service
        logger.error(f"Validation error creating pipeline config: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e: # Catch unexpected errors
        logger.error(f"Error creating configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while creating the configuration."
        )

@router.get("/configs", response_model=List[PipelineConfigResponse])
async def get_pipeline_configs(
    skip: int = 0, 
    limit: int = 100,
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Get all pipeline configurations"""
    try:
        # Delegate to service layer
        configs = await pipeline_service.get_pipelines(
            db=db,
            user=current_user,
            skip=skip,
            limit=limit,
            type_filter=type
        )
        return configs
    except Exception as e:
        logger.error(f"Error getting configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An internal error occurred while retrieving configurations."
        )

@router.get("/configs/{pipeline_id}", response_model=PipelineConfigResponse)
async def get_pipeline_config(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Get a pipeline configuration by ID"""
    try:
        # Delegate to service layer
        pipeline = await pipeline_service.get_pipeline(db=db, pipeline_id=pipeline_id, user=current_user)
        
        if not pipeline:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline configuration not found")
        
        return pipeline
    except PermissionError as e:
        logger.warning(f"Permission denied for config {pipeline_id}: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        if isinstance(e, HTTPException): # Should not happen if service raises PermissionError
            raise e
        logger.error(f"Error getting configuration {pipeline_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error getting configuration.")

@router.put("/configs/{pipeline_id}", response_model=PipelineConfigResponse)
async def update_pipeline_config(
    pipeline_id: UUID,
    pipeline: PipelineConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Update a pipeline configuration"""
    try:
        updated_pipeline = await pipeline_service.update_pipeline(
            db=db,
            pipeline_id=pipeline_id,
            pipeline_data=pipeline,
            user=current_user
        )
        if updated_pipeline is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline configuration not found")
        return updated_pipeline
    except PermissionError as e:
        logger.warning(f"Permission denied for updating config {pipeline_id}: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error updating pipeline config {pipeline_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating configuration {pipeline_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating configuration.")

@router.delete("/configs/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_config(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Delete a pipeline configuration"""
    try:
        deleted = await pipeline_service.delete_pipeline(db=db, pipeline_id=pipeline_id, user=current_user)
        if not deleted:
            # Service returns False if not found
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline configuration not found")
        return None # Return None for 204
    except PermissionError as e:
        logger.warning(f"Permission denied for deleting config {pipeline_id}: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e: # Catch other errors from service like DB errors
        logger.error(f"Error deleting pipeline config {pipeline_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting configuration.")
    except Exception as e:
        logger.error(f"Unexpected error deleting configuration {pipeline_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting configuration.")

# Endpoints for pipeline executions
@router.post("/executions", response_model=PipelineExecutionResponse)
async def execute_pipeline(
    execution_data: PipelineExecutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Execute a pipeline for a document, creating an execution record and triggering a background task."""
    try:
        # Service creates the DB record
        db_execution = await pipeline_service.create_execution(db, execution_data, current_user)

        # Start asynchronous task (assuming Celery)
        try:
            from tasks.tasks import execute_pipeline as celery_execute_pipeline
            logger.info(f"Launching Celery task for execution ID {db_execution.id}")
            task = celery_execute_pipeline.delay(
                str(db_execution.pipeline_id),
                str(db_execution.document_id),
                str(db_execution.id)
            )
            # Optionally save task_id back to the execution record if needed immediately
            # db_execution.task_id = task.id
            # await db.commit()
        except ImportError:
            logger.error("Celery tasks not found. Cannot launch background execution.")
            # Decide if this should be a 500 error or handled differently
            raise HTTPException(
                 status_code=status.HTTP_501_NOT_IMPLEMENTED,
                 detail="Background task execution is not configured."
            )
        except Exception as task_err:
             logger.error(f"Failed to launch Celery task for execution {db_execution.id}: {task_err}")
             # Consider how to handle this - maybe mark execution as failed?
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail="Failed to launch background execution task."
             )

        # Return the created execution record (potentially without task_id if not saved)
        return db_execution # Pydantic should handle the conversion

    except ValueError as e:
        # Errors from service (e.g., pipeline not found)
        logger.error(f"Error creating pipeline execution record: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error starting pipeline execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting pipeline execution."
        )

@router.get("/executions/{execution_id}", response_model=PipelineExecutionResponse)
async def get_execution_status(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Get the status and details of a pipeline execution."""
    try:
        execution = await pipeline_service.get_execution(db, execution_id, current_user)
        if not execution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

        # Return the ORM object directly. 
        # response_model=PipelineExecutionResponse will handle serialization.
        # Ensure PipelineExecutionResponse schema includes necessary fields (like pipeline_name if needed)
        # and has Config.from_attributes = True
        return execution

    except PermissionError as e:
        logger.warning(f"Permission denied for execution {execution_id}: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting execution status {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting execution status."
        )

@router.post("/executions/{execution_id}/cancel", response_model=PipelineExecutionResponse)
async def cancel_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Cancel a pipeline execution if it is in a cancellable state."""
    try:
        execution = await pipeline_service.cancel_execution(db, execution_id, user=current_user)
        if not execution:
             # Service should raise NotFoundError or PermissionError, so this case implies success
             # If service returns None on non-cancellable state, handle via ValueError below
             # Assuming service raises appropriate exceptions for not found / permissions
             # Let's simplify: if we get here, cancellation was likely accepted or already done
             # Re-fetch the execution to return its current state
             current_execution_state = await pipeline_service.get_execution(db, execution_id, current_user)
             if not current_execution_state:
                 # Should not happen if cancel_execution didn't raise NotFoundError
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found after cancellation attempt.")
             return current_execution_state # Return ORM object, rely on response_model

    except PermissionError as e:
        logger.warning(f"Permission denied for cancelling execution {execution_id}: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        # Handles non-cancellable state error from service
        logger.warning(f"Cannot cancel execution {execution_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error canceling execution {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error canceling execution."
        )

@router.post("/batch-process", response_model=BatchJobResponse)
async def process_batch(
    request: ProcessBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Processes a batch of documents with a specified pipeline."""
    try:
        # Validate pipeline exists (can be done in service too)
        pipeline_config = await pipeline_service.get_pipeline(db, request.pipeline_id, current_user)
        if not pipeline_config:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline configuration not found")

        # TODO: Add validation here or in service to check if user has access to all document_ids

        job_id = str(uuid.uuid4()) # Generate Job ID
        execution_ids = []

        # Create execution records via service
        executions = await pipeline_service.create_batch_executions(
             db, request.pipeline_id, request.document_ids, current_user, request.parameters
        )

        # Trigger background tasks for each execution
        try:
            from tasks.tasks import execute_pipeline as celery_execute_pipeline
            for execution in executions:
                logger.info(f"Launching batch Celery task for execution ID {execution.id}")
                task = celery_execute_pipeline.delay(
                    str(execution.pipeline_id),
                    str(execution.document_id),
                    str(execution.id)
                )
                execution_ids.append(str(execution.id))
                # Optionally save task IDs if needed
        except ImportError:
            logger.error("Celery tasks not found. Cannot launch background execution for batch.")
            raise HTTPException(
                 status_code=status.HTTP_501_NOT_IMPLEMENTED,
                 detail="Background task execution is not configured."
            )
        except Exception as task_err:
             logger.error(f"Failed to launch Celery tasks for batch {job_id}: {task_err}")
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail="Failed to launch background execution tasks for batch."
             )

        logger.info(f"Batch processing job {job_id} started for {len(executions)} documents.")
        # Return job ID and initial status
        return BatchJobResponse(job_id=job_id, status="pending", total_documents=len(executions), execution_ids=execution_ids)

    except ValueError as e: # Catch errors from service during execution creation
        logger.error(f"Error initiating batch process: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error starting batch processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting batch processing."
        )

@router.get("/executions/by-document/{document_id}", response_model=List[PipelineExecutionResponse])
async def get_executions_by_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Get all pipeline executions for a specific document, checking permissions."""
    try:
        logger.info(f"Fetching executions for document {document_id} by user {current_user.id}")
        # Delegate to service, passing user for permission check
        executions = await pipeline_service.get_executions_by_document(
            db=db,
            document_id=document_id,
            user=current_user # Service handles filtering by user/admin
        )
        logger.info(f"Found {len(executions)} executions for document {document_id}")

        # Return the list of ORM objects directly
        # response_model=List[PipelineExecutionResponse] will handle serialization
        return executions

    except PermissionError as e: # Catch permission error if service raises it for the document itself
        logger.warning(f"Permission denied for document {document_id}: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting executions for document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting executions for document."
        ) 