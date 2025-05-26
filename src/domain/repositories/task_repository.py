"""
Task repository interfaces and implementations.

This module provides:
- Abstract repository interface for tasks
- SQLAlchemy implementation with async operations
- Error handling and validation
- Efficient query methods with filtering and pagination
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from models.task import Task, TaskQueryParams, TaskStatus
from core.exceptions import TaskNotFoundError, DatabaseError, ValidationError

logger = logging.getLogger(__name__)


class ITaskRepository(ABC):
    """
    Abstract repository interface for task operations.
    
    This interface defines the contract for task data access operations.
    Implementations should handle all database-specific logic.
    """
    
    @abstractmethod
    async def create(self, task: Task) -> Task:
        """
        Create a new task.
        
        Args:
            task: Task domain model to create
            
        Returns:
            Created task with generated ID and timestamps
            
        Raises:
            DatabaseError: If creation fails
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: str, task_id: str) -> Optional[Task]:
        """
        Get a task by ID for a specific user.
        
        Args:
            user_id: User ID who owns the task
            task_id: Task ID to retrieve
            
        Returns:
            Task if found, None otherwise
            
        Raises:
            DatabaseError: If query fails
        """
        pass
    
    @abstractmethod
    async def get_by_user(self, user_id: str, params: TaskQueryParams) -> tuple[List[Task], int]:
        """
        Get tasks for a user with filtering and pagination.
        
        Args:
            user_id: User ID to get tasks for
            params: Query parameters for filtering and pagination
            
        Returns:
            Tuple of (tasks list, total count)
            
        Raises:
            DatabaseError: If query fails
        """
        pass
    
    @abstractmethod
    async def update(self, task: Task) -> Task:
        """
        Update an existing task.
        
        Args:
            task: Task domain model with updated data
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task doesn't exist
            DatabaseError: If update fails
        """
        pass
    
    @abstractmethod
    async def delete(self, user_id: str, task_id: str) -> bool:
        """
        Delete a task.
        
        Args:
            user_id: User ID who owns the task
            task_id: Task ID to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def get_conflicting_tasks(
        self, 
        user_id: str, 
        start_time: datetime, 
        end_time: datetime,
        exclude_task_id: Optional[str] = None
    ) -> List[Task]:
        """
        Get tasks that conflict with the given time range.
        
        Args:
            user_id: User ID to check conflicts for
            start_time: Start time of the proposed task
            end_time: End time of the proposed task
            exclude_task_id: Task ID to exclude from conflict check
            
        Returns:
            List of conflicting tasks
            
        Raises:
            DatabaseError: If query fails
        """
        pass
    
    @abstractmethod
    async def get_overdue_tasks(self, user_id: str) -> List[Task]:
        """
        Get all overdue tasks for a user.
        
        Args:
            user_id: User ID to get overdue tasks for
            
        Returns:
            List of overdue tasks
            
        Raises:
            DatabaseError: If query fails
        """
        pass
    
    @abstractmethod
    async def get_tasks_in_date_range(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Task]:
        """
        Get tasks within a specific date range.
        
        Args:
            user_id: User ID to get tasks for
            start_date: Range start date
            end_date: Range end date
            
        Returns:
            List of tasks in the date range
            
        Raises:
            DatabaseError: If query fails
        """
        pass
    
    @abstractmethod
    async def bulk_update_status(
        self, 
        user_id: str, 
        task_ids: List[str], 
        new_status: TaskStatus
    ) -> List[Task]:
        """
        Update status for multiple tasks.
        
        Args:
            user_id: User ID who owns the tasks
            task_ids: List of task IDs to update
            new_status: New status to set
            
        Returns:
            List of successfully updated tasks
            
        Raises:
            DatabaseError: If bulk update fails
        """
        pass
    
    @abstractmethod
    async def bulk_delete(self, user_id: str, task_ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple tasks.
        
        Args:
            user_id: User ID who owns the tasks
            task_ids: List of task IDs to delete
            
        Returns:
            Dict mapping task_id to deletion success
            
        Raises:
            DatabaseError: If bulk delete fails
        """
        pass


