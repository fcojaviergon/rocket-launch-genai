"""
Procesadores para el sistema de análisis

Este módulo contiene los procesadores utilizados por el sistema de análisis para:
- Procesamiento de documentos
- Generación de embeddings
- Análisis de RFP
- Análisis de propuestas
"""

from modules.analysis.processors.document_processor import DocumentProcessor
from modules.analysis.processors.embedding_processor import EmbeddingProcessor
from modules.analysis.processors.rfp_processor import RfpProcessor
from modules.analysis.processors.proposal_processor import ProposalProcessor

__all__ = [
    'DocumentProcessor',
    'EmbeddingProcessor',
    'RfpProcessor',
    'ProposalProcessor'
]
