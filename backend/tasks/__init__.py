from .worker import celery_app

# Import task definitions to ensure proper registration
from .tasks import execute_pipeline, monitor_batch_process, test_task

__all__ = ['celery_app', 'execute_pipeline', 'monitor_batch_process', 'test_task']
