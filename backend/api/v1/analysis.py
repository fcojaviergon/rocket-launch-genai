"""
API endpoints for analysis scenarios and pipelines
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db, get_current_user, get_task_manager
from database.models.user import User
from database.models.analysis import PipelineType
from modules.analysis.service import AnalysisService
from schemas.analysis import (
    AnalysisScenarioCreate,
    AnalysisScenarioResponse,
    AnalysisPipelineResponse,
    RfpAnalysisPipelineResponse,
    ProposalAnalysisPipelineResponse,
    RfpPipelineCreate,
    ProposalPipelineCreate
)

router = APIRouter()

@router.post("/scenarios", response_model=AnalysisScenarioResponse)
async def create_analysis_scenario(
    scenario: AnalysisScenarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new analysis scenario"""
    service = AnalysisService()
    
    try:
        created_scenario = await service.create_scenario(
            db=db,
            name=scenario.name,
            description=scenario.description,
            user=current_user,
            metadata_config=scenario.metadata_config
        )
        
        return created_scenario
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating scenario: {str(e)}")

@router.get("/scenarios", response_model=List[AnalysisScenarioResponse])
async def get_analysis_scenarios(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analysis scenarios"""
    service = AnalysisService()
    
    try:
        scenarios = await service.get_scenarios(
            db=db,
            user=current_user,
            skip=skip,
            limit=limit
        )
        
        return scenarios
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting scenarios: {str(e)}")

@router.get("/scenarios/{scenario_id}", response_model=AnalysisScenarioResponse)
async def get_analysis_scenario(
    scenario_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get an analysis scenario by ID"""
    service = AnalysisService()
    
    try:
        scenario = await service.get_scenario(
            db=db,
            scenario_id=scenario_id,
            user=current_user
        )
        
        if not scenario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        
        return scenario
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting scenario: {str(e)}")

@router.post("/scenarios/{scenario_id}/rfp", response_model=RfpAnalysisPipelineResponse)
async def add_rfp_pipeline(
    scenario_id: UUID,
    pipeline: RfpPipelineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_manager = Depends(get_task_manager)
):
    """Add an RFP analysis pipeline to a scenario"""
    service = AnalysisService()
    
    try:
        pipeline = await service.add_rfp_pipeline(
            db=db,
            scenario_id=scenario_id,
            document_id=pipeline.document_id,
            user=current_user,
            task_manager=task_manager
        )
        
        return pipeline
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error adding RFP pipeline: {str(e)}")

@router.post("/scenarios/{scenario_id}/proposal", response_model=ProposalAnalysisPipelineResponse)
async def add_proposal_pipeline(
    scenario_id: UUID,
    pipeline: ProposalPipelineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_manager = Depends(get_task_manager)
):
    """Add a proposal analysis pipeline to a scenario"""
    service = AnalysisService()
    
    try:
        pipeline = await service.add_proposal_pipeline(
            db=db,
            scenario_id=scenario_id,
            document_id=pipeline.document_id,
            rfp_pipeline_id=pipeline.rfp_pipeline_id,
            user=current_user,
            task_manager=task_manager
        )
        
        return pipeline
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error adding proposal pipeline: {str(e)}")

@router.get("/scenarios/{scenario_id}/pipelines", response_model=List[AnalysisPipelineResponse])
async def get_scenario_pipelines(
    scenario_id: UUID,
    pipeline_type: Optional[PipelineType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pipelines for a scenario"""
    service = AnalysisService()
    
    try:
        pipelines = await service.get_pipelines(
            db=db,
            scenario_id=scenario_id,
            user=current_user,
            pipeline_type=pipeline_type
        )
        
        return pipelines
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting pipelines: {str(e)}")
