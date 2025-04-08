from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, delete
from sqlalchemy.orm import selectinload

from database.models.user import User
from database.models.pipeline import Pipeline, PipelineExecution, ExecutionStatus
from database.models.document import Document
from schemas.pipeline import PipelineConfigCreate, PipelineConfigUpdate, PipelineExecutionCreate
import logging

logger = logging.getLogger(__name__)

class PipelineService:
    # No __init__ needed if we pass db session to each method

    # --- Helper Method for Data Transformation ---
    def _process_pipeline_db_to_response_dict(self, pipeline: Pipeline) -> Dict[str, Any]:
        """Converts a Pipeline DB object to a dictionary suitable for response, processing steps."""
        pipeline_dict = {
            "id": pipeline.id,
            "name": pipeline.name,
            "description": pipeline.description,
            "type": pipeline.type,
            "user_id": pipeline.user_id,
            "created_at": pipeline.created_at,
            "updated_at": pipeline.updated_at,
            "config_metadata": {}
        }
        # Ensure steps is a list and each step has id and type
        if hasattr(pipeline, "steps") and pipeline.steps:
            pipeline_dict["steps"] = []
            for step in pipeline.steps:
                step_dict = dict(step) # Assume step is already dict-like from JSON
                if not step_dict.get("id"):
                    step_dict["id"] = step_dict.get("name") # Default id to name
                if not step_dict.get("type"):
                    step_dict["type"] = "processor" # Default type
                pipeline_dict["steps"].append(step_dict)
        else:
            pipeline_dict["steps"] = []
        # Ensure config_metadata is a dictionary
        if hasattr(pipeline, "config_metadata") and pipeline.config_metadata:
            if isinstance(pipeline.config_metadata, dict):
                pipeline_dict["config_metadata"] = pipeline.config_metadata
        return pipeline_dict

    # --- Configuration Methods ---
    async def create_pipeline(self, db: AsyncSession, pipeline_data: PipelineConfigCreate, user: User) -> Pipeline:
        """Creates a new pipeline configuration."""
        logger.info(f"Creating pipeline config '{pipeline_data.name}' for user {user.id}")
        steps = []
        if pipeline_data.steps:
            for step in pipeline_data.steps:
                step_dict = step.dict()
                if not step_dict.get("id"):
                    step_dict["id"] = step_dict.get("name")
                if not step_dict.get("type"):
                    step_dict["type"] = "processor"
                steps.append(step_dict)
        metadata = pipeline_data.metadata or {}

        db_pipeline = Pipeline(
            name=pipeline_data.name,
            description=pipeline_data.description,
            type=pipeline_data.type,
            steps=steps,
            config_metadata=metadata,
            user_id=user.id
        )
        db.add(db_pipeline)
        try:
            await db.commit()
            await db.refresh(db_pipeline)
            logger.info(f"Pipeline config '{db_pipeline.name}' created with ID {db_pipeline.id}")
            return db_pipeline
        except Exception as e:
            await db.rollback()
            logger.error(f"Database error creating pipeline config: {e}", exc_info=True)
            raise ValueError(f"Failed to create pipeline configuration: {e}")

    async def get_pipelines(self, db: AsyncSession, user: User, skip: int, limit: int, type_filter: Optional[str]) -> List[Pipeline]:
        """Gets a list of pipeline configurations for a user."""
        logger.info(f"Fetching pipeline configs for user {user.id}, skip={skip}, limit={limit}, type={type_filter}")
        query = select(Pipeline)
        if user.role != "admin":
            query = query.where(Pipeline.user_id == user.id)
        if type_filter:
            query = query.where(Pipeline.type == type_filter)
        query = query.offset(skip).limit(limit).order_by(desc(Pipeline.created_at))

        result = await db.execute(query)
        pipeline_configs = result.scalars().all()
        return list(pipeline_configs)

    async def get_pipeline(self, db: AsyncSession, pipeline_id: uuid.UUID, user: User) -> Optional[Pipeline]:
        """Gets a single pipeline configuration by ID, checking permissions."""
        logger.info(f"Fetching pipeline config {pipeline_id} for user {user.id}")
        query = select(Pipeline).where(Pipeline.id == pipeline_id)
        result = await db.execute(query)
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            return None

        if pipeline.user_id != user.id and user.role != "admin":
            logger.warning(f"User {user.id} permission denied for pipeline config {pipeline_id}")
            raise PermissionError("User does not have permission to view this configuration.")

        return pipeline

    async def update_pipeline(self, db: AsyncSession, pipeline_id: uuid.UUID, pipeline_data: PipelineConfigUpdate, user: User) -> Optional[Pipeline]:
        """Updates a pipeline configuration, checking permissions."""
        logger.info(f"Updating pipeline config {pipeline_id} for user {user.id}")
        query = select(Pipeline).where(Pipeline.id == pipeline_id)
        result = await db.execute(query)
        db_pipeline = result.scalar_one_or_none()

        if not db_pipeline:
            return None

        if db_pipeline.user_id != user.id and user.role != "admin":
            logger.warning(f"User {user.id} permission denied to update pipeline config {pipeline_id}")
            raise PermissionError("User does not have permission to modify this configuration.")

        update_data = pipeline_data.model_dump(exclude_unset=True)
        processed_steps = None # Store processed steps separately

        for key, value in update_data.items():
            if key == "metadata":
                 db_pipeline.config_metadata = value if isinstance(value, dict) else {}
            elif key == "steps":
                 processed_steps = []
                 if value:
                     for step in value:
                         step_dict = dict(step) # Assume step is dict-like
                         if not step_dict.get("id"):
                             step_dict["id"] = step_dict.get("name")
                         if not step_dict.get("type"):
                             step_dict["type"] = "processor"
                         processed_steps.append(step_dict)
                 # Assign processed steps outside the loop
            else:
                setattr(db_pipeline, key, value)

        # Assign processed steps if they were in the update data
        if processed_steps is not None:
             db_pipeline.steps = processed_steps

        try:
            await db.commit()
            await db.refresh(db_pipeline)
            logger.info(f"Pipeline config {pipeline_id} updated successfully.")
            return db_pipeline
        except Exception as e:
            await db.rollback()
            logger.error(f"Database error updating pipeline config {pipeline_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to update pipeline configuration: {e}")

    async def delete_pipeline(self, db: AsyncSession, pipeline_id: uuid.UUID, user: User) -> bool:
        """Deletes a pipeline configuration, checking permissions."""
        logger.info(f"Deleting pipeline config {pipeline_id} requested by user {user.id}")
        query = select(Pipeline).where(Pipeline.id == pipeline_id)
        result = await db.execute(query)
        db_pipeline = result.scalar_one_or_none()

        if not db_pipeline:
            return False

        if db_pipeline.user_id != user.id and user.role != "admin":
            logger.warning(f"User {user.id} permission denied to delete pipeline config {pipeline_id}")
            raise PermissionError("User does not have permission to delete this configuration.")

        # Using delete() method on the session
        await db.delete(db_pipeline)
        try:
            await db.commit()
            logger.info(f"Pipeline config {pipeline_id} deleted successfully.")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Database error deleting pipeline config {pipeline_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to delete pipeline configuration: {e}")

    # --- Pipeline Execution Management ---
    async def get_execution(self, db: AsyncSession, execution_id: uuid.UUID, user: User) -> Optional[PipelineExecution]:
        """Get an execution by ID"""
        result = await db.execute(
            select(PipelineExecution)
            .where(PipelineExecution.id == execution_id)
            .options(
                selectinload(PipelineExecution.pipeline),
                selectinload(PipelineExecution.document)
            )
        )
        execution = result.scalar_one_or_none()

        if not execution:
            return None

        # Permission Check
        if execution.user_id != user.id and user.role != "admin":
             logger.warning(f"User {user.id} permission denied for execution {execution_id}")
             raise PermissionError("User does not have permission to view this execution.")

        return execution

    async def get_executions_by_document(
        self,
        db: AsyncSession,
        pipeline_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        user: Optional[User] = None
    ) -> List[PipelineExecution]:
        """Get executions, filtered by document, pipeline, status, and user permissions."""
        query = select(PipelineExecution).options(
            selectinload(PipelineExecution.pipeline),
            selectinload(PipelineExecution.document)
        )

        conditions = []
        if pipeline_id:
            conditions.append(PipelineExecution.pipeline_id == pipeline_id)
        if document_id:
            conditions.append(PipelineExecution.document_id == document_id)
        if status:
            conditions.append(PipelineExecution.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        # Add user permission filter if user is provided and not admin
        if user and user.role != "admin":
            query = query.where(PipelineExecution.user_id == user.id)

        query = query.order_by(desc(PipelineExecution.created_at))
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def create_execution(self, db: AsyncSession, execution_data: PipelineExecutionCreate, user: User, task_id: Optional[str] = None) -> PipelineExecution:
        """Creates a new pipeline execution record."""
        # Verify pipeline exists (optional, depends if API does it)
        pipeline_check = await db.execute(select(Pipeline).where(Pipeline.id == execution_data.pipeline_id))
        if not pipeline_check.scalar_one_or_none():
            raise ValueError(f"Pipeline configuration with ID {execution_data.pipeline_id} not found.")

        execution = PipelineExecution(
            pipeline_id=execution_data.pipeline_id,
            document_id=execution_data.document_id,
            status=ExecutionStatus.PENDING,
            parameters=execution_data.parameters,
            user_id=user.id,
        )
        db.add(execution)
        try:
            await db.commit()
            await db.refresh(execution)
            logger.info(f"Created pipeline execution {execution.id} for doc {execution.document_id} and pipeline {execution.pipeline_id}")
            return execution
        except Exception as e:
            await db.rollback()
            logger.error(f"Database error creating pipeline execution: {e}", exc_info=True)
            raise ValueError(f"Failed to create pipeline execution: {e}")

    async def update_execution_status(
        self,
        db: AsyncSession,
        execution_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[PipelineExecution]:
        """Update the status of an execution"""
        result = await db.execute(select(PipelineExecution).where(PipelineExecution.id == execution_id))
        execution = result.scalar_one_or_none()
        if not execution:
            return None

        execution.status = status
        if status == "COMPLETED":
            execution.completed_at = datetime.utcnow()
        elif status == "FAILED":
            execution.completed_at = datetime.utcnow()
            execution.error_message = error_message

        await db.commit()
        await db.refresh(execution)
        return execution

    async def update_execution_results(
        self,
        db: AsyncSession,
        execution_id: uuid.UUID,
        results: Dict[str, Any]
    ) -> Optional[PipelineExecution]:
        """Update the results of an execution"""
        result = await db.execute(select(PipelineExecution).where(PipelineExecution.id == execution_id))
        execution = result.scalar_one_or_none()
        if not execution:
            return None

        execution.results = results
        execution.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(execution)
        return execution

    async def start_execution(
        self,
        db: AsyncSession,
        execution_id: uuid.UUID
    ) -> Optional[PipelineExecution]:
        """Mark an execution as started"""
        result = await db.execute(select(PipelineExecution).where(PipelineExecution.id == execution_id))
        execution = result.scalar_one_or_none()
        if not execution:
            return None

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()
        await db.commit()
        await db.refresh(execution)
        return execution

    async def cancel_execution(self, db: AsyncSession, execution_id: uuid.UUID, user: User) -> Optional[PipelineExecution]:
        """Sets execution status to CANCELED after permission checks."""
        logger.info(f"User {user.id} attempting to cancel execution {execution_id}")
        execution = await self.get_execution(db, execution_id, user)
        if not execution:
             return None

        if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            logger.warning(f"Attempt to cancel execution {execution_id} which is already in state {execution.status}")
            raise ValueError(f"Cannot cancel an execution in state {execution.status}")

        execution.status = ExecutionStatus.CANCELED
        execution.completed_at = datetime.utcnow()
        try:
            await db.commit()
            await db.refresh(execution)
            logger.info(f"Execution {execution_id} status set to CANCELED.")
            return execution
        except Exception as e:
            await db.rollback()
            logger.error(f"Database error canceling execution {execution_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to update execution status to canceled: {e}")

    # --- Batch Operations ---
    async def create_batch_executions(
        self,
        db: AsyncSession,
        pipeline_id: uuid.UUID,
        document_ids: List[uuid.UUID],
        user: User,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[PipelineExecution]:
        """Create multiple executions for a pipeline"""
        executions = []
        for doc_id in document_ids:
            exec_data = PipelineExecutionCreate(
                pipeline_id=pipeline_id,
                document_id=doc_id,
                parameters=parameters
            )
            execution = await self.create_execution(db, exec_data, user)
            executions.append(execution)
        return executions 