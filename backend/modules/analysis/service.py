"""
Service for managing analysis scenarios and pipelines
"""
from typing import Dict, Any, List, Optional
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
from modules.pipelines.registry import get_processor_class

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
        document_id: uuid.UUID, 
        user: User,
        task_manager
    ) -> RfpAnalysisPipeline:
        """
        Add an RFP analysis pipeline to a scenario
        
        Args:
            db: Database session
            scenario_id: Scenario ID
            document_id: RFP document ID
            user: User
            task_manager: Task manager
            
        Returns:
            RfpAnalysisPipeline: Created pipeline
        """
        # 1. Verify that the scenario exists
        scenario = await self.get_scenario(db, scenario_id, user)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found or no access")
        
        # 2. Verify that the document exists
        result = await db.execute(
            select(Document).filter(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Create RFP analysis pipeline directly
        pipeline_id = uuid.uuid4()
        pipeline = RfpAnalysisPipeline(
            id=pipeline_id,
            scenario_id=scenario.id,
            document_id=document.id,
            pipeline_type=PipelineType.RFP_ANALYSIS
        )
        db.add(pipeline)
        await db.commit()
        await db.refresh(pipeline)
        
        # 5. Create task in the task system
        task_name = f"RFP Analysis of {document.title} for scenario {scenario.name}"
        parameters = {
            "document_id": str(document.id),
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
        
        # 6. Launch Celery task
        from tasks.analysis.rfp_tasks import process_rfp_document
        celery_task = process_rfp_document.delay(
            document_id=str(document.id),
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
        document_id: uuid.UUID,
        rfp_pipeline_id: uuid.UUID,
        user: User,
        task_manager
    ) -> ProposalAnalysisPipeline:
        """
        Add a proposal analysis pipeline to a scenario
        
        Args:
            db: Database session
            scenario_id: Scenario ID
            document_id: Proposal document ID
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
        
        # 2. Verify that the document exists
        result = await db.execute(
            select(Document).filter(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
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
        
        # Create proposal analysis pipeline directly
        pipeline_id = uuid.uuid4()
        pipeline = ProposalAnalysisPipeline(
            id=pipeline_id,
            scenario_id=scenario.id,
            document_id=document.id,
            pipeline_type=PipelineType.PROPOSAL_ANALYSIS,
            parent_pipeline_id=rfp_pipeline.id
        )
        db.add(pipeline)
        await db.commit()
        await db.refresh(pipeline)
        
        # 7. Create task in the task system
        task_name = f"Proposal Analysis of {document.title} for scenario {scenario.name}"
        parameters = {
            "document_id": str(document.id),
            "pipeline_id": str(pipeline.id),
            "rfp_pipeline_id": str(rfp_pipeline.id)
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
        
        # 8. Launch Celery task
        from tasks.analysis.proposal_tasks import process_proposal_document
        celery_task = process_proposal_document.delay(
            document_id=str(document.id),
            pipeline_id=str(pipeline.id),
            rfp_pipeline_id=str(rfp_pipeline.id),
            user_id=str(user.id),
            task_id=str(task.id)
        )
        
        # 9. Update task with Celery ID
        await task_manager.update_task_celery_id(
            db=db,
            task_id=task.id,
            celery_task_id=celery_task.id
        )
        
        return pipeline
    
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
