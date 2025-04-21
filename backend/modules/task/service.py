from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func

from database.models.task import Task, TaskStatus, TaskType, TaskPriority
from database.models.user import User

logger = logging.getLogger(__name__)

class TaskService:
    """
    Service for centralized task management
    """
    
    async def create_task(
        self,
        db: AsyncSession,
        celery_task_id: str,
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
        Create a new task record
        
        Args:
            db: Database session
            celery_task_id: Celery task ID
            task_name: Name of the task function
            task_type: Type of task
            parameters: Task parameters
            source_type: Type of source entity (e.g., "pipeline", "document")
            source_id: ID of the source entity
            priority: Task priority
            user: User who initiated the task
            max_retries: Maximum number of retries
            
        Returns:
            Created task record
        """
        # Creamos el diccionario con los datos de la tarea
        task_data = {
            "task_id": celery_task_id,
            "name": task_name,
            "task_type": task_type,
            "status": TaskStatus.PENDING,
            "priority": priority,
            "parameters": parameters,
            "source_type": source_type,
            "source_id": source_id,
            "max_retries": max_retries,
            "user_id": user.id if user else None
        }
        
        # Crear la tarea y añadirla a la sesión
        task = Task(**task_data)
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Created task {task.id} of type {task_type} with Celery ID {celery_task_id}")
        return task
    
    async def update_task_status(
        self,
        db: AsyncSession,
        task_id: uuid.UUID,
        status: TaskStatus,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> Optional[Task]:
        """
        Update a task status
        
        Args:
            db: Database session
            task_id: Task ID (database ID)
            status: New status
            error_message: Error message (for failed tasks)
            result: Task result data
            
        Returns:
            Updated task or None if not found
        """
        task = await db.get(Task, task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for status update")
            return None
        
        # Update status and other fields
        task.status = status
        
        # Update timestamps based on status
        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.utcnow()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED):
            task.completed_at = datetime.utcnow()
        
        # Update error message if provided
        if error_message:
            task.error_message = error_message
            
        # Update result if provided
        if result:
            try:
                task.result = result
            except Exception as e:
                logger.error(f"Error serializing task result: {e}")
            
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Updated task {task_id} status to {status}")
        return task
    
    async def update_task_by_celery_id(
        self,
        db: AsyncSession,
        celery_task_id: str,
        status: Optional[TaskStatus] = None,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> Optional[Task]:
        """
        Update a task by its Celery ID
        
        Args:
            db: Database session
            celery_task_id: Celery task ID
            status: New status
            error_message: Error message (for failed tasks)
            result: Task result data
            
        Returns:
            Updated task or None if not found
        """
        query = select(Task).where(Task.task_id == celery_task_id)
        result_query = await db.execute(query)
        task = result_query.scalars().first()
        
        if not task:
            logger.warning(f"Task with Celery ID {celery_task_id} not found")
            return None
        
        # Update status if provided
        if status:
            task.status = status
            
            # Update timestamps based on status
            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.utcnow()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED):
                task.completed_at = datetime.utcnow()
        
        # Update error message if provided
        if error_message:
            task.error_message = error_message
            
        # Update result if provided
        if result:
            try:
                task.result = result
            except Exception as e:
                logger.error(f"Error serializing task result: {e}")
            
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Updated task with Celery ID {celery_task_id}")
        return task
    
    async def get_task(
        self, 
        db: AsyncSession, 
        task_id: uuid.UUID
    ) -> Optional[Task]:
        """
        Get a task by its ID
        
        Args:
            db: Database session
            task_id: Task ID
            
        Returns:
            Task or None if not found
        """
        return await db.get(Task, task_id)
    
    async def get_task_by_celery_id(
        self, 
        db: AsyncSession, 
        celery_task_id: str
    ) -> Optional[Task]:
        """
        Get a task by its Celery ID
        
        Args:
            db: Database session
            celery_task_id: Celery task ID
            
        Returns:
            Task or None if not found
        """
        query = select(Task).where(Task.task_id == celery_task_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_tasks(
        self,
        db: AsyncSession,
        task_type: Optional[TaskType] = None,
        status: Optional[Union[TaskStatus, List[TaskStatus]]] = None,
        source_type: Optional[str] = None,
        source_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        priority: Optional[TaskPriority] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_dir: str = "desc"
    ) -> List[Task]:
        """
        Get tasks with filtering
        
        Args:
            db: Database session
            task_type: Filter by task type
            status: Filter by status or list of statuses
            source_type: Filter by source type
            source_id: Filter by source ID
            user_id: Filter by user ID
            priority: Filter by priority
            limit: Maximum number of records to return
            offset: Offset for pagination
            order_by: Field to order by
            order_dir: Order direction ("asc" or "desc")
            
        Returns:
            List of tasks
        """
        query = select(Task)
        
        # Apply filters
        filters = []
        
        if task_type:
            filters.append(Task.task_type == task_type)
            
        if status:
            if isinstance(status, list):
                filters.append(Task.status.in_(status))
            else:
                filters.append(Task.status == status)
                
        if source_type:
            filters.append(Task.source_type == source_type)
            
        if source_id:
            filters.append(Task.source_id == source_id)
            
        if user_id:
            filters.append(Task.user_id == user_id)
            
        if priority:
            filters.append(Task.priority == priority)
            
        if filters:
            query = query.where(and_(*filters))
            
        # Apply ordering
        if order_by == "priority":
            if order_dir.lower() == "desc":
                query = query.order_by(Task.priority.desc(), Task.created_at.desc())
            else:
                query = query.order_by(Task.priority.asc(), Task.created_at.asc())
        elif hasattr(Task, order_by):
            column = getattr(Task, order_by)
            if order_dir.lower() == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            if order_dir.lower() == "desc":
                query = query.order_by(desc(Task.created_at))
            else:
                query = query.order_by(Task.created_at.asc())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_tasks_by_priority(
        self,
        db: AsyncSession,
        status: Optional[TaskStatus] = None,
        exclude_statuses: List[TaskStatus] = None,
        limit: int = 100
    ) -> List[Task]:
        """
        Get tasks ordered by priority
        
        Args:
            db: Database session
            status: Filter by specific status
            exclude_statuses: List of statuses to exclude
            limit: Maximum number of tasks to return
            
        Returns:
            List of tasks ordered by priority
        """
        query = select(Task)
        
        # Filter by status or exclude specific statuses
        if status:
            query = query.where(Task.status == status)
        if exclude_statuses:
            query = query.where(Task.status.not_in(exclude_statuses))
            
        # Order by priority (highest first) then by created_at (oldest first)
        query = query.order_by(Task.priority.desc(), Task.created_at.asc())
        
        # Apply limit
        query = query.limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_pending_tasks_by_priority(
        self,
        db: AsyncSession,
        limit: int = 100
    ) -> List[Task]:
        """
        Get pending tasks ordered by priority
        
        Args:
            db: Database session
            limit: Maximum number of tasks to return
            
        Returns:
            List of pending tasks ordered by priority
        """
        return await self.get_tasks_by_priority(
            db=db,
            status=TaskStatus.PENDING,
            limit=limit
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
        task = await self.get_task(db, task_id)
        if not task:
            return None
            
        # Only allow changing priority for pending or retrying tasks
        if task.status not in [TaskStatus.PENDING, TaskStatus.RETRYING]:
            logger.warning(f"Cannot change priority for task {task_id} with status {task.status}")
            return task
            
        task.priority = priority
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Updated priority for task {task_id} to {priority}")
        return task
    
    async def get_task_stats(
        self,
        db: AsyncSession,
        task_type: Optional[TaskType] = None,
        source_type: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get task statistics
        
        Args:
            db: Database session
            task_type: Filter by task type
            source_type: Filter by source type
            user_id: Filter by user ID
            since: Only include tasks since this datetime
            
        Returns:
            Dictionary with task statistics
        """
        # Start building the base query with filters
        filters = []
        
        if task_type:
            filters.append(Task.task_type == task_type)
            
        if source_type:
            filters.append(Task.source_type == source_type)
            
        if user_id:
            filters.append(Task.user_id == user_id)
            
        if since:
            filters.append(Task.created_at >= since)
            
        # Total count query
        total_query = select(func.count(Task.id))
        if filters:
            total_query = total_query.where(and_(*filters))
            
        total_result = await db.execute(total_query)
        total_count = total_result.scalar() or 0
        
        # Status breakdown query
        status_query = select(Task.status, func.count(Task.id))
        if filters:
            status_query = status_query.where(and_(*filters))
        status_query = status_query.group_by(Task.status)
        
        status_result = await db.execute(status_query)
        status_breakdown = {status.value: count for status, count in status_result.all()}
        
        # Get counts for each status
        stats = {
            "total": total_count,
            "pending": status_breakdown.get(TaskStatus.PENDING.value, 0),
            "running": status_breakdown.get(TaskStatus.RUNNING.value, 0),
            "completed": status_breakdown.get(TaskStatus.COMPLETED.value, 0),
            "failed": status_breakdown.get(TaskStatus.FAILED.value, 0),
            "canceled": status_breakdown.get(TaskStatus.CANCELED.value, 0),
            "retrying": status_breakdown.get(TaskStatus.RETRYING.value, 0)
        }
        
        # Calculate success rate
        completed = stats["completed"]
        failed = stats["failed"]
        total_finished = completed + failed
        
        if total_finished > 0:
            stats["success_rate"] = round((completed / total_finished) * 100, 2)
        else:
            stats["success_rate"] = 0.0
            
        return stats
    
    async def get_task_processing_times(
        self,
        db: AsyncSession,
        task_type: Optional[TaskType] = None,
        source_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get task processing time statistics
        
        Args:
            db: Database session
            task_type: Filter by task type
            source_type: Filter by source type
            since: Only include tasks created since this time
            limit: Maximum number of tasks to analyze
            
        Returns:
            Dictionary with processing time statistics
        """
        # Build query for completed tasks with start and end times
        query = select(Task).where(
            and_(
                Task.status == TaskStatus.COMPLETED,
                Task.started_at.isnot(None),
                Task.completed_at.isnot(None)
            )
        )
        
        # Apply filters
        if task_type:
            query = query.where(Task.task_type == task_type)
        if source_type:
            query = query.where(Task.source_type == source_type)
        if since:
            query = query.where(Task.created_at >= since)
            
        # Order by most recent and limit
        query = query.order_by(Task.completed_at.desc()).limit(limit)
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        # Calculate processing times
        if not tasks:
            return {
                "count": 0,
                "avg_seconds": 0,
                "min_seconds": 0,
                "max_seconds": 0,
                "total_seconds": 0
            }
            
        processing_times = []
        for task in tasks:
            # Calculate processing time in seconds
            processing_time = (task.completed_at - task.started_at).total_seconds()
            processing_times.append(processing_time)
            
        # Calculate statistics
        count = len(processing_times)
        avg_seconds = sum(processing_times) / count if count > 0 else 0
        min_seconds = min(processing_times) if processing_times else 0
        max_seconds = max(processing_times) if processing_times else 0
        total_seconds = sum(processing_times)
        
        return {
            "count": count,
            "avg_seconds": round(avg_seconds, 2),
            "min_seconds": round(min_seconds, 2),
            "max_seconds": round(max_seconds, 2),
            "total_seconds": round(total_seconds, 2)
        }

    async def update_task(
        self,
        db: AsyncSession,
        task_id: uuid.UUID,
        status: Optional[TaskStatus] = None,
        celery_task_id: Optional[str] = None,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        retries: Optional[int] = None
    ) -> Optional[Task]:
        """
        Update a task with multiple fields
        
        Args:
            db: Database session
            task_id: Task ID
            status: New status
            celery_task_id: Celery task ID
            error_message: Error message
            result: Task result
            retries: Number of retries
            
        Returns:
            Updated task or None if not found
        """
        task = await db.get(Task, task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for update")
            return None
        
        # Update Celery task ID if provided
        if celery_task_id:
            task.task_id = celery_task_id
        
        # Update status if provided
        if status:
            task.status = status
            
            # Update timestamps based on status
            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.utcnow()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED):
                task.completed_at = datetime.utcnow()
        
        # Update error message if provided
        if error_message:
            task.error_message = error_message
            
        # Update result if provided
        if result:
            try:
                task.result = result
            except Exception as e:
                logger.error(f"Error serializing task result: {e}")
                
        # Update retries if provided
        if retries is not None:
            task.retries = retries
            
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Updated task {task_id} with new values")
        return task