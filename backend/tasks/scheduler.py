"""
Task scheduler for periodic maintenance tasks
"""
import logging
from datetime import datetime, timedelta
from celery.schedules import crontab

from .worker import celery_app
from .monitoring_tasks import cleanup_old_tasks, system_health_check

logger = logging.getLogger('tasks.scheduler')

# Define schedules for periodic tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Set up periodic tasks to run on a schedule
    
    Args:
        sender: The Celery app
    """
    logger.info("Setting up periodic tasks...")
    
    # Run cleanup of old tasks every day at 2:00 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0),  # Run at 2:00 AM
        cleanup_old_tasks.s(days_to_keep=30),
        name='cleanup-old-tasks-daily'
    )
    
    # Run system health check every 30 minutes
    sender.add_periodic_task(
        timedelta(minutes=30),  # Run every 30 minutes
        system_health_check.s(),
        name='system-health-check'
    )
    
    logger.info("Periodic tasks have been scheduled")