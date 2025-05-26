"""
Task models with comprehensive validation and type safety.

This module provides:
- Task domain models with strong validation
- Request/Response schemas
- Enum definitions for task properties
- Utility methods for data transformation
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator, field_validator
from pydantic.color import Color


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    
    @classmethod
    def get_active_statuses(cls) -> List[str]:
        """Get list of active (non-final) task statuses"""
        return [cls.PENDING.value, cls.IN_PROGRESS.value, cls.BLOCKED.value]
    
    @classmethod
    def get_final_statuses(cls) -> List[str]:
        """Get list of final task statuses"""
        return [cls.COMPLETED.value, cls.CANCELLED.value]


class TaskPriority(int, Enum):
    """Task priority enumeration"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5
    
    @classmethod
    def get_display_name(cls, priority: int) -> str:
        """Get display name for priority level"""
        mapping = {
            1: "Low",
            2: "Medium", 
            3: "High",
            4: "Urgent",
            5: "Critical"
        }
        return mapping.get(priority, "Unknown")


class TaskCategory(str, Enum):
    """Task category enumeration"""
    WORK = "work"
    PERSONAL = "personal"
    HEALTH = "health"
    EDUCATION = "education"
    FINANCE = "finance"
    SOCIAL = "social"
    HOUSEHOLD = "household"
    OTHER = "other"


# Base Models

class TaskBase(BaseModel):
    """Base task model with common validation"""
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="Task name"
    )
    description: Optional[str] = Field(
        None, 
        max_length=2000, 
        description="Task description"
    )
    start_time: datetime = Field(
        ..., 
        description="Task start time (ISO format with timezone)"
    )
    end_time: datetime = Field(
        ..., 
        description="Task end time (ISO format with timezone)"
    )
    color: str = Field(
        "#3498DB", 
        pattern=r"^#[0-9A-Fa-f]{6}$", 
        description="Task color in hex format"
    )
    status: TaskStatus = Field(
        TaskStatus.PENDING, 
        description="Task status"
    )
    priority: TaskPriority = Field(
        TaskPriority.MEDIUM, 
        description="Task priority level"
    )
    category: TaskCategory = Field(
        TaskCategory.OTHER, 
        description="Task category"
    )
    
    # Validation methods
    @field_validator('start_time', 'end_time')
    def validate_datetime_timezone(cls, v):
        """Ensure datetime has timezone info"""
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                raise ValueError('Invalid datetime format')
        
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            return v
        
        raise ValueError('Invalid datetime type')
    
    @field_validator('end_time')
    def validate_end_time_after_start(cls, v, values):
        """Ensure end_time is after start_time"""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v
    
    @field_validator('name')
    def validate_name_not_empty(cls, v):
        """Ensure name is not just whitespace"""
        if not v.strip():
            raise ValueError('Task name cannot be empty')
        return v.strip()
    
    @field_validator('description')
    def validate_description(cls, v):
        """Clean up description"""
        if v:
            return v.strip() if v.strip() else None
        return v
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Request Models

class TaskCreateRequest(TaskBase):
    """Model for creating a new task"""
    
    @model_validator(mode="after")
    def validate_task_creation(cls, values):
        """Additional validations for task creation"""
        start_time = values.get('start_time')
        end_time = values.get('end_time')
        
        if start_time and end_time:
            # Check if task duration is reasonable (not more than 7 days)
            duration = end_time - start_time
            if duration.days > 7:
                raise ValueError('Task duration cannot exceed 7 days')
            
            # Check if task is not too short (at least 5 minutes)
            if duration.total_seconds() < 300:  # 5 minutes
                raise ValueError('Task duration must be at least 5 minutes')
        
        return values
    
    class Config(TaskBase.Config):
        json_schema_extra = {
            "example": {
                "name": "Complete project proposal",
                "description": "Write and review the Q1 project proposal document",
                "start_time": "2024-01-15T09:00:00Z",
                "end_time": "2024-01-15T17:00:00Z",
                "color": "#3498DB",
                "status": "pending",
                "priority": 2,
                "category": "work"
            }
        }


class TaskUpdateRequest(BaseModel):
    """Model for updating an existing task"""
    
    name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=255
    )
    description: Optional[str] = Field(
        None, 
        max_length=2000
    )
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    color: Optional[str] = Field(
        None, 
        pattern=r"^#[0-9A-Fa-f]{6}$"
    )
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    category: Optional[TaskCategory] = None
    
    @field_validator('start_time', 'end_time')
    def validate_datetime_timezone(cls, v):
        """Ensure datetime has timezone info"""
        if v is None:
            return v
        return TaskBase.__fields__['start_time'].type_.validate_datetime_timezone(v)
    
    @model_validator(mode="after")
    def validate_time_consistency(cls, values):
        """Validate time consistency when both start and end times are provided"""
        start_time = values.get('start_time')
        end_time = values.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise ValueError('End time must be after start time')
        
        return values
    
    class Config:
        use_enum_values = True


