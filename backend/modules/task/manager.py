"""
Task manager for high-level task operations
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import uuid
import logging
import json
import asyncio

from celery.result import AsyncResult
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.task import Task, TaskStatus, TaskType, TaskPriority
from database.models.user import User
from modules.task.service import TaskService

logger = logging.getLogger(__name__)

class TaskManager:
    """
    High-level manager for task operations
    """
    
    def __init__(self, task_service: TaskService):
        """
        Initialize the task manager
        
        Args:
            task_service: Task service for database operations
        """
        self.task_service = task_service
        
    async def create_task(
        self,
        db: AsyncSession,
        task_name: str,
        task_type: TaskType,
        parameters: Dict[str, Any] = None,
        source_type: Optional[str] = None,
        source_id: Optional[uuid.UUID] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        user: Optional[User] = None,
        max_retries: int = 3,
        celery_task_id: Optional[str] = None
    ) -> Task:
        """
        Crear una nueva tarea en la base de datos
        
        Args:
            db: Base de datos
            task_name: Nombre de la tarea
            task_type: Tipo de tarea
            parameters: Parámetros de la tarea
            source_type: Tipo de la entidad fuente
            source_id: ID de la entidad fuente
            priority: Prioridad
            user: Usuario que inició la tarea
            max_retries: Número máximo de reintentos
            celery_task_id: ID de la tarea en Celery (opcional)
            
        Returns:
            Task: La tarea creada
        """
        task = await self.task_service.create_task(
            db=db,
            celery_task_id=celery_task_id or str(uuid.uuid4()),  # Generar ID temporal si no se proporciona
            task_name=task_name,
            task_type=task_type,
            parameters=parameters,
            source_type=source_type,
            source_id=source_id,
            priority=priority,
            user=user,
            max_retries=max_retries
        )
        
        logger.info(f"Created task {task.id} of type {task_type.value} for {source_type} {source_id}")
        return task
        
    async def register_task(
        self,
        db: AsyncSession,
        celery_task,
        task_name: str,
        task_type: TaskType,
        parameters: Dict[str, Any] = None,
        source_type: Optional[str] = None,
        source_id: Optional[uuid.UUID] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        user: Optional[User] = None,
        max_retries: int = 3
    ) -> Task:
        """
        Register a Celery task in the task management system
        
        Args:
            db: Database session
            celery_task: Celery task object
            task_name: Name of the task
            task_type: Type of task
            parameters: Task parameters
            source_type: Type of source entity
            source_id: ID of the source entity
            priority: Task priority
            user: User who initiated the task
            max_retries: Maximum number of retries
            
        Returns:
            Created task record
        """
        celery_task_id = celery_task.id if hasattr(celery_task, 'id') else str(celery_task)
        
        task = await self.task_service.create_task(
            db=db,
            celery_task_id=celery_task_id,
            task_name=task_name,
            task_type=task_type,
            parameters=parameters,
            source_type=source_type,
            source_id=source_id,
            priority=priority,
            user=user,
            max_retries=max_retries
        )
        
        logger.info(f"Registered task {task.id} with Celery ID {celery_task_id} (priority: {priority.value})")
        return task
        
    async def register_batch_tasks(
        self,
        db: AsyncSession,
        celery_tasks: List,
        task_name: str,
        task_type: TaskType,
        source_type: Optional[str] = None,
        source_ids: Optional[List[uuid.UUID]] = None,
        parameters_list: Optional[List[Dict[str, Any]]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        user: Optional[User] = None,
        max_retries: int = 3
    ) -> List[Task]:
        """
        Register multiple Celery tasks in batch
        
        Args:
            db: Database session
            celery_tasks: List of Celery task objects
            task_name: Name of the task
            task_type: Type of task
            source_type: Type of source entity
            source_ids: List of source IDs (one per task)
            parameters_list: List of task parameters (one per task)
            priority: Task priority
            user: User who initiated the tasks
            max_retries: Maximum number of retries
            
        Returns:
            List of created task records
        """
        tasks = []
        
        for i, celery_task in enumerate(celery_tasks):
            # Get source_id and parameters for this task
            source_id = source_ids[i] if source_ids and i < len(source_ids) else None
            parameters = parameters_list[i] if parameters_list and i < len(parameters_list) else None
            
            task = await self.register_task(
                db=db,
                celery_task=celery_task,
                task_name=task_name,
                task_type=task_type,
                parameters=parameters,
                source_type=source_type,
                source_id=source_id,
                priority=priority,
                user=user,
                max_retries=max_retries
            )
            
            tasks.append(task)
            
        logger.info(f"Registered batch of {len(tasks)} tasks")
        return tasks
        
    async def update_task_status(
        self,
        db: AsyncSession,
        task_id: uuid.UUID,
        status: TaskStatus,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> Optional[Task]:
        """
        Update a task's status
        
        Args:
            db: Database session
            task_id: Task ID
            status: New status
            error_message: Error message if status is failed
            result: Task result data
            
        Returns:
            Updated task if found, None otherwise
        """
        return await self.task_service.update_task_status(
            db=db,
            task_id=task_id,
            status=status,
            error_message=error_message,
            result=result
        )
        
    async def update_task(
        self,
        db: AsyncSession,
        task_id: uuid.UUID,
        celery_task_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        retries: Optional[int] = None
    ) -> Optional[Task]:
        """
        Actualizar una tarea existente
        
        Args:
            db: Base de datos
            task_id: ID de la tarea
            celery_task_id: ID de la tarea en Celery
            status: Nuevo estado
            error_message: Mensaje de error
            result: Resultado de la tarea
            retries: Número de reintentos
            
        Returns:
            Task: La tarea actualizada o None si no se encontró
        """
        return await self.task_service.update_task(
            db=db,
            task_id=task_id,
            celery_task_id=celery_task_id,
            status=status,
            error_message=error_message,
            result=result,
            retries=retries
        )
        
    async def update_task_priority(
        self,
        db: AsyncSession,
        task_id: uuid.UUID,
        priority: TaskPriority
    ) -> Optional[Task]:
        """
        Update a task's priority
        
        Args:
            db: Database session
            task_id: Task ID
            priority: New priority
            
        Returns:
            Updated task if found, None otherwise
        """
        return await self.task_service.update_task_priority(
            db=db,
            task_id=task_id,
            priority=priority
        )
        
    async def update_task_celery_id(
        self,
        db: AsyncSession,
        task_id: uuid.UUID,
        celery_task_id: str
    ) -> Optional[Task]:
        """
        Update a task's Celery task ID
        
        Args:
            db: Database session
            task_id: Task ID
            celery_task_id: New Celery task ID
            
        Returns:
            Updated task if found, None otherwise
        """
        return await self.task_service.update_task(db, task_id, celery_task_id=celery_task_id)
    
    async def cancel_task(
        self,
        db: AsyncSession,
        task_id: uuid.UUID
    ) -> Optional[Task]:
        """
        Cancel a task if it's not already completed or failed
        
        Args:
            db: Database session
            task_id: Task ID
            
        Returns:
            Updated task if found and canceled, None otherwise
        """
        task = await self.task_service.get_task(db, task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for cancellation")
            return None
            
        # Only cancel if task is still pending or running
        if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING]:
            logger.warning(f"Cannot cancel task {task_id} with status {task.status}")
            return task
            
        # Try to revoke the Celery task
        try:
            from tasks.worker import celery_app
            celery_app.control.revoke(task.task_id, terminate=True)
            logger.info(f"Revoked Celery task {task.task_id}")
        except Exception as e:
            logger.error(f"Error revoking Celery task {task.task_id}: {e}")
            
        # Update status in database
        return await self.task_service.update_task_status(
            db=db,
            task_id=task_id,
            status=TaskStatus.CANCELED,
            error_message="Task canceled by user"
        )
        
    async def get_task_status(
        self,
        db: AsyncSession,
        task_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get the current status of a task with additional information
        
        Args:
            db: Database session
            task_id: Task ID
            
        Returns:
            Dictionary with task status information
        """
        task = await self.task_service.get_task(db, task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}
            
        # Calculate duration if possible
        duration = None
        if task.started_at and task.completed_at:
            duration = (task.completed_at - task.started_at).total_seconds()
        elif task.started_at:
            duration = (datetime.utcnow() - task.started_at).total_seconds()
            
        # Build status response
        status_info = {
            "id": str(task.id),
            "celery_id": task.task_id,
            "name": task.name,
            "type": task.task_type.value,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration_seconds": round(duration, 2) if duration else None,
            "retry_count": task.retry_count,
            "source_type": task.source_type,
            "source_id": str(task.source_id) if task.source_id else None,
        }
        
        # Add error message if task failed
        if task.status == TaskStatus.FAILED and task.error_message:
            status_info["error_message"] = task.error_message
            
        return status_info
        
    async def get_tasks_by_source(
        self,
        db: AsyncSession,
        source_type: str,
        source_id: uuid.UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get tasks associated with a specific source entity
        
        Args:
            db: Database session
            source_type: Type of source entity
            source_id: ID of the source entity
            limit: Maximum number of tasks to return
            
        Returns:
            List of task status dictionaries
        """
        tasks = await self.task_service.get_tasks(
            db=db,
            source_type=source_type,
            source_id=source_id,
            limit=limit
        )
        
        return [await self.get_task_status(db, task.id) for task in tasks]
        
    async def process_next_pending_tasks(
        self,
        db: AsyncSession,
        task_type: Optional[TaskType] = None,
        limit: int = 5
    ) -> List[Task]:
        """
        Process the next batch of pending tasks based on priority
        
        Args:
            db: Database session
            task_type: Specific task type to process
            limit: Maximum number of tasks to process
            
        Returns:
            List of tasks that were processed
        """
        # Get pending tasks ordered by priority
        query_params = {"status": TaskStatus.PENDING, "limit": limit}
        if task_type:
            query_params["task_type"] = task_type
            
        tasks = await self.task_service.get_tasks_by_priority(db=db, **query_params)
        processed_tasks = []
        
        for task in tasks:
            try:
                # Use task parameters to resubmit the task
                # This is a simplified version, in a real implementation you would 
                # need to handle different task types differently
                from tasks.worker import celery_app
                task_func = celery_app.tasks.get(task.name)
                
                if not task_func:
                    logger.error(f"Task function {task.name} not found")
                    continue
                    
                # Execute the task with its parameters
                parameters = task.parameters or {}
                result = task_func.delay(**parameters)
                
                # Update the task record
                await self.task_service.update_task_by_celery_id(
                    db=db,
                    celery_task_id=task.task_id,
                    status=TaskStatus.RUNNING
                )
                
                processed_tasks.append(task)
                logger.info(f"Processed pending task {task.id} with priority {task.priority.value}")
                
            except Exception as e:
                logger.error(f"Error processing task {task.id}: {e}")
                await self.task_service.update_task_status(
                    db=db,
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error_message=f"Error resubmitting task: {str(e)}"
                )
                
        return processed_tasks

    async def retry_failed_task(
        self,
        db: AsyncSession,
        task_id: uuid.UUID
    ) -> Optional[Task]:
        """
        Retry a failed task
        
        Args:
            db: Database session
            task_id: Task ID
            
        Returns:
            Updated task if found and retried, None otherwise
        """
        task = await self.task_service.get_task(db, task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for retry")
            return None
            
        # Only retry if task is failed
        if task.status != TaskStatus.FAILED:
            logger.warning(f"Cannot retry task {task_id} with status {task.status}")
            return task
            
        try:
            # Use task parameters to resubmit the task
            from tasks.worker import celery_app
            task_func = celery_app.tasks.get(task.name)
            
            if not task_func:
                logger.error(f"Task function {task.name} not found")
                return None
                
            # Execute the task with its parameters
            parameters = task.parameters or {}
            result = task_func.delay(**parameters)
            
            # Update the task record with the new Celery task ID
            task.task_id = result.id
            task.status = TaskStatus.RETRYING
            task.retry_count += 1
            task.started_at = None
            task.completed_at = None
            task.error_message = None
            
            await db.commit()
            await db.refresh(task)
            
            logger.info(f"Retried failed task {task.id}")
            return task
            
        except Exception as e:
            logger.error(f"Error retrying task {task.id}: {e}")
            return None