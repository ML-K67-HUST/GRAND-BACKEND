"""
Task service with comprehensive business logic.

This service provides:
- Task creation, reading, updating, deletion
- Business rule validation
- Schedule conflict detection
- Task status transitions
- Performance analytics
- Bulk operations
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from models.task import (
    Task, TaskCreateRequest, TaskUpdateRequest, TaskQueryParams,
    TaskResponse, TaskListResponse, TaskStatus, TaskPriority, TaskCategory
)
from domain.repositories.task_repository import ITaskRepository, SQLAlchemyTaskRepository
from infrastructure.database.connection import get_db_session
from core.exceptions import (
    ValidationError, 
    TaskNotFoundError, 
    ScheduleConflictError,
    DatabaseError
)

logger = logging.getLogger(__name__)


class TaskService:
    """
    Service class for task management with comprehensive business logic.
    """
    
    def __init__(self, task_repository: Optional[ITaskRepository] = None):
        self._task_repository = task_repository
    
    async def _get_repository(self, session: AsyncSession) -> ITaskRepository:
        """Get task repository instance"""
        if self._task_repository:
            return self._task_repository
        return SQLAlchemyTaskRepository(session)
    
    # Core CRUD Operations
    
    async def create_task(
        self, 
        user_id: str, 
        task_request: TaskCreateRequest
    ) -> TaskResponse:
        """
        Create a new task with business validation.
        
        Args:
            user_id: User creating the task
            task_request: Task creation request
            
        Returns:
            TaskResponse: Created task
            
        Raises:
            ValidationError: If validation fails
            ScheduleConflictError: If schedule conflicts exist
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                # Business validation
                await self._validate_task_creation(repository, user_id, task_request)
                
                # Create domain entity
                task = Task(
                    id=str(uuid4()),
                    user_id=user_id,
                    name=task_request.name,
                    description=task_request.description,
                    start_time=task_request.start_time,
                    end_time=task_request.end_time,
                    color=task_request.color,
                    status=task_request.status,
                    priority=task_request.priority,
                    category=task_request.category
                )
                
                # Save to repository
                created_task = await repository.create(task)
                
                logger.info(f"Task created successfully: {created_task.id} for user {user_id}")
                
                # Convert to response
                return TaskResponse.from_db_model(created_task.to_dict())
                
            except (ValidationError, ScheduleConflictError):
                raise
            except Exception as e:
                logger.error(f"Task creation failed: {e}")
                raise DatabaseError(f"Failed to create task: {e}")
    
    async def get_task(self, user_id: str, task_id: str) -> TaskResponse:
        """
        Get task by ID for specific user.
        
        Args:
            user_id: User requesting the task
            task_id: Task identifier
            
        Returns:
            TaskResponse: Task details
            
        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                task = await repository.get_by_id(task_id, user_id)
                
                if not task:
                    raise TaskNotFoundError(task_id)
                
                return TaskResponse.from_db_model(task.to_dict())
                
            except TaskNotFoundError:
                raise
            except Exception as e:
                logger.error(f"Failed to get task {task_id}: {e}")
                raise DatabaseError(f"Failed to retrieve task: {e}")
    
    async def get_tasks(
        self, 
        user_id: str, 
        params: TaskQueryParams
    ) -> TaskListResponse:
        """
        Get tasks for user with filtering and pagination.
        
        Args:
            user_id: User requesting tasks
            params: Query parameters
            
        Returns:
            TaskListResponse: List of tasks with metadata
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                # Get tasks and total count
                tasks, total_count = await repository.get_all(user_id, params)
                
                # Convert to response models
                task_responses = []
                for task in tasks:
                    task_response = TaskResponse.from_db_model(task.to_dict())
                    task_responses.append(task_response)
                
                # Create list response
                return TaskListResponse(
                    tasks=task_responses,
                    total_count=total_count,
                    offset=params.offset,
                    limit=params.limit
                )
                
            except Exception as e:
                logger.error(f"Failed to get tasks for user {user_id}: {e}")
                raise DatabaseError(f"Failed to retrieve tasks: {e}")
    
    async def update_task(
        self, 
        user_id: str, 
        task_id: str, 
        task_request: TaskUpdateRequest
    ) -> TaskResponse:
        """
        Update existing task with business validation.
        
        Args:
            user_id: User updating the task
            task_id: Task identifier
            task_request: Update request data
            
        Returns:
            TaskResponse: Updated task
            
        Raises:
            TaskNotFoundError: If task doesn't exist
            ValidationError: If validation fails
            ScheduleConflictError: If schedule conflicts exist
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                # Get existing task
                existing_task = await repository.get_by_id(task_id, user_id)
                if not existing_task:
                    raise TaskNotFoundError(task_id)
                
                # Apply updates
                await self._apply_task_updates(existing_task, task_request)
                
                # Business validation
                await self._validate_task_update(
                    repository, user_id, existing_task, task_request
                )
                
                # Save updates
                updated_task = await repository.update(existing_task)
                
                logger.info(f"Task updated successfully: {task_id}")
                
                return TaskResponse.from_db_model(updated_task.to_dict())
                
            except (TaskNotFoundError, ValidationError, ScheduleConflictError):
                raise
            except Exception as e:
                logger.error(f"Task update failed: {e}")
                raise DatabaseError(f"Failed to update task: {e}")
    
    async def delete_task(self, user_id: str, task_id: str) -> bool:
        """
        Delete task by ID for specific user.
        
        Args:
            user_id: User deleting the task
            task_id: Task identifier
            
        Returns:
            bool: True if deleted successfully
            
        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                # Check if task exists
                existing_task = await repository.get_by_id(task_id, user_id)
                if not existing_task:
                    raise TaskNotFoundError(task_id)
                
                # Delete task
                deleted = await repository.delete(task_id, user_id)
                
                if deleted:
                    logger.info(f"Task deleted successfully: {task_id}")
                
                return deleted
                
            except TaskNotFoundError:
                raise
            except Exception as e:
                logger.error(f"Task deletion failed: {e}")
                raise DatabaseError(f"Failed to delete task: {e}")
    
    # Advanced Operations
    
    async def get_tasks_in_date_range(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[TaskResponse]:
        """
        Get tasks within a specific date range.
        
        Args:
            user_id: User identifier
            start_date: Range start date
            end_date: Range end date
            
        Returns:
            List[TaskResponse]: Tasks in the date range
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                tasks = await repository.get_tasks_in_date_range(
                    user_id, start_date, end_date
                )
                
                return [
                    TaskResponse.from_db_model(task.to_dict()) 
                    for task in tasks
                ]
                
            except Exception as e:
                logger.error(f"Failed to get tasks in date range: {e}")
                raise DatabaseError(f"Failed to retrieve tasks in date range: {e}")
    
    async def get_overdue_tasks(self, user_id: str) -> List[TaskResponse]:
        """
        Get overdue tasks for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List[TaskResponse]: Overdue tasks
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                tasks = await repository.get_overdue_tasks(user_id)
                
                return [
                    TaskResponse.from_db_model(task.to_dict()) 
                    for task in tasks
                ]
                
            except Exception as e:
                logger.error(f"Failed to get overdue tasks: {e}")
                raise DatabaseError(f"Failed to retrieve overdue tasks: {e}")
    
    async def update_task_status(
        self, 
        user_id: str, 
        task_id: str, 
        new_status: TaskStatus
    ) -> TaskResponse:
        """
        Update task status with business validation.
        
        Args:
            user_id: User updating the status
            task_id: Task identifier
            new_status: New task status
            
        Returns:
            TaskResponse: Updated task
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                # Get existing task
                task = await repository.get_by_id(task_id, user_id)
                if not task:
                    raise TaskNotFoundError(task_id)
                
                # Validate status transition
                self._validate_status_transition(task.status, new_status)
                
                # Update status
                task.status = new_status
                
                # If completing task, set completion time
                if new_status == TaskStatus.COMPLETED:
                    task.updated_at = datetime.now(timezone.utc)
                
                # Save changes
                updated_task = await repository.update(task)
                
                logger.info(f"Task status updated: {task_id} -> {new_status.value}")
                
                return TaskResponse.from_db_model(updated_task.to_dict())
                
            except (TaskNotFoundError, ValidationError):
                raise
            except Exception as e:
                logger.error(f"Status update failed: {e}")
                raise DatabaseError(f"Failed to update task status: {e}")
    
    async def check_schedule_conflicts(
        self, 
        user_id: str, 
        start_time: datetime, 
        end_time: datetime,
        exclude_task_id: Optional[str] = None
    ) -> List[TaskResponse]:
        """
        Check for schedule conflicts.
        
        Args:
            user_id: User identifier
            start_time: Proposed start time
            end_time: Proposed end time
            exclude_task_id: Task ID to exclude from conflict check
            
        Returns:
            List[TaskResponse]: Conflicting tasks
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                conflicts = await repository.check_schedule_conflict(
                    user_id, start_time, end_time, exclude_task_id
                )
                
                return [
                    TaskResponse.from_db_model(task.to_dict()) 
                    for task in conflicts
                ]
                
            except Exception as e:
                logger.error(f"Conflict check failed: {e}")
                raise DatabaseError(f"Failed to check schedule conflicts: {e}")
    
    async def get_task_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive task statistics for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict[str, Any]: Task statistics
        """
        async with get_db_session() as session:
            try:
                repository = await self._get_repository(session)
                
                stats = await repository.get_task_statistics(user_id)
                
                # Add additional calculated metrics
                today = datetime.now(timezone.utc).date()
                week_start = today - timedelta(days=today.weekday())
                week_end = week_start + timedelta(days=6)
                
                # Get tasks for this week
                week_tasks = await repository.get_tasks_in_date_range(
                    user_id,
                    datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc),
                    datetime.combine(week_end, datetime.max.time()).replace(tzinfo=timezone.utc)
                )
                
                stats['this_week_tasks'] = len(week_tasks)
                stats['this_week_completed'] = len([
                    t for t in week_tasks if t.status == TaskStatus.COMPLETED
                ])
                
                return stats
                
            except Exception as e:
                logger.error(f"Failed to get task statistics: {e}")
                raise DatabaseError(f"Failed to retrieve task statistics: {e}")
    
    # Bulk Operations
    
    async def bulk_update_status(
        self, 
        user_id: str, 
        task_ids: List[str], 
        new_status: TaskStatus
    ) -> List[TaskResponse]:
        """
        Update status for multiple tasks.
        
        Args:
            user_id: User performing the update
            task_ids: List of task IDs to update
            new_status: New status for all tasks
            
        Returns:
            List[TaskResponse]: Updated tasks
        """
        updated_tasks = []
        
        for task_id in task_ids:
            try:
                updated_task = await self.update_task_status(user_id, task_id, new_status)
                updated_tasks.append(updated_task)
            except Exception as e:
                logger.warning(f"Failed to update task {task_id}: {e}")
                # Continue with other tasks
        
        return updated_tasks
    
    async def bulk_delete_tasks(
        self, 
        user_id: str, 
        task_ids: List[str]
    ) -> Dict[str, bool]:
        """
        Delete multiple tasks.
        
        Args:
            user_id: User performing the deletion
            task_ids: List of task IDs to delete
            
        Returns:
            Dict[str, bool]: Map of task_id -> deletion_success
        """
        results = {}
        
        for task_id in task_ids:
            try:
                deleted = await self.delete_task(user_id, task_id)
                results[task_id] = deleted
            except Exception as e:
                logger.warning(f"Failed to delete task {task_id}: {e}")
                results[task_id] = False
        
        return results
    
    # Private Methods - Business Logic
    
    async def _validate_task_creation(
        self, 
        repository: ITaskRepository, 
        user_id: str, 
        task_request: TaskCreateRequest
    ) -> None:
        """Validate task creation business rules"""
        
        # Check for schedule conflicts
        conflicts = await repository.check_schedule_conflict(
            user_id, task_request.start_time, task_request.end_time
        )
        
        if conflicts:
            conflicting_task = conflicts[0]
            raise ScheduleConflictError(conflicting_task.id)
        
        # Additional business validations can be added here
        # e.g., maximum tasks per day, priority constraints, etc.
    
    async def _validate_task_update(
        self, 
        repository: ITaskRepository, 
        user_id: str, 
        existing_task: Task,
        task_request: TaskUpdateRequest
    ) -> None:
        """Validate task update business rules"""
        
        # If time is being updated, check for conflicts
        if (task_request.start_time is not None or 
            task_request.end_time is not None):
            
            start_time = task_request.start_time or existing_task.start_time
            end_time = task_request.end_time or existing_task.end_time
            
            conflicts = await repository.check_schedule_conflict(
                user_id, start_time, end_time, existing_task.id
            )
            
            if conflicts:
                conflicting_task = conflicts[0]
                raise ScheduleConflictError(conflicting_task.id)
    
    async def _apply_task_updates(
        self, 
        task: Task, 
        updates: TaskUpdateRequest
    ) -> None:
        """Apply updates to task entity"""
        
        update_data = updates.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(task, field) and value is not None:
                setattr(task, field, value)
    
    def _validate_status_transition(
        self, 
        current_status: TaskStatus, 
        new_status: TaskStatus
    ) -> None:
        """Validate that status transition is allowed"""
        
        # Define allowed transitions
        allowed_transitions = {
            TaskStatus.PENDING: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
            TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.BLOCKED, TaskStatus.CANCELLED],
            TaskStatus.BLOCKED: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
            TaskStatus.COMPLETED: [],  # Final state
            TaskStatus.CANCELLED: []   # Final state
        }
        
        allowed = allowed_transitions.get(current_status, [])
        
        if new_status not in allowed and new_status != current_status:
            raise ValidationError(
                f"Invalid status transition from {current_status.value} to {new_status.value}"
            ) 