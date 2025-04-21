"""
Base classes for document analysis pipelines
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from uuid import UUID
from database.models.document import Document

class BasePipeline(ABC):
    """Base class for document analysis pipelines"""
    
    def __init__(self):
        self.context = {}

    
    @abstractmethod
    async def process(self, pipeline_id: UUID, document: Document) -> Dict[str, Any]:
        """
        Process a document and return the results
        
        Args:
            pipeline_id: ID of the analysis pipeline
            document: Document to process
            
        Returns:
            Dict[str, Any]: Processing results
        """
        pass
    
    def _cleanup_and_return(self, context):
        """Clean up resources and return the context"""
        # Common implementation to clean up resources
        return context
