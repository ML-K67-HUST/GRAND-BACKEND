"""
Authentication middleware for JWT token validation and user context.

This middleware provides:
- JWT token validation
- User context injection
- Route protection
- Token refresh handling
- Rate limiting by user
"""

import logging
from typing import Optional, Set, Callable
from datetime import datetime, timezone

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from core.exceptions import (
    AuthenticationError, 
    TokenExpiredError, 
    InvalidTokenError,
    RateLimitExceededError
)
from services.auth_service import AuthService
from core.config import settings

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT authentication and user context injection.
    """
    
    def __init__(
        self, 
        app,
        auth_service: AuthService,
        exclude_paths: Optional[Set[str]] = None,
        exclude_prefixes: Optional[Set[str]] = None
    ):
        super().__init__(app)
        self.auth_service = auth_service
        self.security = HTTPBearer(auto_error=False)
        
        # Default excluded paths (public endpoints)
        self.exclude_paths = exclude_paths or {
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/auth/login",
            "/auth/register",
            "/auth/google",
            "/auth/refresh"
        }
        
        # Excluded path prefixes
        self.exclude_prefixes = exclude_prefixes or {
            "/static",
            "/api/v1/auth"
        }
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Handle authentication for incoming requests.
        """
        # Check if path should be excluded from authentication
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        try:
            # Extract and validate token
            user_context = await self._authenticate_request(request)
            
            # Inject user context into request state
            request.state.user = user_context
            request.state.user_id = user_context["user_id"]
            request.state.is_authenticated = True
            
            # Check rate limits for authenticated user
            await self._check_rate_limits(request, user_context["user_id"])
            
            # Log successful authentication
            logger.debug(
                f"Authenticated request - User: {user_context['user_id']} - "
                f"Path: {request.url.path} - "
                f"Request ID: {getattr(request.state, 'request_id', 'unknown')}"
            )
            
            response = await call_next(request)
            return response
            
        except (AuthenticationError, TokenExpiredError, InvalidTokenError) as exc:
            logger.warning(
                f"Authentication failed - Path: {request.url.path} - "
                f"Error: {exc.message} - "
                f"Request ID: {getattr(request.state, 'request_id', 'unknown')}"
            )
            raise exc
            
        except Exception as exc:
            logger.error(
                f"Unexpected authentication error - Path: {request.url.path} - "
                f"Error: {str(exc)}",
                exc_info=True
            )
            raise AuthenticationError("Authentication service error")
    
    def _should_exclude_path(self, path: str) -> bool:
        """
        Check if path should be excluded from authentication.
        """
        # Check exact path matches
        if path in self.exclude_paths:
            return True
        
        # Check prefix matches
        for prefix in self.exclude_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    async def _authenticate_request(self, request: Request) -> dict:
        """
        Extract token from request and validate it.
        
        Returns:
            dict: User context with user_id, email, etc.
        """
        # Extract token from Authorization header
        token = await self._extract_token(request)
        
        if not token:
            raise AuthenticationError("Missing authentication token")
        
        # Validate token and get user context
        try:
            user_context = await self.auth_service.validate_access_token(token)
            return user_context
            
        except TokenExpiredError:
            raise TokenExpiredError("Access token has expired")
            
        except InvalidTokenError:
            raise InvalidTokenError("Invalid access token")
            
        except Exception as exc:
            logger.error(f"Token validation error: {exc}")
            raise AuthenticationError("Token validation failed")
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request headers.
        
        Supports:
        - Authorization: Bearer <token>
        - Authorization: <token>
        
        Returns:
            str: JWT token or None if not found
        """
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # Handle "Bearer <token>" format
            if auth_header.startswith("Bearer "):
                return auth_header[7:]  # Remove "Bearer " prefix
            
            # Handle direct token format
            elif not auth_header.startswith("Basic"):
                return auth_header
        
        # Try X-Access-Token header (alternative)
        x_token = request.headers.get("X-Access-Token")
        if x_token:
            return x_token
        
        return None
    
    async def _check_rate_limits(self, request: Request, user_id: str) -> None:
        """
        Check rate limits for authenticated user.
        
        Args:
            request: FastAPI request object
            user_id: Authenticated user ID
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        if not settings.security.rate_limit_enabled:
            return
        
        # Rate limiting logic would go here
        # For now, we'll implement a simple in-memory rate limiter
        # In production, you'd use Redis or similar
        
        # This is a placeholder - implement proper rate limiting
        # based on your requirements
        pass


class OptionalAuthenticationMiddleware(AuthenticationMiddleware):
    """
    Middleware that provides optional authentication.
    
    Unlike the base AuthenticationMiddleware, this one:
    - Doesn't raise exceptions for missing/invalid tokens
    - Sets request.state.is_authenticated = False for unauthenticated requests
    - Allows the request to continue
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Handle optional authentication for incoming requests.
        """
        # Check if path should be excluded
        if self._should_exclude_path(request.url.path):
            request.state.is_authenticated = False
            return await call_next(request)
        
        try:
            # Try to authenticate
            user_context = await self._authenticate_request(request)
            
            # Inject user context
            request.state.user = user_context
            request.state.user_id = user_context["user_id"]
            request.state.is_authenticated = True
            
            logger.debug(f"Optional auth successful - User: {user_context['user_id']}")
            
        except (AuthenticationError, TokenExpiredError, InvalidTokenError):
            # Authentication failed, but continue without user context
            request.state.user = None
            request.state.user_id = None
            request.state.is_authenticated = False
            
            logger.debug(f"Optional auth failed - continuing without authentication")
            
        except Exception as exc:
            # Unexpected error, log but continue
            logger.warning(f"Optional auth error: {exc}")
            request.state.user = None
            request.state.user_id = None
            request.state.is_authenticated = False
        
        return await call_next(request)


# Dependency for route-level authentication
async def require_auth(request: Request) -> dict:
    """
    FastAPI dependency that requires authentication.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(require_auth)):
            return {"user_id": user["user_id"]}
    
    Returns:
        dict: User context
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    if not getattr(request.state, 'is_authenticated', False):
        raise AuthenticationError("Authentication required")
    
    return request.state.user


async def get_current_user(request: Request) -> Optional[dict]:
    """
    FastAPI dependency that returns current user if authenticated.
    
    Usage:
        @app.get("/profile")
        async def profile(user: Optional[dict] = Depends(get_current_user)):
            if user:
                return {"message": f"Hello {user['email']}"}
            return {"message": "Hello anonymous user"}
    
    Returns:
        dict or None: User context if authenticated, None otherwise
    """
    if getattr(request.state, 'is_authenticated', False):
        return request.state.user
    return None


async def get_current_user_id(request: Request) -> Optional[str]:
    """
    FastAPI dependency that returns current user ID if authenticated.
    
    Returns:
        str or None: User ID if authenticated, None otherwise
    """
    if getattr(request.state, 'is_authenticated', False):
        return request.state.user_id
    return None 