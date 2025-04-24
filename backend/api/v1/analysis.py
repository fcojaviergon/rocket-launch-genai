"""
API endpoints for analysis scenarios and pipelines
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.dependencies import get_db, get_current_user, get_task_manager
from database.models.user import User
from database.models.document import Document
from database.models.analysis import PipelineType, AnalysisPipeline
from database.models.analysis_document import PipelineDocument, DocumentRole
from modules.analysis.service import AnalysisService
from schemas.analysis import (
    AnalysisScenarioCreate,
    AnalysisScenarioResponse,
    AnalysisPipelineResponse,
    RfpAnalysisPipelineResponse,
    ProposalAnalysisPipelineResponse,
    RfpPipelineCreate,
    ProposalPipelineCreate,
    PipelineDocumentInfo
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
    """Add an RFP analysis pipeline to a scenario with multiple documents"""
    service = AnalysisService()
    
    try:
        pipeline = await service.add_rfp_pipeline(
            db=db,
            scenario_id=scenario_id,
            document_ids=pipeline.document_ids,
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
    """Add a proposal analysis pipeline to a scenario with multiple documents"""
    service = AnalysisService()
    
    try:
        pipeline = await service.add_proposal_pipeline(
            db=db,
            scenario_id=scenario_id,
            document_ids=pipeline.document_ids,
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
        
        # Transformar los objetos del modelo a los esquemas de respuesta
        response_pipelines = []
        for pipeline in pipelines:
            # Obtener los IDs de documentos asociados al pipeline
            doc_query = select(PipelineDocument.document_id).where(PipelineDocument.pipeline_id == pipeline.id)
            doc_result = await db.execute(doc_query)
            document_ids = [doc_id for doc_id, in doc_result.fetchall()]
            
            # Crear el objeto de respuesta según el tipo de pipeline
            if pipeline.pipeline_type == PipelineType.RFP_ANALYSIS:
                response_pipeline = RfpAnalysisPipelineResponse(
                    id=pipeline.id,
                    scenario_id=pipeline.scenario_id,
                    pipeline_type=pipeline.pipeline_type,
                    created_at=pipeline.created_at,
                    updated_at=pipeline.updated_at,
                    status=pipeline.status,
                    completed_at=pipeline.completed_at,
                    document_ids=document_ids,
                    results={} if pipeline.results is None else pipeline.results
                )
            elif pipeline.pipeline_type == PipelineType.PROPOSAL_ANALYSIS:
                response_pipeline = ProposalAnalysisPipelineResponse(
                    id=pipeline.id,
                    scenario_id=pipeline.scenario_id,
                    pipeline_type=pipeline.pipeline_type,
                    created_at=pipeline.created_at,
                    updated_at=pipeline.updated_at,
                    status=pipeline.status,
                    completed_at=pipeline.completed_at,
                    document_ids=document_ids,
                    results={} if pipeline.results is None else pipeline.results
                )
            else:
                # Tipo de pipeline genérico
                response_pipeline = AnalysisPipelineResponse(
                    id=pipeline.id,
                    scenario_id=pipeline.scenario_id,
                    pipeline_type=pipeline.pipeline_type,
                    created_at=pipeline.created_at,
                    updated_at=pipeline.updated_at,
                    status=pipeline.status,
                    completed_at=pipeline.completed_at,
                    document_ids=document_ids,
                    results={} if pipeline.results is None else pipeline.results
                )
            
            response_pipelines.append(response_pipeline)
        
        return response_pipelines
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting pipelines: {str(e)}")

@router.get("/pipelines/{pipeline_id}/documents", response_model=List[PipelineDocumentInfo])
async def get_pipeline_documents(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener todos los documentos asociados a un pipeline"""
    from sqlalchemy import select, join
    
    try:
        # Verificar que el pipeline existe
        pipeline_query = select(AnalysisPipeline).filter(AnalysisPipeline.id == pipeline_id)
        result = await db.execute(pipeline_query)
        pipeline = result.scalar_one_or_none()
        
        if not pipeline:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")
        
        # Obtener documentos asociados con join para eficiencia
        query = select(PipelineDocument, Document).join(
            Document, 
            PipelineDocument.document_id == Document.id
        ).filter(PipelineDocument.pipeline_id == pipeline_id)
        
        result = await db.execute(query)
        document_info = []
        
        for pd, doc in result:
            document_info.append(PipelineDocumentInfo(
                document_id=doc.id,
                title=doc.title,
                filename=doc.filename,
                role=pd.role.value,
                processing_order=pd.processing_order
            ))
        
        return document_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting documents: {str(e)}")

@router.post("/pipelines/{pipeline_id}/reprocess")
async def reprocess_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_manager = Depends(get_task_manager)
):
    """Reprocesar un pipeline existente"""
    service = AnalysisService()
    
    try:
        await service.reprocess_pipeline(
            db=db,
            pipeline_id=pipeline_id,
            user=current_user,
            task_manager=task_manager
        )
        
        return {"message": "Pipeline reprocessing started"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error reprocessing pipeline: {str(e)}")

@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Eliminar un pipeline y sus datos asociados"""
    service = AnalysisService()
    
    try:
        await service.delete_pipeline(
            db=db,
            pipeline_id=pipeline_id,
            user=current_user
        )
        
        return {"message": "Pipeline deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting pipeline: {str(e)}")

@router.get("/pipelines/{pipeline_id}/results")
async def get_pipeline_results(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener los resultados de un pipeline de análisis"""
    from sqlalchemy import select
    
    try:
        # Verificar que el pipeline existe
        pipeline_query = select(AnalysisPipeline).filter(AnalysisPipeline.id == pipeline_id)
        result = await db.execute(pipeline_query)
        pipeline = result.scalar_one_or_none()
        
        if not pipeline:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")
        
        # Obtener resultados del pipeline
        results = {
            "pipeline_id": str(pipeline.id),
            "pipeline_type": pipeline.pipeline_type.value if pipeline.pipeline_type else None,
            "created_at": pipeline.created_at.isoformat() if pipeline.created_at else None,
            "updated_at": pipeline.updated_at.isoformat() if pipeline.updated_at else None
        }
        
        # Agregar resultados específicos según el tipo de pipeline
        if pipeline.pipeline_type == PipelineType.RFP_ANALYSIS:
            results.update({
                "extracted_criteria": pipeline.extracted_criteria,
                "evaluation_framework": pipeline.evaluation_framework,
                "results": pipeline.results
            })
        elif pipeline.pipeline_type == PipelineType.PROPOSAL_ANALYSIS:
            results.update({
                "criteria_evaluations": pipeline.criteria_evaluations,
                "overall_score": pipeline.overall_score,
                "executive_summary": pipeline.executive_summary,
                "results": pipeline.results
            })
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting pipeline results: {str(e)}")
