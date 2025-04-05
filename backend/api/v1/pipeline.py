from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
import logging
from sqlalchemy import select
from uuid import UUID

from core.deps import get_current_user, get_db, get_current_admin_user
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

router = APIRouter()
logger = logging.getLogger(__name__)

# Endpoints for pipeline configurations
@router.post("/configs", response_model=PipelineConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline_config(
    pipeline: PipelineConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new pipeline configuration"""
    try:
        # Process steps to ensure they have id and type
        steps = []
        if pipeline.steps:
            for step in pipeline.steps:
                step_dict = step.dict()
                if not step_dict.get("id"):
                    step_dict["id"] = step_dict.get("name")
                if not step_dict.get("type"):
                    step_dict["type"] = "processor"
                steps.append(step_dict)
        
        # Convert metadata to dictionary if it's not
        metadata = {}
        if pipeline.metadata and isinstance(pipeline.metadata, dict):
            metadata = pipeline.metadata
        
        # Convert to database model
        db_pipeline = Pipeline(
            name=pipeline.name,
            description=pipeline.description,
            type=pipeline.type,
            steps=steps,
            config_metadata=metadata,
            user_id=current_user.id
        )
        
        # Save to database
        db.add(db_pipeline)
        await db.commit()
        await db.refresh(db_pipeline)
        
        # Create a dictionary with processed data for the response
        pipeline_dict = {
            "id": db_pipeline.id,
            "name": db_pipeline.name,
            "description": db_pipeline.description,
            "type": db_pipeline.type,
            "user_id": db_pipeline.user_id,
            "created_at": db_pipeline.created_at,
            "updated_at": db_pipeline.updated_at,
            "config_metadata": metadata
        }
        
        # Include processed steps
        pipeline_dict["steps"] = steps
        
        return pipeline_dict
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating configuration: {str(e)}"
        )

@router.get("/configs", response_model=List[PipelineConfigResponse])
async def get_pipeline_configs(
    skip: int = 0, 
    limit: int = 100,
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pipeline configurations"""
    try:
        # Build the base query
        query = select(Pipeline)
        
        # Filter by user unless admin
        if current_user.role != "admin":
            query = query.where(Pipeline.user_id == current_user.id)
        
        # Filter by type if specified
        if type:
            query = query.where(Pipeline.type == type)
        
        # Execute the query with pagination
        result = await db.execute(query.offset(skip).limit(limit))
        pipeline_configs = result.scalars().all()
        
        # Process data to ensure compatibility with the schema
        processed_configs = []
        for pipeline in pipeline_configs:
            pipeline_dict = {
                "id": pipeline.id,
                "name": pipeline.name,
                "description": pipeline.description,
                "type": pipeline.type,
                "user_id": pipeline.user_id,
                "created_at": pipeline.created_at,
                "updated_at": pipeline.updated_at,
                "config_metadata": {}  # Initialize as empty dictionary
            }
            
            # Ensure steps is a list and each step has id and type
            if hasattr(pipeline, "steps") and pipeline.steps:
                pipeline_dict["steps"] = []
                for step in pipeline.steps:
                    step_dict = dict(step)
                    if not step_dict.get("id"):
                        step_dict["id"] = step_dict.get("name")
                    if not step_dict.get("type"):
                        step_dict["type"] = "processor"
                    pipeline_dict["steps"].append(step_dict)
            else:
                pipeline_dict["steps"] = []
            
            # Ensure config_metadata is a dictionary
            if hasattr(pipeline, "config_metadata") and pipeline.config_metadata:
                if isinstance(pipeline.config_metadata, dict):
                    pipeline_dict["config_metadata"] = pipeline.config_metadata
            
            processed_configs.append(pipeline_dict)
        
        return processed_configs
    except Exception as e:
        logger.error(f"Error getting configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error getting configurations: {str(e)}"
        )

@router.get("/configs/{pipeline_id}", response_model=PipelineConfigResponse)
async def get_pipeline_config(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a pipeline configuration by ID"""
    try:
        # Find the pipeline in the database
        query = select(Pipeline).where(Pipeline.id == pipeline_id)
        result = await db.execute(query)
        pipeline = result.scalar_one_or_none()
        
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline configuration not found")
        
        # Verify permissions (only owner or admin)
        if pipeline.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to view this configuration")
        
        # Create a dictionary with processed data
        pipeline_dict = {
            "id": pipeline.id,
            "name": pipeline.name,
            "description": pipeline.description,
            "type": pipeline.type,
            "user_id": pipeline.user_id,
            "created_at": pipeline.created_at,
            "updated_at": pipeline.updated_at,
            "config_metadata": {}  # Initialize as empty dictionary
        }
        
        # Ensure steps is a list and each step has id and type
        if hasattr(pipeline, "steps") and pipeline.steps:
            pipeline_dict["steps"] = []
            for step in pipeline.steps:
                step_dict = dict(step)
                if not step_dict.get("id"):
                    step_dict["id"] = step_dict.get("name")
                if not step_dict.get("type"):
                    step_dict["type"] = "processor"
                pipeline_dict["steps"].append(step_dict)
        else:
            pipeline_dict["steps"] = []
        
        # Ensure config_metadata is a dictionary
        if hasattr(pipeline, "config_metadata") and pipeline.config_metadata:
            if isinstance(pipeline.config_metadata, dict):
                pipeline_dict["config_metadata"] = pipeline.config_metadata
        
        return pipeline_dict
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error getting configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting configuration: {str(e)}")

@router.put("/configs/{pipeline_id}", response_model=PipelineConfigResponse)
async def update_pipeline_config(
    pipeline_id: int,
    pipeline: PipelineConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar una configuración de pipeline"""
    try:
        # Buscar el pipeline en la base de datos
        query = select(Pipeline).where(Pipeline.id == pipeline_id)
        result = await db.execute(query)
        db_pipeline = result.scalar_one_or_none()
        
        if not db_pipeline:
            raise HTTPException(status_code=404, detail="Configuración de pipeline no encontrada")
        
        # Verificar permisos (solo propietario o admin)
        if db_pipeline.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="No tiene permiso para modificar esta configuración")
        
        # Actualizar campos
        update_data = pipeline.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key == "metadata":
                # Asegurar que metadata es un diccionario
                if value is not None and not isinstance(value, dict):
                    value = {}
                db_pipeline.config_metadata = value
            elif key == "steps":
                # Asegurar que cada step tiene id y type
                if value:
                    for step in value:
                        step_dict = dict(step)
                        if not step_dict.get("id"):
                            step_dict["id"] = step_dict.get("name")
                        if not step_dict.get("type"):
                            step_dict["type"] = "processor"
                    db_pipeline.steps = value
            else:
                setattr(db_pipeline, key, value)
        
        # Guardar cambios
        await db.commit()
        await db.refresh(db_pipeline)
        
        # Crear un diccionario con los datos procesados para la respuesta
        pipeline_dict = {
            "id": db_pipeline.id,
            "name": db_pipeline.name,
            "description": db_pipeline.description,
            "type": db_pipeline.type,
            "user_id": db_pipeline.user_id,
            "created_at": db_pipeline.created_at,
            "updated_at": db_pipeline.updated_at,
            "config_metadata": {} if db_pipeline.config_metadata is None else db_pipeline.config_metadata
        }
        
        # Procesar steps para la respuesta
        pipeline_dict["steps"] = []
        if hasattr(db_pipeline, "steps") and db_pipeline.steps:
            for step in db_pipeline.steps:
                step_dict = dict(step)
                if not step_dict.get("id"):
                    step_dict["id"] = step_dict.get("name")
                if not step_dict.get("type"):
                    step_dict["type"] = "processor"
                pipeline_dict["steps"].append(step_dict)
        
        return pipeline_dict
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error updating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating configuration: {str(e)}")

@router.delete("/configs/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_config(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a pipeline configuration"""
    try:
        # Search for the pipeline in the database
        query = select(Pipeline).where(Pipeline.id == pipeline_id)
        result = await db.execute(query)
        db_pipeline = result.scalar_one_or_none()
        
        if not db_pipeline:
            raise HTTPException(status_code=404, detail="Pipeline configuration not found")
        
        # Verify permissions (only owner or admin)
        if db_pipeline.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to delete this configuration")
        
        # Delete configuration
        await db.delete(db_pipeline)
        await db.commit()
        
        return None
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error deleting configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting configuration: {str(e)}")

# Endpoints for pipeline executions
@router.post("/executions", response_model=PipelineExecutionResponse)
async def execute_pipeline(
    execution: PipelineExecutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute a pipeline for a document"""
    try:
        # Verify that the configuration exists
        query = select(Pipeline).where(Pipeline.id == execution.pipeline_id)
        result = await db.execute(query)
        pipeline = result.scalars().first()
        
        if not pipeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pipeline configuration not found"
            )
        
        # Create execution record
        db_execution = PipelineExecution(
            pipeline_id=execution.pipeline_id,
            document_id=execution.document_id,
            status=ExecutionStatus.PENDING,
            parameters=execution.parameters,
            user_id=current_user.id
        )
        
        # Save to database
        db.add(db_execution)
        await db.commit()
        await db.refresh(db_execution)
        
        # Start asynchronous task to process the document
        from tasks.tasks import execute_pipeline as celery_execute_pipeline
        
        # Launch task in background
        logger.info(f"Launching task to execute pipeline with ID {db_execution.id}")
        task = celery_execute_pipeline.delay(
            str(db_execution.pipeline_id), 
            str(db_execution.document_id),
            str(db_execution.id)  # Pass execution_id as third parameter
        )
        db_execution.task_id = task.id
        await db.commit()
        
        return db_execution
    except Exception as e:
        await db.rollback()
        logger.error(f"Error starting pipeline execution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting execution: {str(e)}"
        )

@router.get("/executions/{execution_id}", response_model=PipelineExecutionResponse)
async def get_execution_status(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the status of a pipeline execution"""
    try:
        # Search for the execution
        query = select(PipelineExecution).where(PipelineExecution.id == execution_id)
        result = await db.execute(query)
        execution = result.scalar_one_or_none()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        # Verify permissions (only owner or admin)
        if execution.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this execution"
            )
            
        # Get the pipeline name
        pipeline_query = select(Pipeline).where(Pipeline.id == execution.pipeline_id)
        pipeline_result = await db.execute(pipeline_query)
        pipeline = pipeline_result.scalar_one_or_none()
        pipeline_name = pipeline.name if pipeline else "Unknown pipeline"
        
        # Format the response
        execution_dict = {
            "id": execution.id,
            "pipeline_id": execution.pipeline_id,
            "pipeline_name": pipeline_name,
            "document_id": execution.document_id,
            "user_id": execution.user_id,
            "status": execution.status.value,  # Convert enum to string
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "created_at": execution.created_at,
            "updated_at": execution.updated_at,
            "results": execution.results or {},
            "result": execution.results or {},  # Keep compatibility
            "parameters": execution.parameters or {},
            "error": execution.error_message,
        }
        
        return execution_dict
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting status: {str(e)}"
        )

@router.post("/executions/{execution_id}/cancel", response_model=PipelineExecutionResponse)
async def cancel_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a pipeline execution in progress"""
    try:
        # Search for the execution using asynchronous methods
        result = await db.execute(
            select(PipelineExecution).filter(PipelineExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        # Verify permissions
        if execution.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to cancel this execution"
            )
        
        # Verify if it can be canceled
        if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel an execution in state {execution.status}"
            )
        
        # Here the task would be canceled in the background
        
        # Update status
        execution.status = ExecutionStatus.CANCELED
        await db.commit()
        await db.refresh(execution)
        
        return execution
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error canceling execution {execution_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error canceling execution: {str(e)}"
        )

@router.post("/batch-process", response_model=BatchJobResponse)
async def process_batch(
    request: ProcessBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Procesar un lote de documentos con un pipeline"""
    try:
        # Verify that the configuration exists
        query = select(Pipeline).where(Pipeline.id == request.pipeline_id)
        result = await db.execute(query)
        pipeline = result.scalars().first()
        
        if not pipeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pipeline configuration not found"
            )
        
        # Create a unique job_id
        import uuid
        job_id = str(uuid.uuid4())
        
        # Start processing for each document
        from tasks.tasks import execute_pipeline as celery_execute_pipeline

        
        # List to store execution IDs
        execution_ids = []
        
        # Create an execution for each document and launch tasks
        for doc_id in request.document_ids:
            # Create execution record
            db_execution = PipelineExecution(
                pipeline_id=request.pipeline_id,
                document_id=doc_id,
                status=ExecutionStatus.PENDING,
                parameters=request.parameters,
                user_id=current_user.id
            )
            
            # Guardar en base de datos
            db.add(db_execution)
            await db.commit()
            await db.refresh(db_execution)
            
            # Store execution ID
            execution_ids.append(str(db_execution.id))
            
            # Launch task in background
            logger.info(f"Launching batch task for document {doc_id} with pipeline {request.pipeline_id}")
            task = celery_execute_pipeline.delay(
                str(db_execution.pipeline_id), 
                str(db_execution.document_id),
                str(db_execution.id)  # Pass execution_id as third parameter
            )
            db_execution.task_id = task.id
            await db.commit()

            return db_execution
        
        logger.info(f"Batch processing started with job_id: {job_id}, documents: {len(request.document_ids)}")
        return BatchJobResponse(job_id=job_id, status="pending", total_documents=len(request.document_ids))
    except Exception as e:
        logger.error(f"Error starting batch processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting batch processing: {str(e)}"
        )

@router.get("/executions/by-document/{document_id}", response_model=List[PipelineExecutionResponse])
async def get_executions_by_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pipeline executions for a specific document"""
    try:
        logger.info(f"Searching executions for document: {document_id}")
        
        # Build the query
        query = select(PipelineExecution).where(
            PipelineExecution.document_id == document_id
        )
        
        # Only the owner or admin can see the executions
        if current_user.role != "admin":
            query = query.where(PipelineExecution.user_id == current_user.id)
        
        # Execute the query
        result = await db.execute(query)
        executions = result.scalars().all()
        
        logger.info(f"Found {len(list(executions))} executions for document {document_id}")
        
        # Prepare response
        execution_responses = []
        for execution in executions:
            try:
                # Get the pipeline name
                pipeline_query = select(Pipeline).where(Pipeline.id == execution.pipeline_id)
                pipeline_result = await db.execute(pipeline_query)
                pipeline = pipeline_result.scalar_one_or_none()
                pipeline_name = pipeline.name if pipeline else "Unknown pipeline"
                
                # Format the response
                execution_dict = {
                    "id": str(execution.id),
                    "pipeline_id": str(execution.pipeline_id),
                    "pipeline_name": pipeline_name,
                    "document_id": str(execution.document_id),
                    "user_id": str(execution.user_id),
                    "status": execution.status.value if execution.status else "unknown",
                    "started_at": execution.started_at,
                    "completed_at": execution.completed_at,
                    "created_at": execution.created_at,
                    "updated_at": execution.updated_at,
                    "results": execution.results or {},
                    "result": execution.results or {},
                    "parameters": execution.parameters or {},
                    "error": execution.error_message,
                }
                
                execution_responses.append(execution_dict)
            except Exception as inner_e:
                logger.error(f"Error processing execution {execution.id}: {str(inner_e)}")
                # Continue with the next execution
        
        return execution_responses
        
    except Exception as e:
        logger.error(f"Error getting executions for document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting executions for document: {str(e)}"
        ) 