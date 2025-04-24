"""
Service for managing analysis scenarios and pipelines
"""
from typing import Dict, Any, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models.user import User
from database.models.document import Document
from database.models.analysis import (
    AnalysisScenario, 
    AnalysisPipeline, 
    RfpAnalysisPipeline,
    ProposalAnalysisPipeline,
    PipelineType
)   
from database.models.task import Task, TaskType, TaskStatus, TaskPriority
from database.models.analysis_document import PipelineDocument, DocumentRole

class AnalysisService:
    """Service for analysis scenarios and pipelines"""
    
    async def create_scenario(
        self, 
        db: AsyncSession, 
        name: str, 
        description: str, 
        user: User,
        metadata_config: Optional[Dict[str, Any]] = None
    ) -> AnalysisScenario:
        """
        Create a new analysis scenario
        
        Args:
            db: Database session
            name: Scenario name
            description: Scenario description
            user: User creating the scenario
            metadata_config: Additional configuration
            
        Returns:
            AnalysisScenario: Created scenario
        """
        scenario = AnalysisScenario(
            name=name,
            description=description,
            metadata_config=metadata_config or {},
            user_id=user.id
        )
        
        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)
        
        return scenario
    
    async def get_scenarios(
        self, 
        db: AsyncSession, 
        user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[AnalysisScenario]:
        """
        Get analysis scenarios
        
        Args:
            db: Database session
            user: User
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List[AnalysisScenario]: List of scenarios
        """
        query = select(AnalysisScenario)
        
        # Filter by user if not admin
        if user.role != "admin":
            query = query.where(AnalysisScenario.user_id == user.id)
        
        # Order by creation date descending
        query = query.order_by(AnalysisScenario.created_at.desc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_scenario(
        self, 
        db: AsyncSession, 
        scenario_id: uuid.UUID, 
        user: User
    ) -> Optional[AnalysisScenario]:
        """
        Get an analysis scenario by ID
        
        Args:
            db: Database session
            scenario_id: Scenario ID
            user: User
            
        Returns:
            Optional[AnalysisScenario]: Scenario or None if not found
        """
        query = select(AnalysisScenario).where(AnalysisScenario.id == scenario_id)
        
        # Filter by user if not admin
        if user.role != "admin":
            query = query.where(AnalysisScenario.user_id == user.id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def add_rfp_pipeline(
        self, 
        db: AsyncSession, 
        scenario_id: uuid.UUID, 
        document_ids: List[uuid.UUID], 
        user: User,
        task_manager
    ) -> RfpAnalysisPipeline:
        """
        Add an RFP analysis pipeline to a scenario with multiple documents
        
        Args:
            db: Database session
            scenario_id: Scenario ID
            document_ids: List of RFP document IDs to process
            user: User
            task_manager: Task manager
            
        Returns:
            RfpAnalysisPipeline: Created pipeline
        """
        # 1. Verify that the scenario exists
        scenario = await self.get_scenario(db, scenario_id, user)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found or no access")
        
        # 2. Verify that all documents exist
        if not document_ids:
            raise ValueError("At least one document must be provided")
            
        documents = []
        for doc_id in document_ids:
            result = await db.execute(
                select(Document).filter(Document.id == doc_id)
            )
            document = result.scalar_one_or_none()
            if not document:
                raise ValueError(f"Document {doc_id} not found")
            documents.append(document)
        
        # Use first document as principal document
        principal_document = documents[0]
        
        # 4. Create RFP analysis pipeline
        pipeline_id = uuid.uuid4()
        pipeline = RfpAnalysisPipeline(
            id=pipeline_id,
            scenario_id=scenario.id,
            principal_document_id=principal_document.id,
            pipeline_type=PipelineType.RFP_ANALYSIS
        )
        db.add(pipeline)
        await db.commit()
        await db.refresh(pipeline)
        
        # 5. Associate documents with pipeline using the many-to-many relationship
        from database.models.analysis_document import PipelineDocument, DocumentRole
        
        # Associate each document with the pipeline
        for idx, document in enumerate(documents):
            # First document is primary, rest are secondary
            doc_role = DocumentRole.PRIMARY if idx == 0 else DocumentRole.SECONDARY
            
            pipeline_document = PipelineDocument(
                pipeline_id=pipeline.id,
                document_id=document.id,
                role=doc_role,
                processing_order=idx  # Order by index
            )
            db.add(pipeline_document)
        
        await db.commit()
        
        # 6. Create task in the task system
        task_name = f"RFP Analysis of {principal_document.title} for scenario {scenario.name}"
        parameters = {
            "document_ids": [str(doc.id) for doc in documents],
            "pipeline_id": str(pipeline.id)
        }
        task = await task_manager.create_task(
            db=db,
            task_name=task_name,
            task_type=TaskType.RFP_ANALYSIS,
            parameters=parameters,
            source_type="analysis_pipeline",
            source_id=pipeline.id,
            priority=TaskPriority.NORMAL,
            user=user
        )
        
        # 6. Launch Celery task (versión asíncrona)
        from tasks.analysis.rfp_workflow_tasks import process_rfp_documents_async
        celery_task = process_rfp_documents_async.delay(
            document_ids=[str(doc.id) for doc in documents],
            pipeline_id=str(pipeline.id),
            user_id=str(user.id),
            task_id=str(task.id)
        )
        
        # 7. Update task with Celery ID
        await task_manager.update_task_celery_id(
            db=db,
            task_id=task.id,
            celery_task_id=celery_task.id
        )
        
        return pipeline
    
    async def add_proposal_pipeline(
        self, 
        db: AsyncSession, 
        scenario_id: uuid.UUID, 
        document_ids: List[uuid.UUID],
        rfp_pipeline_id: uuid.UUID,
        user: User,
        task_manager
    ) -> ProposalAnalysisPipeline:
        """
        Add a proposal analysis pipeline to a scenario with multiple documents
        
        Args:
            db: Database session
            scenario_id: Scenario ID
            documents: List of proposal documents to process
            rfp_pipeline_id: ID of the related RFP pipeline
            user: User
            task_manager: Task manager
            
        Returns:
            ProposalAnalysisPipeline: Created pipeline
        """
        # 1. Verify that the scenario exists
        scenario = await self.get_scenario(db, scenario_id, user)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found or no access")
        
        # 2. Verify that all documents exist
        if not document_ids:
            raise ValueError("At least one document must be provided")
            
        documents = []
        for doc_id in document_ids:
            result = await db.execute(
                select(Document).filter(Document.id == doc_id)
            )
            document = result.scalar_one_or_none()
            if not document:
                raise ValueError(f"Document {doc_id} not found")
            documents.append(document)
        
        # 3. Verify that the RFP pipeline exists
        result = await db.execute(
            select(RfpAnalysisPipeline).filter(RfpAnalysisPipeline.id == rfp_pipeline_id)
        )
        rfp_pipeline = result.scalar_one_or_none()
        if not rfp_pipeline:
            raise ValueError(f"RFP pipeline {rfp_pipeline_id} not found")
        
        # 4. Verify that the RFP pipeline belongs to the same scenario
        if rfp_pipeline.scenario_id != scenario.id:
            raise ValueError(f"The RFP pipeline does not belong to scenario {scenario.name}")
        
        # 4. Create the pipeline
        # El primer documento de la lista se considera el principal
        principal_document = documents[0] if documents else None
        if not principal_document:
            raise ValueError("No se pudo determinar el documento principal")
        
        pipeline = ProposalAnalysisPipeline(
            scenario_id=scenario_id,
            pipeline_type=PipelineType.PROPOSAL_ANALYSIS,
            referenced_rfp_id=rfp_pipeline.id,
            principal_document_id=principal_document.id  # Establecer el documento principal
        )
        
        db.add(pipeline)
        await db.flush()
        
        # 5. Associate all documents with the pipeline
        for i, document in enumerate(documents):
            # First document is primary, rest are secondary
            role = DocumentRole.PRIMARY if i == 0 else DocumentRole.SECONDARY
            
            pipeline_document = PipelineDocument(
                pipeline_id=pipeline.id,
                document_id=document.id,
                role=role,
                processing_order=i + 1  # Order based on position in list
            )
            
            db.add(pipeline_document)
        
        await db.flush()
        await db.refresh(pipeline_document)
        
        # 6. Create task in the task system
        primary_doc = documents[0]  # First document is considered primary for task naming
        task_name = f"Proposal Analysis of {primary_doc.title} and {len(documents)-1} additional documents"
        parameters = {
            "document_ids": [str(doc.id) for doc in documents],
            "pipeline_id": str(pipeline.id),
            "rfp_pipeline_id": str(rfp_pipeline_id)
        }
        task = await task_manager.create_task(
            db=db,
            task_name=task_name,
            task_type=TaskType.PROPOSAL_ANALYSIS,
            parameters=parameters,
            source_type="analysis_pipeline",
            source_id=pipeline.id,
            priority=TaskPriority.NORMAL,
            user=user
        )
        
        # 7. Launch Celery task (versión asíncrona)
        from tasks.analysis.proposal_workflow_tasks import process_proposal_documents_async
        celery_task = process_proposal_documents_async.delay(
            document_ids=[str(doc.id) for doc in documents],
            pipeline_id=str(pipeline.id),
            rfp_pipeline_id=str(rfp_pipeline_id),
            user_id=str(user.id),
            task_id=str(task.id)
        )
        
        # 8. Update task with Celery ID
        await task_manager.update_task_celery_id(
            db=db,
            task_id=task.id,
            celery_task_id=celery_task.id
        )
        
        return pipeline
    
    async def reprocess_pipeline(
        self,
        db: AsyncSession,
        pipeline_id: uuid.UUID,
        user: User,
        task_manager
    ) -> AnalysisPipeline:
        """
        Reprocess an existing pipeline
        
        Args:
            db: Database session
            pipeline_id: Pipeline ID
            user: User
            task_manager: Task manager
            
        Returns:
            AnalysisPipeline: Updated pipeline
        """
        # 1. Verify that the pipeline exists
        result = await db.execute(
            select(AnalysisPipeline).filter(AnalysisPipeline.id == pipeline_id)
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
            
        # 2. Reset pipeline status
        pipeline.status = "pending"
        pipeline.completed_at = None
        
        # 3. Get principal document for task name
        result = await db.execute(
            select(Document).filter(Document.id == pipeline.principal_document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise ValueError(f"Principal document not found for pipeline {pipeline_id}")
            
        # 4. Create task based on pipeline type
        if pipeline.pipeline_type == PipelineType.RFP_ANALYSIS:
            # 5. Create task for RFP analysis
            primary_doc = document  # First document is considered primary for task naming
            task_name = f"RFP Analysis of {primary_doc.title} (reprocessing)"
            parameters = {
                "document_ids": [str(doc.id) for doc in [document]],
                "pipeline_id": str(pipeline.id)
            }
            task = await task_manager.create_task(
                db=db,
                task_name=task_name,
                task_type=TaskType.RFP_ANALYSIS,
                parameters=parameters,
                source_type="analysis_pipeline",
                source_id=pipeline.id,
                priority=TaskPriority.NORMAL,
                user=user
            )
            
            # Launch Celery task (versión asíncrona)
            from tasks.analysis.rfp_workflow_tasks import process_rfp_documents_async
            celery_task = process_rfp_documents_async.delay(
                document_ids=[str(doc.id) for doc in [document]],
                pipeline_id=str(pipeline.id),
                user_id=str(user.id),
                task_id=str(task.id)
            )
            
        elif pipeline.pipeline_type == PipelineType.PROPOSAL_ANALYSIS:
            # Get RFP pipeline
            rfp_pipeline_id = pipeline.parent_pipeline_id
            if not rfp_pipeline_id:
                raise ValueError("Proposal pipeline has no associated RFP pipeline")
                
            # 6. Create task for proposal analysis
            primary_doc = document  # First document is considered primary for task naming
            task_name = f"Proposal Analysis of {primary_doc.title} (reprocessing)"
            parameters = {
                "document_ids": [str(doc.id) for doc in [document]],
                "pipeline_id": str(pipeline.id),
                "rfp_pipeline_id": str(rfp_pipeline_id)
            }
            task = await task_manager.create_task(
                db=db,
                task_name=task_name,
                task_type=TaskType.PROPOSAL_ANALYSIS,
                parameters=parameters,
                source_type="analysis_pipeline",
                source_id=pipeline.id,
                priority=TaskPriority.NORMAL,
                user=user
            )
            
            # Launch Celery task (versión asíncrona)
            from tasks.analysis.proposal_workflow_tasks import process_proposal_documents_async
            celery_task = process_proposal_documents_async.delay(
                document_ids=[str(doc.id) for doc in [document]],
                pipeline_id=str(pipeline.id),
                rfp_pipeline_id=str(rfp_pipeline_id),
                user_id=str(user.id),
                task_id=str(task.id)
            )
        else:
            raise ValueError(f"Unsupported pipeline type: {pipeline.pipeline_type}")
            
        # Update task with Celery ID
        await task_manager.update_task_celery_id(
            db=db,
            task_id=task.id,
            celery_task_id=celery_task.id
        )
        
        await db.commit()
        await db.refresh(pipeline)
        return pipeline
        
    async def delete_pipeline(
        self,
        db: AsyncSession,
        pipeline_id: uuid.UUID,
        user: User
    ) -> bool:
        """
        Delete a pipeline and its associated data
        
        Args:
            db: Database session
            pipeline_id: Pipeline ID
            user: User
            
        Returns:
            bool: True if deleted successfully
        """
        # 1. Verify that the pipeline exists
        result = await db.execute(
            select(AnalysisPipeline).filter(AnalysisPipeline.id == pipeline_id)
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
            
        # Ya no es necesario verificar pipelines hijos, ya que eliminamos la jerarquía padre-hijo
            
        # 3. Delete the pipeline (cascade will handle related entities)
        await db.delete(pipeline)
        await db.commit()
        
        return True
    
    async def get_pipelines(
        self, 
        db: AsyncSession, 
        scenario_id: uuid.UUID, 
        user: User,
        pipeline_type: Optional[PipelineType] = None
    ) -> List[AnalysisPipeline]:
        """
        Get pipelines for a scenario
        
        Args:
            db: Database session
            scenario_id: Scenario ID
            user: User
            pipeline_type: Filter by pipeline type
            
        Returns:
            List[AnalysisPipeline]: List of pipelines
        """
        # Verify that the scenario exists
        scenario = await self.get_scenario(db, scenario_id, user)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found or no access")
        
        # Get pipelines
        query = select(AnalysisPipeline).where(AnalysisPipeline.scenario_id == scenario_id)
        
        # Filter by pipeline type
        if pipeline_type:
            query = query.where(AnalysisPipeline.pipeline_type == pipeline_type)
        
        # Order by creation date
        query = query.order_by(AnalysisPipeline.created_at)
        
        result = await db.execute(query)
        return result.scalars().all()
