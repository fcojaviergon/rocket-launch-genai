"""
Base utilities for Celery tasks
"""
import logging
import time
import asyncio
import json
from datetime import datetime
import uuid
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar, Union, List, Type
from functools import wraps

from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_async_session_context

logger = logging.getLogger('tasks.base')

# Tipo para resultados de las tareas
T = TypeVar('T')

def run_async_task(
    async_func: Callable[..., Awaitable[Dict[str, Any]]], 
    *args, 
    **kwargs
) -> Dict[str, Any]:
    """
    Utility to run an asynchronous function in a Celery task
    
    Args:
        async_func: Asynchronous function to run
        *args: Positional arguments for the async function
        **kwargs: Keyword arguments for the async function
        
    Returns:
        Dict[str, Any]: Result of the async function or error information
    """
    start_time = time.time()
    task_name = async_func.__name__
    
    try:
        logger.info(f"Running async function {task_name}")
        # Crear un nuevo event loop en lugar de intentar obtener uno existente
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            # Cerrar el loop al terminar
            loop.close()
        
        elapsed = time.time() - start_time
        logger.info(f"Async function {task_name} completed in {elapsed:.2f}s")
        
        # Ensure we have a status in the result
        if not isinstance(result, dict):
            result = {"result": result, "status": "success"}
        elif "status" not in result:
            result["status"] = "success"
            
        result["elapsed_time"] = elapsed
        return result
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Async function {task_name} failed after {elapsed:.2f}s: {str(e)}", exc_info=True)
        
        return {
            "status": "error",
            "error": str(e),
            "elapsed_time": elapsed
        }

def run_sync_task(
    func: Callable[..., T],
    *args,
    **kwargs
) -> Dict[str, Any]:
    """
    Utility to run a synchronous function in a Celery task.
    This is preferred over run_async_task to avoid event loop issues.
    
    Args:
        func: Synchronous function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Dict[str, Any]: Result of the function or error information
    """
    start_time = time.time()
    task_name = func.__name__
    
    try:
        logger.info(f"Running sync function {task_name}")
        result = func(*args, **kwargs)
        
        elapsed = time.time() - start_time
        logger.info(f"Sync function {task_name} completed in {elapsed:.2f}s")
        
        # Ensure we have a status in the result
        if not isinstance(result, dict):
            result = {"result": result, "status": "success"}
        elif "status" not in result:
            result["status"] = "success"
            
        result["elapsed_time"] = elapsed
        return result
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Sync function {task_name} failed after {elapsed:.2f}s: {str(e)}", exc_info=True)
        
        return {
            "status": "error",
            "error": str(e),
            "elapsed_time": elapsed
        }

# Agregar una función para obtener una sesión síncrona
def get_sync_session():
    """
    Get a synchronous database session for use in Celery tasks
    
    Returns:
        SQLAlchemy synchronous Session
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.config import settings
    
    # Crear engine síncrono
    # Convertir PostgresDsn a string y reemplazar el driver
    db_url = str(settings.DATABASE_URL)
    sync_db_url = db_url.replace("+asyncpg", "")
    
    sync_engine = create_engine(
        sync_db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    
    # Crear session factory
    SyncSession = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    
    # Devolver una nueva sesión
    return SyncSession()

# Función para actualizar el estado de una tarea en la base de datos de forma síncrona
def update_task_status_sync(
    task_id: str,
    status: str,
    error_message: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    celery_task_id: Optional[str] = None  # Renombrar para claridad pero mantener compatibilidad
) -> bool:
    """
    Actualiza el estado de una tarea en la base de datos de forma síncrona
    
    Args:
        task_id: ID de la tarea en la base de datos 
        status: Nuevo estado (RUNNING, COMPLETED, FAILED)
        error_message: Mensaje de error si falló
        result: Resultado si se completó
        celery_task_id: ID de la tarea en Celery (si se desea actualizar el task_id)
        
    Returns:
        bool: True si se actualizó correctamente
    """
    from database.models.task import Task, TaskStatus
    
    try:
        # Obtener sesión síncrona
        session = get_sync_session()
        
        try:
            # Buscar la tarea por su ID en base de datos
            from sqlalchemy import select
            stmt = select(Task).where(Task.id == task_id)
            task = session.execute(stmt).scalar_one_or_none()
            
            if not task:
                # Si no encuentra la tarea por ID, buscar por task_id (Celery ID)
                stmt = select(Task).where(Task.task_id == task_id)
                task = session.execute(stmt).scalar_one_or_none()
                
                # Si todavía no encuentra y se proporcionó celery_task_id, buscar con ese valor
                if not task and celery_task_id:
                    stmt = select(Task).where(Task.task_id == celery_task_id)
                    task = session.execute(stmt).scalar_one_or_none()
                
                if not task:
                    logger.warning(f"Task with ID {task_id} not found")
                    return False
                
            # Actualizar estado
            if status == "RUNNING":
                task.status = TaskStatus.RUNNING
                if not task.started_at:
                    task.started_at = datetime.utcnow()
                # Actualizar task_id si se proporcionó celery_task_id nuevo
                if celery_task_id:
                    task.task_id = celery_task_id
            elif status == "COMPLETED":
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                task.error_message = None
                if result:
                    task.result = result
            elif status == "FAILED":
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                task.error_message = error_message
                if result:
                    task.result = result
                    
            # Guardar cambios
            session.commit()
            logger.info(f"Updated task {task.id} status to {status}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating task status: {e}", exc_info=True)
            return False
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error creating sync session: {e}", exc_info=True)
        return False