class TaskQueryParams(BaseModel):
    """Model for task query parameters"""
    
    # Filtering
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    category: Optional[TaskCategory] = None
    name_contains: Optional[str] = Field(None, max_length=100)
    
    # Date range filtering
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Pagination
    offset: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Number of records to return")
    
    # Sorting
    sort_by: str = Field("start_time", description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")
    
    @field_validator('start_date', 'end_date')
    def validate_dates(cls, v):
        """Validate date formats"""
        if v is None:
            return v
        return TaskBase.__fields__['start_time'].type_.validate_datetime_timezone(v)
    
    @model_validator(mode="after")
    def validate_date_range(cls, values):
        """Validate date range"""
        start_date = values.get('start_date')
        end_date = values.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValueError('End date must be after start date')
        
        return values


# Response Models

class TaskResponse(TaskBase):
    """Model for task response"""
    
    id: str = Field(..., description="Unique task identifier")
    user_id: str = Field(..., description="User ID who owns the task")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Computed fields
    duration_minutes: int = Field(..., description="Task duration in minutes")
    is_overdue: bool = Field(..., description="Whether task is overdue")
    is_active: bool = Field(..., description="Whether task is in active status")
    
    @field_validator('duration_minutes')
    def calculate_duration(cls, v, values):
        """Calculate task duration in minutes"""
        start_time = values.get('start_time')
        end_time = values.get('end_time')
        
        if start_time and end_time:
            duration = end_time - start_time
            return int(duration.total_seconds() / 60)
        return 0
    
    @field_validator('is_overdue')
    def calculate_is_overdue(cls, v, values):
        """Check if task is overdue"""
        end_time = values.get('end_time')
        status = values.get('status')
        
        if end_time and status in TaskStatus.get_active_statuses():
            return datetime.now(timezone.utc) > end_time
        return False
    
    @field_validator('is_active')
    def calculate_is_active(cls, v, values):
        """Check if task is in active status"""
        status = values.get('status')
        return status in TaskStatus.get_active_statuses()
    
    @classmethod
    def from_db_model(cls, db_task: Dict[str, Any]) -> 'TaskResponse':
        """Create TaskResponse from database model"""
        return cls(
            id=str(db_task['taskid']),
            user_id=str(db_task['userid']),
            name=db_task['task_name'],
            description=db_task.get('task_description'),
            start_time=db_task['start_time'],
            end_time=db_task['end_time'],
            color=db_task.get('color', '#3498DB'),
            status=db_task.get('status', TaskStatus.PENDING),
            priority=db_task.get('priority', TaskPriority.MEDIUM),
            category=db_task.get('category', TaskCategory.OTHER),
            created_at=db_task.get('created_at', datetime.now(timezone.utc)),
            updated_at=db_task.get('updated_at', datetime.now(timezone.utc))
        )
    
    class Config(TaskBase.Config):
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user123",
                "name": "Complete project proposal",
                "description": "Write and review the Q1 project proposal document",
                "start_time": "2024-01-15T09:00:00Z",
                "end_time": "2024-01-15T17:00:00Z",
                "color": "#3498DB",
                "status": "pending",
                "priority": 2,
                "category": "work",
                "created_at": "2024-01-10T10:00:00Z",
                "updated_at": "2024-01-10T10:00:00Z",
                "duration_minutes": 480,
                "is_overdue": False,
                "is_active": True
            }
        }


class TaskListResponse(BaseModel):
    """Model for task list response"""
    
    tasks: List[TaskResponse] = Field(..., description="List of tasks")
    total_count: int = Field(..., description="Total number of tasks")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Current limit")
    has_more: bool = Field(..., description="Whether there are more tasks")
    
    # Summary statistics
    summary: Dict[str, Any] = Field(..., description="Task summary statistics")
    
    @field_validator('summary')
    def calculate_summary(cls, v, values):
        """Calculate task summary statistics"""
        tasks = values.get('tasks', [])
        
        if not tasks:
            return {
                "total": 0,
                "by_status": {},
                "by_priority": {},
                "overdue_count": 0,
                "active_count": 0
            }
        
        # Count by status
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(1 for t in tasks if t.status == status)
        
        # Count by priority  
        priority_counts = {}
        for priority in TaskPriority:
            priority_counts[priority.value] = sum(1 for t in tasks if t.priority == priority)
        
        return {
            "total": len(tasks),
            "by_status": status_counts,
            "by_priority": priority_counts,
            "overdue_count": sum(1 for t in tasks if t.is_overdue),
            "active_count": sum(1 for t in tasks if t.is_active)
        }
    
    @field_validator('has_more')
    def calculate_has_more(cls, v, values):
        """Calculate if there are more tasks"""
        total_count = values.get('total_count', 0)
        offset = values.get('offset', 0)
        limit = values.get('limit', 100)
        
        return (offset + limit) < total_count
    
    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [],
                "total_count": 50,
                "offset": 0,
                "limit": 20,
                "has_more": True,
                "summary": {
                    "total": 20,
                    "by_status": {
                        "pending": 10,
                        "in_progress": 5,
                        "completed": 3,
                        "cancelled": 2
                    },
                    "by_priority": {
                        "1": 5,
                        "2": 8,
                        "3": 4,
                        "4": 2,
                        "5": 1
                    },
                    "overdue_count": 3,
                    "active_count": 15
                }
            }
        }


# Domain Models (for business logic)

class Task(TaskBase):
    """Domain model for task entity"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = Field(...)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update_fields(self, **kwargs) -> None:
        """Update task fields and set updated_at timestamp"""
        for field, value in kwargs.items():
            if hasattr(self, field) and value is not None:
                setattr(self, field, value)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for database storage"""
        return {
            'taskid': self.id,
            'userid': self.user_id,
            'task_name': self.name,
            'task_description': self.description,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'color': self.color,
            'status': self.status.value,
            'priority': self.priority.value,
            'category': self.category.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create Task from dictionary (e.g., from database)"""
        return cls(
            id=str(data['taskid']),
            user_id=str(data['userid']),
            name=data['task_name'],
            description=data.get('task_description'),
            start_time=data['start_time'],
            end_time=data['end_time'],
            color=data.get('color', '#3498DB'),
            status=data.get('status', TaskStatus.PENDING),
            priority=data.get('priority', TaskPriority.MEDIUM),
            category=data.get('category', TaskCategory.OTHER),
            created_at=data.get('created_at', datetime.now(timezone.utc)),
            updated_at=data.get('updated_at', datetime.now(timezone.utc))
        )