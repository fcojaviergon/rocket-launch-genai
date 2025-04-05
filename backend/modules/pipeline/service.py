from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_
from sqlalchemy.orm import selectinload

from database.models.pipeline import Pipeline, PipelineExecution
from database.models.document import Document
from .executor import PipelineExecutor

class PipelineService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Pipeline Management ---
    async def get_pipeline(self, pipeline_id: uuid.UUID) -> Optional[Pipeline]:
        """Get a pipeline by ID"""
        result = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.id == pipeline_id)
            .options(selectinload(Pipeline.executions))
        )
        return result.scalar_one_or_none()

    async def get_pipelines(self, skip: int = 0, limit: int = 100) -> List[Pipeline]:
        """Get all pipelines with pagination"""
        result = await self.session.execute(
            select(Pipeline)
            .options(selectinload(Pipeline.executions))
            .offset(skip).limit(limit)
            .order_by(desc(Pipeline.created_at))
        )
        return list(result.scalars().all())

    async def create_pipeline(
        self, 
        name: str, 
        description: str, 
        processors_config: List[Dict[str, Any]]
    ) -> Pipeline:
        """Create a new pipeline"""
        pipeline = Pipeline(
            name=name,
            description=description,
            processors_config=processors_config,
            created_at=datetime.utcnow()
        )
        self.session.add(pipeline)
        await self.session.commit()
        await self.session.refresh(pipeline)
        return pipeline

    async def update_pipeline(
        self,
        pipeline_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        processors_config: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Pipeline]:
        """Update an existing pipeline"""
        pipeline = await self.get_pipeline(pipeline_id)
        if not pipeline:
            return None

        if name is not None:
            pipeline.name = name
        if description is not None:
            pipeline.description = description
        if processors_config is not None:
            pipeline.processors_config = processors_config
        
        pipeline.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(pipeline)
        return pipeline

    async def delete_pipeline(self, pipeline_id: uuid.UUID) -> bool:
        """Delete a pipeline"""
        pipeline = await self.get_pipeline(pipeline_id)
        if not pipeline:
            return False

        await self.session.delete(pipeline)
        await self.session.commit()
        return True

    # --- Pipeline Execution Management ---
    async def get_execution(self, execution_id: uuid.UUID) -> Optional[PipelineExecution]:
        """Get an execution by ID"""
        result = await self.session.execute(
            select(PipelineExecution)
            .where(PipelineExecution.id == execution_id)
            .options(
                selectinload(PipelineExecution.pipeline),
                selectinload(PipelineExecution.document)
            )
        )
        return result.scalar_one_or_none()

    async def get_executions(
        self,
        pipeline_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[PipelineExecution]:
        """Get executions with optional filters"""
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

        query = query.order_by(desc(PipelineExecution.created_at))
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_execution(
        self, 
        pipeline_id: uuid.UUID, 
        document_id: uuid.UUID
    ) -> PipelineExecution:
        """Create a new pipeline execution"""
        execution = PipelineExecution(
            pipeline_id=pipeline_id,
            document_id=document_id,
            status="PENDING",
            created_at=datetime.utcnow()
        )
        self.session.add(execution)
        await self.session.commit()
        await self.session.refresh(execution)
        return execution

    async def update_execution_status(
        self,
        execution_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[PipelineExecution]:
        """Update the status of an execution"""
        execution = await self.get_execution(execution_id)
        if not execution:
            return None

        execution.status = status
        if status == "COMPLETED":
            execution.completed_at = datetime.utcnow()
        elif status == "FAILED":
            execution.completed_at = datetime.utcnow()
            execution.error_message = error_message

        await self.session.commit()
        await self.session.refresh(execution)
        return execution

    async def update_execution_results(
        self,
        execution_id: uuid.UUID,
        results: Dict[str, Any]
    ) -> Optional[PipelineExecution]:
        """Update the results of an execution"""
        execution = await self.get_execution(execution_id)
        if not execution:
            return None

        execution.results = results
        execution.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(execution)
        return execution

    async def start_execution(
        self,
        execution_id: uuid.UUID
    ) -> Optional[PipelineExecution]:
        """Mark an execution as started"""
        execution = await self.get_execution(execution_id)
        if not execution:
            return None

        execution.status = "IN_PROGRESS"
        execution.started_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(execution)
        return execution

    # --- Batch Operations ---
    async def create_batch_executions(
        self,
        pipeline_id: uuid.UUID,
        document_ids: List[uuid.UUID]
    ) -> List[PipelineExecution]:
        """Create multiple executions for a pipeline"""
        executions = []
        for doc_id in document_ids:
            execution = await self.create_execution(pipeline_id, doc_id)
            executions.append(execution)
        return executions 