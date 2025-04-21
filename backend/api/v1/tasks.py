from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
import uuid

from core.dependencies import get_db, get_current_user
from database.models.user import User
from database.models.task import TaskStatus, TaskType, TaskPriority
from sqlalchemy.ext.asyncio import AsyncSession
from modules.task.service import TaskService
from modules.task.manager import TaskManager

router = APIRouter()

task_service = TaskService()
task_manager = TaskManager(task_service)

@router.get("/tasks", response_model=List[dict])
async def list_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, description="Maximum number of tasks to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of tasks to skip", ge=0),
    order_by: str = Query("created_at", description="Field to order by"),
    order_dir: str = Query("desc", description="Order direction ('asc' or 'desc')"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List tasks with filtering, ordering, and pagination
    """
    try:
        task_type_enum = None
        if task_type:
            try:
                task_type_enum = TaskType[task_type.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid task type: {task_type}"
                )
                
        status_enum = None
        if status:
            try:
                status_enum = TaskStatus[status.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
                
        priority_enum = None
        if priority:
            try:
                priority_enum = TaskPriority[priority.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid priority: {priority}"
                )
                
        user_id_uuid = None
        if user_id:
            try:
                user_id_uuid = uuid.UUID(user_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid user ID: {user_id}"
                )
                
        source_id_uuid = None
        if source_id:
            try:
                source_id_uuid = uuid.UUID(source_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid source ID: {source_id}"
                )
                
        tasks = await task_service.get_tasks(
            db=db,
            task_type=task_type_enum,
            status=status_enum,
            source_type=source_type,
            source_id=source_id_uuid,
            priority=priority_enum,
            user_id=user_id_uuid,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir
        )
        
        task_dicts = []
        for task in tasks:
            duration = None
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
            
            task_dict = {
                "id": str(task.id),
                "celery_id": task.task_id,
                "name": task.name,
                "type": task.task_type.value,
                "status": task.status.value,
                "priority": task.priority.value,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "duration_seconds": round(duration, 2) if duration is not None else None,
                "source_type": task.source_type,
                "source_id": str(task.source_id) if task.source_id else None,
                "retry_count": task.retry_count,
                "user_id": str(task.user_id) if task.user_id else None,
                "error_message": task.error_message,
            }
            task_dicts.append(task_dict)
            
        return task_dicts
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing tasks: {str(e)}"
        )

@router.get("/tasks/{task_id}", response_model=dict)
async def get_task(
    task_id: str = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a task by ID
    """
    try:
        task_uuid = uuid.UUID(task_id)
        task_status = await task_manager.get_task_status(db, task_uuid)
        
        if "error" in task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=task_status["error"]
            )
            
        return task_status
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task ID: {task_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task: {str(e)}"
        )

@router.post("/tasks/{task_id}/cancel", response_model=dict)
async def cancel_task(
    task_id: str = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a task
    """
    try:
        task_uuid = uuid.UUID(task_id)
        task = await task_manager.cancel_task(db, task_uuid)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
            
        return {"message": f"Task {task_id} canceled successfully", "status": task.status.value}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task ID: {task_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error canceling task: {str(e)}"
        )

@router.post("/tasks/{task_id}/retry", response_model=dict)
async def retry_task(
    task_id: str = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retry a failed task
    """
    try:
        task_uuid = uuid.UUID(task_id)
        task = await task_manager.retry_failed_task(db, task_uuid)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found or could not be retried"
            )
            
        return {"message": f"Task {task_id} scheduled for retry", "status": task.status.value}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task ID: {task_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrying task: {str(e)}"
        )

@router.post("/tasks/{task_id}/priority", response_model=dict)
async def update_task_priority(
    priority: str,
    task_id: str = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a task's priority
    """
    try:
        try:
            priority_enum = TaskPriority[priority.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {priority}. Valid values: {[p.value for p in TaskPriority]}"
            )
            
        task_uuid = uuid.UUID(task_id)
        task = await task_manager.update_task_priority(db, task_uuid, priority_enum)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
            
        return {
            "message": f"Task {task_id} priority updated to {priority}",
            "priority": task.priority.value,
            "status": task.status.value
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task ID: {task_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating task priority: {str(e)}"
        )

@router.get("/tasks/stats/summary", response_model=dict)
async def get_task_stats_summary(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    days: int = Query(7, description="Number of days to include", ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get task statistics summary
    """
    try:
        task_type_enum = None
        if task_type:
            try:
                task_type_enum = TaskType[task_type.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid task type: {task_type}"
                )
                
        since = datetime.utcnow() - timedelta(days=days)
        
        stats = await task_service.get_task_stats(
            db=db,
            task_type=task_type_enum,
            source_type=source_type,
            since=since
        )
        
        processing_times = await task_service.get_task_processing_times(
            db=db,
            task_type=task_type_enum,
            source_type=source_type,
            since=since
        )
        
        return {
            "period_days": days,
            "since": since.isoformat(),
            "counts": stats,
            "processing_times": processing_times
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task statistics: {str(e)}"
        )

@router.get("/tasks/source/{source_type}/{source_id}", response_model=List[dict])
async def get_tasks_by_source(
    source_type: str = Path(..., description="Source type"),
    source_id: str = Path(..., description="Source ID"),
    limit: int = Query(10, description="Maximum number of tasks to return", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tasks by source entity
    """
    try:
        source_id_uuid = uuid.UUID(source_id)
        tasks = await task_manager.get_tasks_by_source(
            db=db,
            source_type=source_type,
            source_id=source_id_uuid,
            limit=limit
        )
        
        return tasks
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source ID: {source_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting tasks by source: {str(e)}"
        )