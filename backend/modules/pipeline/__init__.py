"""
Módulo para la gestión de pipelines de procesamiento de documentos
"""

from modules.pipeline.executor import PipelineExecutor, create_processing_result
from modules.pipeline.processors import (
    TextExtractionProcessor, 
    SummarizerProcessor, 
    KeywordExtractionProcessor, 
    SentimentAnalysisProcessor,
    AVAILABLE_PROCESSORS,
    get_processor
)

__all__ = [
    "PipelineExecutor", 
    "create_processing_result",
    "TextExtractionProcessor", 
    "SummarizerProcessor", 
    "KeywordExtractionProcessor", 
    "SentimentAnalysisProcessor",
    "AVAILABLE_PROCESSORS",
    "get_processor"
]
