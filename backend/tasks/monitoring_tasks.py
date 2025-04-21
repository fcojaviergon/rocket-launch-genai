"""
Monitoring and batch processing tasks
"""
import logging
import time
import uuid
import asyncio
from typing import Dict, Any, List

from .worker import celery_app
from .base_tasks import run_async_task

from database.session import get_async_session_context

from datetime import datetime

logger = logging.getLogger('tasks.monitoring')

@celery_app.task(name="monitor_batch_process")
def monitor_batch_process(batch_id: str, execution_ids: List[str]):
    """
    Monitors the progress of a batch process of documents
    
    Args:
        batch_id (str): ID of the batch process
        execution_ids (list): List of execution IDs to monitor
    
    Returns:
        dict: Status of the monitoring
    """
    logger.info(f"Monitoring batch process {batch_id} with {len(execution_ids)} executions")
    
    # Use the run_async_task utility to execute the async function
    result = run_async_task(
        _monitor_batch_process_async,
        batch_id,
        execution_ids
    )
    
    # Add batch_id to result for tracking
    result["batch_id"] = batch_id
    result["total_executions"] = len(execution_ids)
    
    return result

@celery_app.task(name="cleanup_old_tasks")
def cleanup_old_tasks(days_to_keep: int = 30):
    """
    Cleans up old task records from the database
    
    Args:
        days_to_keep: Number of days of task history to retain
        
    Returns:
        dict: Cleanup results
    """
    logger.info(f"Starting cleanup of tasks older than {days_to_keep} days")
    
    # Use the run_async_task utility to execute the async function
    result = run_async_task(
        _cleanup_old_tasks_async,
        days_to_keep
    )
    
    return result

async def _cleanup_old_tasks_async(days_to_keep: int = 30):
    """
    Async helper for cleaning up old task records
    
    Args:
        days_to_keep: Number of days of task history to retain
        
    Returns:
        dict: Cleanup results with counts
    """
    from database.models.task import Task
    from sqlalchemy import delete, and_, or_, func
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    logger.info(f"[Async Cleanup] Removing tasks created before {cutoff_date}")
    
    try:
        async with get_async_session_context() as session:
            # Get count before deletion for reporting
            count_query = func.count(Task.id).select().where(
                and_(
                    Task.created_at < cutoff_date,
                    or_(
                        Task.status == "completed",
                        Task.status == "failed",
                        Task.status == "canceled"
                    )
                )
            )
            result = await session.execute(count_query)
            count_to_delete = result.scalar() or 0
            
            if count_to_delete == 0:
                logger.info("[Async Cleanup] No old tasks to delete")
                return {
                    "status": "success",
                    "deleted_count": 0,
                    "message": "No old tasks found to delete"
                }
            
            # Delete old completed, failed, or canceled tasks
            delete_stmt = delete(Task).where(
                and_(
                    Task.created_at < cutoff_date,
                    or_(
                        Task.status == "completed",
                        Task.status == "failed", 
                        Task.status == "canceled"
                    )
                )
            )
            
            result = await session.execute(delete_stmt)
            await session.commit()
            
            logger.info(f"[Async Cleanup] Successfully deleted {count_to_delete} old tasks")
            
            return {
                "status": "success", 
                "deleted_count": count_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "message": f"Successfully deleted {count_to_delete} old tasks"
            }
            
    except Exception as e:
        logger.error(f"[Async Cleanup] Error cleaning up old tasks: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Cleanup failed: {str(e)}"
        }

@celery_app.task(name="system_health_check")
def system_health_check():
    """
    Performs a health check of the system components
    
    Returns:
        dict: Health check results
    """
    logger.info(f"Starting system health check")
    
    # Use the run_async_task utility
    result = run_async_task(_system_health_check_async)
    
    return result

async def _system_health_check_async():
    """
    Async helper for system health checks
    
    Returns:
        dict: Health check results for various components
    """
    from core.health import check_database, check_celery_workers, check_redis, check_llm_service
    
    logger.info("[Health Check] Running system component checks")
    
    try:
        # Run all health checks in parallel
        db_check = check_database()
        celery_check = check_celery_workers()
        redis_check = check_redis()
        llm_check = check_llm_service()
        
        # Wait for all checks to complete
        db_result = await db_check
        celery_result = await celery_check
        redis_result = await redis_check
        llm_result = await llm_check
        
        # Calculate overall system status
        components_status = [
            db_result["status"],
            celery_result["status"],
            redis_result["status"],
            llm_result["status"]
        ]
        
        if all(status == "healthy" for status in components_status):
            overall_status = "healthy"
        elif any(status == "unhealthy" for status in components_status):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
            
        # Compile results
        health_result = {
            "status": "success",
            "system_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": db_result,
                "celery": celery_result,
                "redis": redis_result,
                "llm_service": llm_result
            }
        }
        
        logger.info(f"[Health Check] System status: {overall_status}")
        return health_result
        
    except Exception as e:
        logger.error(f"[Health Check] Error running health checks: {e}", exc_info=True)
        return {
            "status": "error",
            "system_status": "unknown",
            "error": f"Health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }