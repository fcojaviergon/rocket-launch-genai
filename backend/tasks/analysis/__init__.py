"""
Módulo de tareas de análisis
"""

# Importar explícitamente las tareas para que Celery las descubra
# Tareas de procesamiento de documentos
from tasks.analysis.document_processing_tasks import (
    process_document_content
)

# Tareas de combinación de documentos
from tasks.analysis.document_combination_tasks import (
    combine_document_results
)

# Tareas de análisis de RFP
from tasks.analysis.rfp_analysis_tasks import (
    analyze_rfp_content
)

# Tareas de flujo de trabajo de RFP
from tasks.analysis.rfp_workflow_tasks import (
    process_rfp_documents
)

# Tareas de análisis de propuestas
from tasks.analysis.proposal_analysis_tasks import (
    analyze_proposal_content
)

# Tareas de flujo de trabajo de propuestas
from tasks.analysis.proposal_workflow_tasks import (
    process_proposal_documents
)

__all__ = [
    'process_rfp_documents',
    'process_document_content',
    'combine_document_results',
    'analyze_rfp_content',
    'process_proposal_documents',
    'analyze_proposal_content'
]