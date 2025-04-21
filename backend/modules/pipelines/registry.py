"""
Registry for pipeline processors
"""
from typing import Dict, Any, Type
from modules.pipelines.base import BasePipeline
from modules.pipelines.rfp.processor import RfpPipeline
from modules.pipelines.proposal.processor import ProposalPipeline
from database.models.analysis import PipelineType

# Register pipeline processors
PIPELINE_PROCESSORS = {
    PipelineType.RFP_ANALYSIS: {
        "processor_class": RfpPipeline,
        "description": "Pipeline for RFP documents",
        "task_name": "process_rfp_document"
    },
    PipelineType.PROPOSAL_ANALYSIS: {
        "processor_class": ProposalPipeline,
        "description": "Pipeline for proposal documents",
        "task_name": "process_proposal_document"
    }
}

def register_processor(pipeline_type: PipelineType, processor_class: Type[BasePipeline]):
    """
    Register a processor class for a specific pipeline type
    
    Args:
        pipeline_type: Type of pipeline
        processor_class: Processor class
    """
    if pipeline_type not in PIPELINE_PROCESSORS:
        PIPELINE_PROCESSORS[pipeline_type] = {
            "processor_class": processor_class,
            "description": f"Pipeline for {pipeline_type.value}",
            "task_name": f"process_{pipeline_type.value}"
        }
    else:
        PIPELINE_PROCESSORS[pipeline_type]["processor_class"] = processor_class

def get_processor_class(pipeline_type: PipelineType) -> Type[BasePipeline]:
    """
    Get the processor class for a specific pipeline type
    
    Args:
        pipeline_type: Type of pipeline
        
    Returns:
        Type[BasePipeline]: Processor class
        
    Raises:
        ValueError: If the pipeline type is not supported or not registered
    """
    if pipeline_type not in PIPELINE_PROCESSORS:
        raise ValueError(f"Unsupported pipeline type: {pipeline_type}")
    
    processor_class = PIPELINE_PROCESSORS[pipeline_type]["processor_class"]
    if not processor_class:
        raise ValueError(f"Processor class for {pipeline_type} not registered")
    
    return processor_class

def get_processor_task_name(pipeline_type: PipelineType) -> str:
    """
    Get the Celery task name for a specific pipeline type
    
    Args:
        pipeline_type: Type of pipeline
        
    Returns:
        str: Celery task name
        
    Raises:
        ValueError: If the pipeline type is not supported
    """
    if pipeline_type not in PIPELINE_PROCESSORS:
        raise ValueError(f"Unsupported pipeline type: {pipeline_type}")
    
    return PIPELINE_PROCESSORS[pipeline_type]["task_name"]