class SQLAlchemyTaskRepository(ITaskRepository):
    """
    SQLAlchemy implementation of task repository.
    
    This implementation uses raw SQL queries for optimal performance
    while maintaining clean architecture principles.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, task: Task) -> Task:
        """Create a new task in the database."""
        try:
            if not task.id:
                task.id = str(uuid4())
            
            task.created_at = datetime.now()
            task.updated_at = task.created_at
            
            query = text("""
                INSERT INTO tasks (
                    taskid, userid, task_name, task_description, 
                    start_time, end_time, color, status, priority, category,
                    created_at, updated_at
                ) VALUES (
                    :taskid, :userid, :task_name, :task_description,
                    :start_time, :end_time, :color, :status, :priority, :category,
                    :created_at, :updated_at
                )
            """)
            
            await self.session.execute(query, task.to_dict())
            
            logger.debug(f"Task created in database: {task.id}")
            return task
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to create task: {e}")
            raise DatabaseError(f"Task creation failed: {e}")
    
    async def get_by_id(self, user_id: str, task_id: str) -> Optional[Task]:
        """Get a task by ID for a specific user."""
        try:
            query = text("""
                SELECT taskid, userid, task_name, task_description,
                       start_time, end_time, color, status, priority, category,
                       created_at, updated_at
                FROM tasks 
                WHERE taskid = :task_id AND userid = :user_id
            """)
            
            result = await self.session.execute(
                query, 
                {"task_id": task_id, "user_id": user_id}
            )
            row = result.fetchone()
            
            if not row:
                return None
            
            return Task.from_dict(row._asdict())
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            raise DatabaseError(f"Failed to retrieve task: {e}")
    
    async def get_by_user(self, user_id: str, params: TaskQueryParams) -> tuple[List[Task], int]:
        """Get tasks for a user with filtering and pagination."""
        try:
            where_conditions = ["userid = :user_id"]
            query_params = {"user_id": user_id}
            
            if params.status:
                where_conditions.append("status = :status")
                query_params["status"] = params.status.value
            
            if params.priority:
                where_conditions.append("priority = :priority")
                query_params["priority"] = params.priority.value
            
            if params.category:
                where_conditions.append("category = :category")
                query_params["category"] = params.category.value
            
            if params.name_contains:
                where_conditions.append("task_name ILIKE :name_pattern")
                query_params["name_pattern"] = f"%{params.name_contains}%"
            
            if params.start_date:
                where_conditions.append("end_time >= :start_date")
                query_params["start_date"] = params.start_date
            
            if params.end_date:
                where_conditions.append("start_time <= :end_date")
                query_params["end_date"] = params.end_date
            
            where_clause = " AND ".join(where_conditions)
            
            count_query = text(f"""
                SELECT COUNT(*) as total
                FROM tasks
                WHERE {where_clause}
            """)
            
            count_result = await self.session.execute(count_query, query_params)
            total_count = count_result.fetchone()[0]
            
            order_direction = "ASC" if params.sort_order == "asc" else "DESC"
            
            valid_sort_fields = {
                "start_time", "end_time", "task_name", "status", 
                "priority", "category", "created_at", "updated_at"
            }
            sort_field = params.sort_by if params.sort_by in valid_sort_fields else "start_time"
            
            main_query = text(f"""
                SELECT taskid, userid, task_name, task_description,
                       start_time, end_time, color, status, priority, category,
                       created_at, updated_at
                FROM tasks
                WHERE {where_clause}
                ORDER BY {sort_field} {order_direction}
                LIMIT :limit OFFSET :offset
            """)
            
            query_params.update({
                "limit": params.limit,
                "offset": params.offset
            })
            
            result = await self.session.execute(main_query, query_params)
            rows = result.fetchall()
            
            tasks = [Task.from_dict(row._asdict()) for row in rows]
            
            logger.debug(f"Retrieved {len(tasks)} tasks for user {user_id}")
            return tasks, total_count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get tasks for user {user_id}: {e}")
            raise DatabaseError(f"Failed to retrieve tasks: {e}")
    
    async def update(self, task: Task) -> Task:
        """Update an existing task."""
        try:
            task.updated_at = datetime.now()
            
            query = text("""
                UPDATE tasks SET
                    task_name = :task_name,
                    task_description = :task_description,
                    start_time = :start_time,
                    end_time = :end_time,
                    color = :color,
                    status = :status,
                    priority = :priority,
                    category = :category,
                    updated_at = :updated_at
                WHERE taskid = :taskid AND userid = :userid
            """)
            
            result = await self.session.execute(query, task.to_dict())
            
            if result.rowcount == 0:
                raise TaskNotFoundError(f"Task not found: {task.id}")
            
            logger.debug(f"Task updated in database: {task.id}")
            return task
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update task {task.id}: {e}")
            raise DatabaseError(f"Task update failed: {e}")
    
    async def delete(self, user_id: str, task_id: str) -> bool:
        """Delete a task."""
        try:
            query = text("""
                DELETE FROM tasks 
                WHERE taskid = :task_id AND userid = :user_id
            """)
            
            result = await self.session.execute(
                query, 
                {"task_id": task_id, "user_id": user_id}
            )
            
            deleted = result.rowcount > 0
            if deleted:
                logger.debug(f"Task deleted from database: {task_id}")
            
            return deleted
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise DatabaseError(f"Task deletion failed: {e}")
    
    async def get_conflicting_tasks(
        self, 
        user_id: str, 
        start_time: datetime, 
        end_time: datetime,
        exclude_task_id: Optional[str] = None
    ) -> List[Task]:
        """Get tasks that conflict with the given time range."""
        try:
            where_conditions = [
                "userid = :user_id",
                "status IN ('pending', 'in_progress', 'blocked')",
                "start_time < :end_time",
                "end_time > :start_time"
            ]
            
            query_params = {
                "user_id": user_id,
                "start_time": start_time,
                "end_time": end_time
            }
            
            if exclude_task_id:
                where_conditions.append("taskid != :exclude_task_id")
                query_params["exclude_task_id"] = exclude_task_id
            
            where_clause = " AND ".join(where_conditions)
            
            query = text(f"""
                SELECT taskid, userid, task_name, task_description,
                       start_time, end_time, color, status, priority, category,
                       created_at, updated_at
                FROM tasks
                WHERE {where_clause}
                ORDER BY start_time
            """)
            
            result = await self.session.execute(query, query_params)
            rows = result.fetchall()
            
            tasks = [Task.from_dict(row._asdict()) for row in rows]
            
            logger.debug(f"Found {len(tasks)} conflicting tasks for user {user_id}")
            return tasks
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get conflicting tasks: {e}")
            raise DatabaseError(f"Failed to check conflicts: {e}")
    
    async def get_overdue_tasks(self, user_id: str) -> List[Task]:
        """Get all overdue tasks for a user."""
        try:
            query = text("""
                SELECT taskid, userid, task_name, task_description,
                       start_time, end_time, color, status, priority, category,
                       created_at, updated_at
                FROM tasks
                WHERE userid = :user_id
                    AND status IN ('pending', 'in_progress', 'blocked')
                    AND end_time < NOW()
                ORDER BY end_time
            """)
            
            result = await self.session.execute(query, {"user_id": user_id})
            rows = result.fetchall()
            
            tasks = [Task.from_dict(row._asdict()) for row in rows]
            
            logger.debug(f"Found {len(tasks)} overdue tasks for user {user_id}")
            return tasks
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get overdue tasks: {e}")
            raise DatabaseError(f"Failed to retrieve overdue tasks: {e}")
    
    async def get_tasks_in_date_range(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Task]:
        """Get tasks within a specific date range."""
        try:
            query = text("""
                SELECT taskid, userid, task_name, task_description,
                       start_time, end_time, color, status, priority, category,
                       created_at, updated_at
                FROM tasks
                WHERE userid = :user_id
                    AND start_time < :end_date
                    AND end_time > :start_date
                ORDER BY start_time
            """)
            
            result = await self.session.execute(query, {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            })
            rows = result.fetchall()
            
            tasks = [Task.from_dict(row._asdict()) for row in rows]
            
            logger.debug(f"Found {len(tasks)} tasks in date range for user {user_id}")
            return tasks
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get tasks in date range: {e}")
            raise DatabaseError(f"Failed to retrieve tasks in date range: {e}")
    
    async def bulk_update_status(
        self, 
        user_id: str, 
        task_ids: List[str], 
        new_status: TaskStatus
    ) -> List[Task]:
        """Update status for multiple tasks."""
        try:
            if not task_ids:
                return []
            
            placeholders = ",".join([f":task_id_{i}" for i in range(len(task_ids))])
            query_params = {"user_id": user_id, "new_status": new_status.value}
            
            for i, task_id in enumerate(task_ids):
                query_params[f"task_id_{i}"] = task_id
            
            update_query = text(f"""
                UPDATE tasks SET
                    status = :new_status,
                    updated_at = NOW()
                WHERE userid = :user_id
                    AND taskid IN ({placeholders})
            """)
            
            await self.session.execute(update_query, query_params)
            
            select_query = text(f"""
                SELECT taskid, userid, task_name, task_description,
                       start_time, end_time, color, status, priority, category,
                       created_at, updated_at
                FROM tasks
                WHERE userid = :user_id
                    AND taskid IN ({placeholders})
            """)
            
            result = await self.session.execute(select_query, query_params)
            rows = result.fetchall()
            
            tasks = [Task.from_dict(row._asdict()) for row in rows]
            
            logger.debug(f"Bulk updated {len(tasks)} tasks to status {new_status.value}")
            return tasks
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to bulk update task status: {e}")
            raise DatabaseError(f"Bulk status update failed: {e}")
    
    async def bulk_delete(self, user_id: str, task_ids: List[str]) -> Dict[str, bool]:
        """Delete multiple tasks."""
        try:
            if not task_ids:
                return {}
            
            results = {}
                
            for task_id in task_ids:
                try:
                    deleted = await self.delete(user_id, task_id)
                    results[task_id] = deleted
                except Exception as e:
                    logger.warning(f"Failed to delete task {task_id}: {e}")
                    results[task_id] = False
            
            success_count = sum(1 for success in results.values() if success)
            logger.debug(f"Bulk deleted {success_count}/{len(task_ids)} tasks")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to bulk delete tasks: {e}")
            raise DatabaseError(f"Bulk delete failed: {e}") 