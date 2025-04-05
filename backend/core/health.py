"""
Health check module for the application.
Provides functions to check the health of various components.
"""
import asyncio
import time
import os
import platform
import logging
from typing import Dict, Any, List, Optional
import psutil
import asyncpg
from sqlalchemy import text

from core.logging_config import get_logger
from core.config import settings
from database.session import get_db

logger = get_logger("app.health")

async def check_database_connection() -> Dict[str, Any]:
    """
    Check if the database connection is healthy
    
    Returns:
        Dict with status and connection details
    """
    start_time = time.time()
    result = {
        "component": "database",
        "status": "unknown",
        "response_time_ms": 0,
        "details": {}
    }
    
    try:
        # Get database session
        async for session in get_db():
            # Simple query to check connection - use SQLAlchemy text() function
            await session.execute(text("SELECT 1"))
            
            # Get connection pool statistics
            # This assumes SQLAlchemy is using an asyncpg pool
            if hasattr(session, "bind") and hasattr(session.bind, "pool"):
                pool = session.bind.pool
                if pool:
                    result["details"]["pool_size"] = pool.size
                    result["details"]["pool_overflow"] = pool.overflow
                    result["details"]["pool_timeout"] = pool.timeout
            
            # Calculate response time
            result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
            result["status"] = "healthy"
            
            # Close the session
            await session.close()
            break
            
    except Exception as e:
        result["status"] = "unhealthy"
        result["details"]["error"] = str(e)
        result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Database health check failed: {str(e)}", exc_info=True)
        
    return result

async def check_redis_connection() -> Dict[str, Any]:
    """
    Check if Redis connection is healthy
    
    Returns:
        Dict with status and connection details
    """
    start_time = time.time()
    result = {
        "component": "redis",
        "status": "unknown",
        "response_time_ms": 0,
        "details": {}
    }
    
    try:
        import redis.asyncio as redis
        redis_url = settings.REDIS_URL
        
        # Create Redis client
        redis_client = redis.from_url(redis_url)
        
        # Perform ping to check connection
        ping_response = await redis_client.ping()
        
        # Close connection
        await redis_client.close()
        
        # Calculate response time
        result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if ping_response:
            result["status"] = "healthy"
        else:
            result["status"] = "unhealthy"
            result["details"]["error"] = "Redis ping failed"
            
    except ImportError:
        result["status"] = "skipped"
        result["details"]["error"] = "Redis client not available"
        
    except Exception as e:
        result["status"] = "unhealthy"
        result["details"]["error"] = str(e)
        result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Redis health check failed: {str(e)}", exc_info=True)
        
    return result

def check_system_resources() -> Dict[str, Any]:
    """
    Check system resources (CPU, memory, disk)
    
    Returns:
        Dict with system resource information
    """
    result = {
        "component": "system",
        "status": "healthy",
        "details": {}
    }
    
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Platform information
        result["details"]["platform"] = platform.platform()
        result["details"]["python_version"] = platform.python_version()
        
        # Add resource usage
        result["details"]["cpu_percent"] = cpu_percent
        result["details"]["memory_percent"] = memory_percent
        result["details"]["disk_percent"] = disk_percent
        
        # Set status based on resource usage
        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
            result["status"] = "warning"
            
        if cpu_percent > 95 or memory_percent > 95 or disk_percent > 95:
            result["status"] = "critical"
            
    except Exception as e:
        result["status"] = "unknown"
        result["details"]["error"] = str(e)
        logger.error(f"System resource check failed: {str(e)}", exc_info=True)
        
    return result

async def check_celery_workers() -> Dict[str, Any]:
    """
    Check if Celery workers are running and responding
    
    Returns:
        Dict with status and worker details
    """
    start_time = time.time()
    result = {
        "component": "celery",
        "status": "unknown",
        "response_time_ms": 0,
        "details": {}
    }
    
    try:
        from tasks.worker import celery_app
        
        # Inspect workers
        i = celery_app.control.inspect()
        
        # Get list of active workers
        active_workers = i.active()
        
        # Calculate response time
        result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if active_workers:
            result["status"] = "healthy"
            result["details"]["active_workers"] = len(active_workers)
            result["details"]["worker_names"] = list(active_workers.keys())
        else:
            result["status"] = "unhealthy"
            result["details"]["error"] = "No active Celery workers found"
            
    except ImportError:
        result["status"] = "skipped"
        result["details"]["error"] = "Celery not available"
        
    except Exception as e:
        result["status"] = "unhealthy"
        result["details"]["error"] = str(e)
        result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Celery worker check failed: {str(e)}", exc_info=True)
        
    return result

async def comprehensive_health_check() -> Dict[str, Any]:
    """
    Run a comprehensive health check of all system components
    
    Returns:
        Dict with overall status and component details
    """
    # Get start time
    start_time = time.time()
    
    # Run all checks concurrently
    db_check, redis_check, celery_check = await asyncio.gather(
        check_database_connection(),
        check_redis_connection(),
        check_celery_workers(),
        return_exceptions=True
    )
    
    # Run synchronous checks
    system_check = check_system_resources()
    
    # Convert exceptions to error responses
    if isinstance(db_check, Exception):
        db_check = {
            "component": "database",
            "status": "error",
            "details": {"error": str(db_check)}
        }
        
    if isinstance(redis_check, Exception):
        redis_check = {
            "component": "redis",
            "status": "error",
            "details": {"error": str(redis_check)}
        }
        
    if isinstance(celery_check, Exception):
        celery_check = {
            "component": "celery",
            "status": "error",
            "details": {"error": str(celery_check)}
        }
    
    # Collect all checks
    checks = [db_check, redis_check, system_check, celery_check]
    
    # Determine overall status
    # If any critical component is unhealthy, the overall status is unhealthy
    # Database must be healthy
    critical_components = ["database"]
    
    overall_status = "healthy"
    
    for check in checks:
        component = check.get("component")
        status = check.get("status")
        
        if component in critical_components and status != "healthy":
            overall_status = "unhealthy"
            break
            
        if status == "critical":
            overall_status = "critical"
            
        if status == "warning" and overall_status != "unhealthy" and overall_status != "critical":
            overall_status = "warning"
    
    # Calculate total response time
    response_time = round((time.time() - start_time) * 1000, 2)
    
    # Build response
    result = {
        "status": overall_status,
        "response_time_ms": response_time,
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "components": checks
    }
    
    # Log health check results
    log_level = logging.WARNING if overall_status != "healthy" else logging.INFO
    logger.log(log_level, f"Health check: {overall_status}", extra={"health": result})
    
    return result 