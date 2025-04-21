"""
Celery worker initialization and shared components
"""
import logging
from celery import Celery
from celery.signals import task_prerun, task_success, task_failure, task_postrun

from core.config import settings
from tasks.base_tasks import update_task_status_sync

# Configure logging for Celery tasks
logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery("rocket_launch_tasks")
celery_app.conf.broker_url = settings.CELERY_BROKER_URL
celery_app.conf.result_backend = settings.CELERY_RESULT_BACKEND

# Load Celery config from settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100,
    task_track_started=True
)

# Configure Celery beat schedule
celery_app.conf.beat_schedule = {
    'cleanup-old-tasks': {
        'task': 'cleanup_old_tasks', 
        'schedule': 86400.0,  # every 24 hours
        'kwargs': {'days_to_keep': 7}
    },
    'system-health-check': {
        'task': 'system_health_check',
        'schedule': 3600.0,  # hourly
    }
}

# Task signals
@task_prerun.connect
def task_started(task_id, task, *args, **kwargs):
    """Signal handler for when a task starts"""
    logger.info(f"Task started: {task_id}")
    
    # Update task status in DB if possible (use try/except to avoid blocking the task)
    try:
        # Usar la función síncrona en lugar de asyncio
        update_task_status_sync(
            task_id=task_id,
            status="RUNNING"
        )
    except Exception as e:
        logger.error(f"Failed to update task status to RUNNING: {e}")

@task_success.connect
def task_completed(sender=None, result=None, **kwargs):
    """Signal handler for when a task completes successfully"""
    task_id = sender.request.id
    logger.info(f"Task completed successfully: {task_id}")
    
    # Update task status in DB
    try:
        # Usar la función síncrona en lugar de asyncio
        update_task_status_sync(
            task_id=task_id,
            status="COMPLETED",
            result=result
        )
    except Exception as e:
        logger.error(f"Failed to update task status to COMPLETED: {e}")

@task_failure.connect
def task_failed(sender=None, exception=None, **kwargs):
    """Signal handler for when a task fails"""
    task_id = sender.request.id
    logger.info(f"Task failed: {task_id}, Exception: {exception}")
    
    # Update task status in DB
    try:
        # Usar la función síncrona en lugar de asyncio
        update_task_status_sync(
            task_id=task_id,
            status="FAILED",
            error_message=str(exception)
        )
    except Exception as e:
        logger.error(f"Failed to update task status to FAILED: {e}")

@task_postrun.connect
def cleanup_task(sender=None, task_id=None, **kwargs):
    """Cleanup resources after task completes or fails"""
    # This is a good place to ensure resources are properly cleaned up
    # For example, close database connections, file handles, etc.
    pass

# Make Celery autodiscover tasks in the tasks package and its submodules
celery_app.autodiscover_tasks([
    'tasks',
    'tasks.analysis',
    'tasks.document',
    'tasks.batch'
], force=True)