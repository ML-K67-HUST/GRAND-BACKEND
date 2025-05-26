"""
Custom exceptions for the TimeNest Backend application.

This module provides a comprehensive set of exceptions that map to HTTP status codes
and provide consistent error responses across the application.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime


class BaseTimeNestException(Exception):
    """
    Base exception for all TimeNest application exceptions.
    
    All custom exceptions should inherit from this class to ensure
    consistent error handling and response formatting.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.headers = headers or {}
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp.isoformat()
            }
        }


# 4xx Client Error Exceptions

class ValidationError(BaseTimeNestException):
    """Raised when request validation fails (400 Bad Request)"""
    
    def __init__(
        self, 
        message: str = "Validation failed",
        field_errors: Optional[List[Dict[str, Any]]] = None
    ):
        details = {"field_errors": field_errors} if field_errors else {}
        super().__init__(message, 400, "VALIDATION_ERROR", details)


class AuthenticationError(BaseTimeNestException):
    """Raised when authentication fails (401 Unauthorized)"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401, "AUTHENTICATION_ERROR")


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired"""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message)
        self.error_code = "TOKEN_EXPIRED"


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid"""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)
        self.error_code = "INVALID_TOKEN"


class AuthorizationError(BaseTimeNestException):
    """Raised when user lacks permission (403 Forbidden)"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, 403, "AUTHORIZATION_ERROR")


class NotFoundError(BaseTimeNestException):
    """Raised when a resource is not found (404 Not Found)"""
    
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} with identifier '{identifier}' not found"
        details = {"resource": resource, "identifier": identifier}
        super().__init__(message, 404, "RESOURCE_NOT_FOUND", details)


class ConflictError(BaseTimeNestException):
    """Raised when there's a conflict with current state (409 Conflict)"""
    
    def __init__(self, message: str, conflicting_resource: Optional[str] = None):
        details = {"conflicting_resource": conflicting_resource} if conflicting_resource else {}
        super().__init__(message, 409, "CONFLICT_ERROR", details)


class RateLimitExceededError(BaseTimeNestException):
    """Raised when rate limit is exceeded (429 Too Many Requests)"""
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        headers = {"Retry-After": str(retry_after)} if retry_after else {}
        super().__init__(message, 429, "RATE_LIMIT_EXCEEDED", headers=headers)


# 5xx Server Error Exceptions

class DatabaseError(BaseTimeNestException):
    """Raised when database operation fails (500 Internal Server Error)"""
    
    def __init__(
        self, 
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        table: Optional[str] = None
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        super().__init__(message, 500, "DATABASE_ERROR", details)


class ExternalServiceError(BaseTimeNestException):
    """Raised when external service call fails (502 Bad Gateway)"""
    
    def __init__(
        self, 
        service: str, 
        message: str = "External service error",
        status_code: Optional[int] = None
    ):
        full_message = f"{service}: {message}"
        details = {"service": service}
        if status_code:
            details["external_status_code"] = status_code
        super().__init__(full_message, 502, "EXTERNAL_SERVICE_ERROR", details)


class ServiceUnavailableError(BaseTimeNestException):
    """Raised when service is temporarily unavailable (503 Service Unavailable)"""
    
    def __init__(
        self, 
        message: str = "Service temporarily unavailable",
        retry_after: Optional[int] = None
    ):
        headers = {"Retry-After": str(retry_after)} if retry_after else {}
        super().__init__(message, 503, "SERVICE_UNAVAILABLE", headers=headers)


# Business Logic Exceptions

class TaskValidationError(ValidationError):
    """Raised when task-specific validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        field_errors = [{"field": field, "message": message}] if field else None
        super().__init__(f"Task validation error: {message}", field_errors)


class ScheduleConflictError(ConflictError):
    """Raised when task schedule conflicts with existing tasks"""
    
    def __init__(self, conflicting_task_id: str):
        message = "Task schedule conflicts with existing task"
        super().__init__(message, conflicting_task_id)
        self.error_code = "SCHEDULE_CONFLICT"


class UserNotFoundError(NotFoundError):
    """Raised when user is not found"""
    
    def __init__(self, user_id: str):
        super().__init__("User", user_id)


class TaskNotFoundError(NotFoundError):
    """Raised when task is not found"""
    
    def __init__(self, task_id: str):
        super().__init__("Task", task_id)


class EmailAlreadyExistsError(ConflictError):
    """Raised when trying to register with existing email"""
    
    def __init__(self, email: str):
        message = f"Email '{email}' is already registered"
        super().__init__(message, email)
        self.error_code = "EMAIL_ALREADY_EXISTS"


class UsernameAlreadyExistsError(ConflictError):
    """Raised when trying to register with existing username"""
    
    def __init__(self, username: str):
        message = f"Username '{username}' is already taken"
        super().__init__(message, username)
        self.error_code = "USERNAME_ALREADY_EXISTS"


class PasswordValidationError(ValidationError):
    """Raised when password doesn't meet requirements"""
    
    def __init__(self, requirements: List[str]):
        message = "Password doesn't meet requirements"
        details = {"requirements": requirements}
        super().__init__(message, [{"field": "password", "message": message}])
        self.details.update(details)


class OTPExpiredError(ValidationError):
    """Raised when OTP has expired"""
    
    def __init__(self):
        super().__init__("OTP has expired")
        self.error_code = "OTP_EXPIRED"


class OTPInvalidError(ValidationError):
    """Raised when OTP is invalid"""
    
    def __init__(self):
        super().__init__("Invalid OTP")
        self.error_code = "OTP_INVALID" 