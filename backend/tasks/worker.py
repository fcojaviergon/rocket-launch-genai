"""
Celery worker initialization and shared components
"""
import logging
import asyncio
from celery import Celery
from celery.signals import task_prerun, task_success, task_failure, task_postrun

from core.config import settings

# Use redis-py instead of aioredis to avoid the TimeoutError conflict
import redis

# Configure logging for Celery tasks
logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery("rocket_launch_tasks")
celery_app.conf.broker_url = settings.CELERY_BROKER_URL
celery_app.conf.result_backend = settings.CELERY_RESULT_BACKEND

# Use Celery's autodiscover_tasks to find and register all tasks
celery_app.autodiscover_tasks([
    'tasks',
    'tasks.analysis',
    'tasks.monitoring_tasks',
    'tasks.analysis.document_processing_tasks',
    'tasks.analysis.document_combination_tasks',
    'tasks.analysis.rfp_analysis_tasks',
    'tasks.analysis.proposal_analysis_tasks',
    'tasks.analysis.rfp_workflow_tasks',
    'tasks.analysis.proposal_workflow_tasks',
], force=True)

logger.info("All task modules discovered and registered with Celery")

# Configurar redis como broker para soporte asíncrono
celery_app.conf.broker_transport_options = {'global_keyprefix': 'rocket_launch:'}

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
    task_track_started=True,
    # Configuración para soporte asíncrono
    worker_pool="solo",  # Usar solo pool para soporte de async/await
    task_cls="tasks.base_tasks:AsyncTask"  # Clase base para tareas asíncronas
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
        # Import here to avoid circular imports
        from tasks.base_tasks import update_task_status_sync
        
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(update_task_status_sync(
                task_id=task_id,
                status="RUNNING"
            ))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Failed to update task status to RUNNING: {e}")

@task_success.connect
def task_completed(sender=None, result=None, **kwargs):
    """Signal handler for when a task completes successfully"""
    task_id = sender.request.id
    logger.info(f"Task completed successfully: {task_id}")
    
    # Update task status in DB
    try:
        # Import here to avoid circular imports
        from tasks.base_tasks import update_task_status_sync
        
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(update_task_status_sync(
                task_id=task_id,
                status="COMPLETED",
                result=result
            ))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Failed to update task status to COMPLETED: {e}")

@task_failure.connect
def task_failed(sender=None, exception=None, **kwargs):
    """Signal handler for when a task fails"""
    task_id = sender.request.id
    logger.info(f"Task failed: {task_id}, Exception: {exception}")
    
    # Update task status in DB
    try:
        # Import here to avoid circular imports
        from tasks.base_tasks import update_task_status_sync
        
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(update_task_status_sync(
                task_id=task_id,
                status="FAILED",
                error_message=str(exception)
            ))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Failed to update task status to FAILED: {e}")

@task_postrun.connect
def cleanup_task(sender=None, task_id=None, **kwargs):
    """Cleanup resources after task completes or fails"""
    # This is a good place to ensure resources are properly cleaned up
    # For example, close database connections, file handles, etc.
    pass