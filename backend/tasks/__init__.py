from .worker import celery_app

# Import task definitions from domain-specific modules
from .monitoring_tasks import monitor_batch_process, cleanup_old_tasks, system_health_check

# Import analysis tasks
from .analysis.rfp_tasks import process_rfp_document
from .analysis.proposal_tasks import process_proposal_document

# Import scheduler to ensure periodic tasks are registered
from . import scheduler

__all__ = [
    'celery_app',
    'process_rfp_document',
    'process_proposal_document',
    'monitor_batch_process',
    'cleanup_old_tasks',
    'system_health_check'
]
