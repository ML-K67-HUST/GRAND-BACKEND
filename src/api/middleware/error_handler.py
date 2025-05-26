"""
Error handling middleware for centralized error processing and logging.
"""

import logging
import traceback
from typing import Callable, Dict, Any, Optional

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.exceptions import BaseTimeNestException

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Centralized error handling middleware for consistent error responses.
    """
    
    def __init__(self, app, debug: bool = False):
        super().__init__(app)
        self.debug = debug
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle any exceptions that occur.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware or endpoint in the chain
            
        Returns:
            Response object with proper error handling
        """
        try:
            response = await call_next(request)
            return response
            
        except BaseTimeNestException as exc:
            # Handle our custom application exceptions
            logger.warning(f"Application error: {exc}")
            return self._create_error_response(
                status_code=exc.status_code,
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, 'request_id', None)
            )
            
        except HTTPException as exc:
            # Handle FastAPI HTTP exceptions
            logger.warning(f"HTTP error: {exc.detail}")
            return self._create_error_response(
                status_code=exc.status_code,
                error_code="HTTP_ERROR",
                message=exc.detail,
                request_id=getattr(request.state, 'request_id', None)
            )
            
        except Exception as exc:
            # Handle unexpected exceptions
            error_id = getattr(request.state, 'request_id', 'unknown')
            logger.error(
                f"Unexpected error (ID: {error_id}): {exc}",
                exc_info=True
            )
            
            # Don't expose internal errors in production
            if self.debug:
                message = str(exc)
                details = {
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc()
                }
            else:
                message = "Internal server error"
                details = {"error_id": error_id}
            
            return self._create_error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="INTERNAL_ERROR",
                message=message,
                details=details,
                request_id=error_id
            )
    
    def _create_error_response(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> JSONResponse:
        """
        Create standardized error response.
        
        Args:
            status_code: HTTP status code
            error_code: Application-specific error code
            message: Error message
            details: Additional error details
            request_id: Request identifier for tracking
            
        Returns:
            JSONResponse with error details
        """
        error_response = {
            "error": {
                "code": error_code,
                "message": message,
                "status_code": status_code
            }
        }
        
        if details:
            error_response["error"]["details"] = details
            
        if request_id:
            error_response["error"]["request_id"] = request_id
            
        return JSONResponse(
            status_code=status_code,
            content=error_response
        ) 