"""
Task execution middleware for logging and performance tracking
"""
import logging
import time
import functools
import asyncio
from typing import Callable, Any

logger = logging.getLogger('tasks.middleware')

def log_task_execution(task_func):
    """
    Decorator to log task execution time and details
    
    Args:
        task_func: Celery task function to wrap
        
    Returns:
        Wrapped function with logging
    """
    @functools.wraps(task_func)
    def wrapper(*args, **kwargs):
        task_name = task_func.__name__
        start_time = time.time()
        task_id = None
        
        # Log task start
        arg_str = ", ".join([str(arg) for arg in args])
        kwarg_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        params = f"{arg_str}{', ' if arg_str and kwarg_str else ''}{kwarg_str}"
        logger.info(f"Starting task {task_name}({params})")
        
        try:
            # Execute the task
            result = task_func(*args, **kwargs)
            
            # Try to extract task ID if available
            if hasattr(result, 'id'):
                task_id = result.id
                
            # Log task completion
            elapsed = time.time() - start_time
            logger.info(f"Task {task_name} completed in {elapsed:.2f}s {f'(ID: {task_id})' if task_id else ''}")
            
            return result
        except Exception as e:
            # Log task failure
            elapsed = time.time() - start_time
            logger.error(f"Task {task_name} failed after {elapsed:.2f}s: {str(e)}", exc_info=True)
            raise
    
    return wrapper

def async_task_logging(async_func):
    """
    Decorator for async task functions to log execution time and details
    
    Args:
        async_func: Async function to wrap
        
    Returns:
        Wrapped async function with logging
    """
    @functools.wraps(async_func)
    async def wrapper(*args, **kwargs):
        func_name = async_func.__name__
        start_time = time.time()
        
        # Log function start
        arg_str = ", ".join([str(arg) for arg in args])
        kwarg_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        params = f"{arg_str}{', ' if arg_str and kwarg_str else ''}{kwarg_str}"
        logger.info(f"Starting async function {func_name}({params})")
        
        try:
            # Execute the function
            result = await async_func(*args, **kwargs)
            
            # Log function completion
            elapsed = time.time() - start_time
            logger.info(f"Async function {func_name} completed in {elapsed:.2f}s")
            
            return result
        except Exception as e:
            # Log function failure
            elapsed = time.time() - start_time
            logger.error(f"Async function {func_name} failed after {elapsed:.2f}s: {str(e)}", exc_info=True)
            raise
    
    return wrapper