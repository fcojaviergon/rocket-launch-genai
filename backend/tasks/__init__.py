from .worker import celery_app

# Import task definitions from domain-specific modules
from .monitoring_tasks import monitor_batch_process, cleanup_old_tasks, system_health_check

# Import analysis tasks (nuevas tareas asíncronas)
from .analysis.proposal_workflow_tasks import process_proposal_documents_async
from .analysis.rfp_workflow_tasks import process_rfp_documents_async
from .analysis.document_processing_tasks import process_document_content
from .analysis.document_combination_tasks import combine_document_results
from .analysis.rfp_analysis_tasks import analyze_rfp_content
from .analysis.proposal_analysis_tasks import analyze_proposal_content

__all__ = [
    'celery_app',
    # Tareas asíncronas de análisis
    'process_document_content',
    'combine_document_results',
    'analyze_rfp_content',
    'process_proposal_documents_async',
    'analyze_proposal_content',
    'process_rfp_documents_async',
    # Tareas de monitoreo
    'monitor_batch_process',
    'cleanup_old_tasks',
    'system_health_check'
]
