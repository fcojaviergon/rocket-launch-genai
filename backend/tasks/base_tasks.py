"""
Base utilities for Celery tasks
"""
import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar

from database.session import get_async_session_context  

from celery import Task

logger = logging.getLogger('tasks.base')

# Tipo para resultados de las tareas
T = TypeVar('T')


class AsyncTask(Task):
    """Clase base para tareas asíncronas en Celery"""
    
    async def _call_async(self, *args, **kwargs):
        """Implementación asíncrona de la tarea"""
        raise NotImplementedError("Las subclases deben implementar este método")
    
    def __call__(self, *args, **kwargs):
        """Método principal que ejecuta la tarea asíncrona"""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Si ya hay un bucle en ejecución, usamos ese
            return loop.create_task(self._call_async(*args, **kwargs))
        else:
            # Si no hay un bucle en ejecución, creamos uno nuevo
            return asyncio.run(self._call_async(*args, **kwargs))
    
    @classmethod
    def register_task(cls, app, name=None, **options):
        """Registra una tarea asíncrona en la aplicación Celery"""
        def decorator(async_func):
            task_name = name or async_func.__name__
            
            # Crear una subclase de AsyncTask para esta función específica
            task_cls = type(f"{async_func.__name__}Task", (cls,), {
                "_call_async": staticmethod(async_func),
                "__module__": async_func.__module__,
                "__doc__": async_func.__doc__
            })
            
            # Registrar la tarea en Celery
            app.register_task(task_cls())
            
            # Devolver la función original sin modificar
            return async_func
        
        return decorator


# Decorador para crear tareas asíncronas
def async_task(app, name=None, **options):
    """Decorador para crear tareas asíncronas en Celery"""
    return AsyncTask.register_task(app, name, **options)

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

def update_task_status_sync(
    task_id: str,
    status: str,
    error_message: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    celery_task_id: Optional[str] = None  # Renombrar para claridad pero mantener compatibilidad
) -> bool:
    """
    Actualiza el estado de una tarea en la base de datos de forma síncrona
    
    IMPORTANTE: task_id puede ser:
    1. Un UUID de la columna 'id' de la tabla Task (formato UUID)
    2. El ID de Celery (columna 'celery_id' en la tabla Task)
    
    Esta función busca primero por id, luego por celery_id, y finalmente por celery_task_id si se proporciona.
    
    Args:
        task_id: ID de la tarea (puede ser UUID de DB o ID de Celery)
        status: Nuevo estado (RUNNING, COMPLETED, FAILED)
        error_message: Mensaje de error si falló
        result: Resultado si se completó
        celery_task_id: ID de la tarea en Celery (si se desea actualizar el task_id)
        
    Returns:
        bool: True si se actualizó correctamente
    """
    from database.models.task import Task, TaskStatus
    from database.session import get_sync_session_context
    
    try:
        # Usar context manager para sesiones síncronas en Celery
        with get_sync_session_context() as session:
            # Buscar la tarea por su ID en base de datos usando API síncrona
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                # Si no encuentra la tarea por ID, buscar por celery_id (Celery ID)
                task = session.query(Task).filter(Task.celery_id == task_id).first()
                
                # Si todavía no encuentra y se proporcionó celery_task_id, buscar con ese valor
                if not task and celery_task_id:
                    task = session.query(Task).filter(Task.celery_id == celery_task_id).first()
                    
                if not task:
                    # Verificar si parece ser un ID de subtarea de Celery (contiene guiones)
                    if "-" in task_id:
                        logger.warning(f"No se encontró tarea para ID {task_id}. Puede ser una subtarea.")
                    else:
                        logger.error(f"No se encontró tarea para ID {task_id}")
                    return False
                
            # Actualizar estado
            if status == "RUNNING":
                task.status = TaskStatus.RUNNING
                if not task.started_at:
                    task.started_at = datetime.utcnow()
                # Actualizar task_id si se proporcionó celery_task_id nuevo
                if celery_task_id:
                    task.celery_id = celery_task_id
            elif status == "COMPLETED":
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                task.error_message = None
                if result:
                    # Serializar el resultado para evitar problemas de JSON
                    from utils.serialization import serialize_for_json
                    
                    # Verificar si es un AsyncResult de Celery
                    from celery.result import AsyncResult
                    if isinstance(result, AsyncResult):
                        # Convertir AsyncResult a un diccionario serializable
                        task.result = {
                            "task_id": result.id,
                            "status": result.status,
                            "success": True
                        }
                    else:
                        # Serializar cualquier otro tipo de resultado
                        task.result = serialize_for_json(result)
            elif status == "FAILED":
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                task.error_message = error_message
                if result:
                    # Serializar el resultado para evitar problemas de JSON
                    from utils.serialization import serialize_for_json
                    
                    # Verificar si es un AsyncResult de Celery
                    from celery.result import AsyncResult
                    if isinstance(result, AsyncResult):
                        # Convertir AsyncResult a un diccionario serializable
                        task.result = {
                            "task_id": result.id,
                            "status": result.status,
                            "success": True
                        }
                    else:
                        # Serializar cualquier otro tipo de resultado
                        task.result = serialize_for_json(result)
                    
            # Guardar cambios (el commit se hace automáticamente al salir del context manager)
            
            # Mensaje más informativo sobre la actualización de la tarea
            # Verificar si el modelo Task tiene el atributo parent_task_id
            has_parent_field = hasattr(task, 'parent_task_id')
            task_type = "Main task" if not has_parent_field or task.parent_task_id is None else "Subtask"
            parent_info = f" (Parent: {task.parent_task_id})" if has_parent_field and task.parent_task_id else ""
            result_info = ""
            
            if status == "COMPLETED" and isinstance(task.result, dict):
                # Añadir información relevante del resultado
                if "workflow_completed" in task.result:
                    result_info = " - Workflow completed"
                elif "analysis_completed" in task.result:
                    result_info = " - Analysis completed"
                elif "documents_combined" in task.result:
                    result_info = " - Documents combined"
            
            logger.info(f"{task_type} updated: DB ID {task.id} (Celery ID: {task.celery_id}){parent_info} "
                       f"status → {status}{result_info}")
            return True
            
    except Exception as e:
        logger.error(f"Error en update_task_status_sync: {e}", exc_info=True)
        return False