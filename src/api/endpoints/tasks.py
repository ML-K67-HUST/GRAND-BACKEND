"""
Task API endpoints with clean architecture integration.

This module provides:
- RESTful task endpoints
- Proper error handling and validation
- Authentication integration
- Pagination and filtering
- OpenAPI documentation
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Path, Body, status
from fastapi.responses import JSONResponse

from models.task import (
    TaskCreateRequest, 
    TaskUpdateRequest, 
    TaskQueryParams,
    TaskResponse, 
    TaskListResponse,
    TaskStatus
)
from services.task_service import TaskService
from api.middleware.authentication import require_auth, get_current_user_id
from core.exceptions import (
    TaskNotFoundError, 
    ValidationError, 
    ScheduleConflictError,
    AuthenticationError
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Dependency injection
def get_task_service() -> TaskService:
    """Get task service instance"""
    return TaskService()


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Create a new task with schedule conflict validation"
)
async def create_task(
    task_request: TaskCreateRequest = Body(..., description="Task creation data"),
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Create a new task for the authenticated user.
    
    - **name**: Task name (required, 1-255 characters)
    - **description**: Task description (optional, max 2000 characters)
    - **start_time**: Task start time (ISO format with timezone)
    - **end_time**: Task end time (ISO format with timezone)
    - **color**: Task color in hex format (default: #3498DB)
    - **status**: Task status (default: pending)
    - **priority**: Task priority level (1-5, default: 2)
    - **category**: Task category (default: other)
    
    Returns the created task with generated ID and timestamps.
    """
    try:
        task = await task_service.create_task(user_id, task_request)
        logger.info(f"Task created via API: {task.id} for user {user_id}")
        return task
        
    except ScheduleConflictError as e:
        logger.warning(f"Task creation failed - schedule conflict: {e.message}")
        raise
    except ValidationError as e:
        logger.warning(f"Task creation failed - validation: {e.message}")
        raise


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="Get tasks with filtering and pagination",
    description="Retrieve tasks for the authenticated user with optional filtering"
)
async def get_tasks(
    # Filtering parameters
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by priority level"),
    category: Optional[str] = Query(None, description="Filter by task category"),
    name_contains: Optional[str] = Query(None, max_length=100, description="Filter by task name substring"),
    
    # Date range filtering
    start_date: Optional[datetime] = Query(None, description="Filter tasks starting after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter tasks ending before this date"),
    
    # Pagination
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    
    # Sorting
    sort_by: str = Query("start_time", description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    
    # Dependencies
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> TaskListResponse:
    """
    Get tasks for the authenticated user with optional filtering and pagination.
    
    Supports filtering by:
    - Status (pending, in_progress, completed, cancelled, blocked)
    - Priority level (1-5)
    - Category
    - Name substring search
    - Date range
    
    Returns paginated results with metadata including total count and summary statistics.
    """
    # Build query parameters
    params = TaskQueryParams(
        status=status,
        priority=priority,
        category=category,
        name_contains=name_contains,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    tasks = await task_service.get_tasks(user_id, params)
    logger.debug(f"Retrieved {len(tasks.tasks)} tasks for user {user_id}")
    return tasks


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a specific task",
    description="Retrieve a single task by ID"
)
async def get_task(
    task_id: str = Path(..., description="Task ID"),
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Get a specific task by ID for the authenticated user.
    
    Returns the task details including computed fields like duration and status flags.
    """
    try:
        task = await task_service.get_task(user_id, task_id)
        return task
        
    except TaskNotFoundError as e:
        logger.warning(f"Task not found: {task_id} for user {user_id}")
        raise


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
    description="Update an existing task with validation"
)
async def update_task(
    task_id: str = Path(..., description="Task ID"),
    task_request: TaskUpdateRequest = Body(..., description="Task update data"),
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Update an existing task for the authenticated user.
    
    All fields are optional in the update request. Only provided fields will be updated.
    Schedule conflict validation is performed if start_time or end_time is changed.
    """
    try:
        task = await task_service.update_task(user_id, task_id, task_request)
        logger.info(f"Task updated via API: {task_id} for user {user_id}")
        return task
        
    except TaskNotFoundError as e:
        logger.warning(f"Update failed - task not found: {task_id}")
        raise
    except ScheduleConflictError as e:
        logger.warning(f"Update failed - schedule conflict: {e.message}")
        raise
    except ValidationError as e:
        logger.warning(f"Update failed - validation: {e.message}")
        raise


@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
    summary="Update task status",
    description="Update only the status of a task with transition validation"
)
async def update_task_status(
    task_id: str = Path(..., description="Task ID"),
    new_status: TaskStatus = Body(..., embed=True, description="New task status"),
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Update the status of a specific task.
    
    Status transitions are validated according to business rules:
    - pending → in_progress, cancelled
    - in_progress → completed, blocked, cancelled
    - blocked → in_progress, cancelled
    - completed, cancelled → (final states, no transitions allowed)
    """
    try:
        task = await task_service.update_task_status(user_id, task_id, new_status)
        logger.info(f"Task status updated: {task_id} -> {new_status.value}")
        return task
        
    except TaskNotFoundError as e:
        logger.warning(f"Status update failed - task not found: {task_id}")
        raise
    except ValidationError as e:
        logger.warning(f"Status update failed - invalid transition: {e.message}")
        raise


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Delete a task permanently"
)
async def delete_task(
    task_id: str = Path(..., description="Task ID"),
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Delete a task permanently for the authenticated user.
    
    This action cannot be undone. Returns 204 No Content on success.
    """
    try:
        await task_service.delete_task(user_id, task_id)
        logger.info(f"Task deleted via API: {task_id} for user {user_id}")
        
    except TaskNotFoundError as e:
        logger.warning(f"Delete failed - task not found: {task_id}")
        raise


@router.get(
    "/overdue/list",
    response_model=List[TaskResponse],
    summary="Get overdue tasks",
    description="Retrieve all overdue tasks for the authenticated user"
)
async def get_overdue_tasks(
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """
    Get all overdue tasks for the authenticated user.
    
    Returns tasks that have passed their end_time and are still in active status
    (pending, in_progress, or blocked).
    """
    tasks = await task_service.get_overdue_tasks(user_id)
    logger.debug(f"Retrieved {len(tasks)} overdue tasks for user {user_id}")
    return tasks


@router.get(
    "/date-range",
    response_model=List[TaskResponse],
    summary="Get tasks in date range",
    description="Retrieve tasks within a specific date range"
)
async def get_tasks_in_date_range(
    start_date: datetime = Query(..., description="Range start date (ISO format)"),
    end_date: datetime = Query(..., description="Range end date (ISO format)"),
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """
    Get tasks within a specific date range for the authenticated user.
    
    Returns tasks that overlap with the specified date range.
    """
    tasks = await task_service.get_tasks_in_date_range(user_id, start_date, end_date)
    logger.debug(f"Retrieved {len(tasks)} tasks in date range for user {user_id}")
    return tasks


@router.post(
    "/check-conflicts",
    response_model=List[TaskResponse],
    summary="Check schedule conflicts",
    description="Check for schedule conflicts with proposed time slot"
)
async def check_schedule_conflicts(
    start_time: datetime = Body(..., description="Proposed start time"),
    end_time: datetime = Body(..., description="Proposed end time"),
    exclude_task_id: Optional[str] = Body(None, description="Task ID to exclude from conflict check"),
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """
    Check for schedule conflicts with a proposed time slot.
    
    Useful for validating task creation or updates before submission.
    Can exclude a specific task ID (useful for task updates).
    
    Returns list of conflicting tasks.
    """
    conflicts = await task_service.check_schedule_conflicts(
        user_id, start_time, end_time, exclude_task_id
    )
    logger.debug(f"Found {len(conflicts)} schedule conflicts for user {user_id}")
    return conflicts


@router.get(
    "/statistics/summary",
    summary="Get task statistics",
    description="Get comprehensive task statistics for the authenticated user"
)
async def get_task_statistics(
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> dict:
    """
    Get comprehensive task statistics for the authenticated user.
    
    Returns metrics including:
    - Total tasks by status
    - Completion rates
    - Overdue tasks count
    - This week's tasks and completion
    - Average completion time
    """
    stats = await task_service.get_task_statistics(user_id)
    logger.debug(f"Retrieved task statistics for user {user_id}")
    return stats


# Bulk Operations

@router.patch(
    "/bulk/status",
    response_model=List[TaskResponse],
    summary="Bulk update task status",
    description="Update status for multiple tasks"
)
async def bulk_update_status(
    task_ids: List[str] = Body(..., description="List of task IDs to update"),
    new_status: TaskStatus = Body(..., description="New status for all tasks"),
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """
    Update status for multiple tasks in a single operation.
    
    Returns list of successfully updated tasks. Failed updates are logged but don't
    prevent other tasks from being updated.
    """
    updated_tasks = await task_service.bulk_update_status(user_id, task_ids, new_status)
    logger.info(f"Bulk status update: {len(updated_tasks)}/{len(task_ids)} tasks updated")
    return updated_tasks


@router.delete(
    "/bulk/delete",
    summary="Bulk delete tasks",
    description="Delete multiple tasks"
)
async def bulk_delete_tasks(
    task_ids: List[str] = Body(..., description="List of task IDs to delete"),
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service)
) -> dict:
    """
    Delete multiple tasks in a single operation.
    
    Returns a map of task_id -> deletion_success for each task.
    """
    results = await task_service.bulk_delete_tasks(user_id, task_ids)
    success_count = sum(1 for success in results.values() if success)
    logger.info(f"Bulk delete: {success_count}/{len(task_ids)} tasks deleted")
    
    return {
        "results": results,
        "summary": {
            "total_requested": len(task_ids),
            "successful_deletions": success_count,
            "failed_deletions": len(task_ids) - success_count
        }
    } 