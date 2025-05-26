"""
Authentication API endpoints with enhanced security.

This module provides:
- User login/logout with JWT tokens
- Token refresh mechanism
- Password validation and security
- User registration with validation
- OAuth integration ready
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, Body, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field, validator

from services.auth_service import AuthService, get_auth_service_dependency
from api.middleware.authentication import get_current_user, require_auth
from core.exceptions import (
    AuthenticationError,
    ValidationError,
    TokenExpiredError,
    InvalidTokenError,
    PasswordValidationError
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Request/Response Models

class LoginRequest(BaseModel):
    """User login request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "your_password"
            }
        }


class RegisterRequest(BaseModel):
    """User registration request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    confirm_password: str = Field(..., description="Password confirmation")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric (underscores and hyphens allowed)')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "username": "newuser123",
                "first_name": "John",
                "last_name": "Doe"
            }
        }


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class RefreshTokenRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str = Field(..., description="Valid refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class LogoutRequest(BaseModel):
    """Logout request model"""
    refresh_token: str = Field(..., description="Refresh token to blacklist")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class UserResponse(BaseModel):
    """User profile response model"""
    user_id: str = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    is_active: bool = Field(default=True, description="Account status")
    last_login: str = Field(None, description="Last login timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "is_active": True,
                "last_login": "2024-01-15T10:30:00Z"
            }
        }


# Authentication Endpoints

@router.post(
    "/login",
    response_model=Dict[str, Any],
    summary="User login",
    description="Authenticate user and return JWT tokens"
)
async def login(
    request: LoginRequest = Body(..., description="Login credentials"),
    auth_service: AuthService = Depends(get_auth_service_dependency)
) -> Dict[str, Any]:
    """
    Authenticate user with email and password.
    
    Returns:
    - User profile information
    - JWT access token (30 minutes expiration)
    - JWT refresh token (7 days expiration)
    
    The access token should be included in the Authorization header
    for protected endpoints: `Authorization: Bearer <access_token>`
    """
    try:
        user_data, access_token, refresh_token = await auth_service.authenticate_user(
            request.email, request.password
        )
        
        logger.info(f"User logged in successfully: {request.email}")
        
        return {
            "user": user_data,
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": auth_service.access_token_expire_minutes * 60
            },
            "message": "Login successful"
        }
        
    except AuthenticationError as e:
        logger.warning(f"Login failed for {request.email}: {e.message}")
        raise


@router.post(
    "/register",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="User registration",
    description="Register a new user account"
)
async def register(
    request: RegisterRequest = Body(..., description="Registration data"),
    auth_service: AuthService = Depends(get_auth_service_dependency)
) -> Dict[str, Any]:
    """
    Register a new user account.
    
    Password requirements:
    - At least 8 characters long
    - Contains uppercase and lowercase letters
    - Contains at least one number
    - Contains at least one special character
    
    Returns user profile and authentication tokens.
    """
    try:
        # Validate password strength
        is_valid, requirements = auth_service.validate_password_strength(request.password)
        if not is_valid:
            raise PasswordValidationError(requirements)
        
        # Create user in database
        user_data, access_token, refresh_token = await auth_service.register_user(
            email=request.email,
            password=request.password,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name
        )
        
        logger.info(f"User registered successfully: {request.email}")
        
        return {
            "message": "Registration successful",
            "user": user_data,
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": auth_service.access_token_expire_minutes * 60
            }
        }
        
    except PasswordValidationError as e:
        logger.warning(f"Registration failed - weak password: {request.email}")
        raise
    except ValidationError as e:
        logger.warning(f"Registration failed - validation: {e.message}")
        raise


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
async def refresh_token(
    request: RefreshTokenRequest = Body(..., description="Refresh token"),
    auth_service: AuthService = Depends(get_auth_service_dependency)
) -> TokenResponse:
    """
    Refresh the access token using a valid refresh token.
    
    The old refresh token will be blacklisted and a new one will be issued.
    This implements token rotation for enhanced security.
    """
    try:
        new_access_token, new_refresh_token = await auth_service.refresh_access_token(
            request.refresh_token
        )
        
        logger.info("Token refresh successful")
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=auth_service.access_token_expire_minutes * 60
        )
        
    except (TokenExpiredError, InvalidTokenError) as e:
        logger.warning(f"Token refresh failed: {e.message}")
        raise


@router.post(
    "/logout",
    summary="User logout",
    description="Logout user and blacklist tokens"
)
async def logout(
    request: LogoutRequest = Body(..., description="Logout data"),
    current_user: Dict[str, Any] = Depends(require_auth),
    auth_service: AuthService = Depends(get_auth_service_dependency)
) -> Dict[str, str]:
    """
    Logout the current user and blacklist their tokens.
    
    Both the access token (from Authorization header) and refresh token
    (from request body) will be blacklisted to prevent further use.
    """
    try:
        # Extract access token from request state (set by auth middleware)
        # In a real implementation, you'd get this from the Authorization header
        access_token = "placeholder"  # TODO: Extract from request
        
        await auth_service.logout_user(access_token, request.refresh_token)
        
        logger.info(f"User logged out: {current_user['user_id']}")
        
        return {"message": "Logout successful"}
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise AuthenticationError("Logout failed")


@router.get(
    "/profile",
    response_model=UserResponse,
    summary="Get user profile",
    description="Get current user profile information"
)
async def get_profile(
    current_user: Dict[str, Any] = Depends(require_auth)
) -> UserResponse:
    """
    Get the current authenticated user's profile information.
    
    Returns user details excluding sensitive information like password hashes.
    """
    # TODO: Fetch complete user profile from database
    # For now, return data from JWT token
    
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        username=current_user.get("username", ""),
        first_name=current_user.get("first_name", ""),
        last_name=current_user.get("last_name", ""),
        last_login=current_user.get("last_login")
    )


@router.post(
    "/validate-token",
    summary="Validate access token",
    description="Validate if an access token is valid and not expired"
)
async def validate_token(
    current_user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Validate the current access token.
    
    This endpoint can be used by other services to validate tokens
    without needing to implement JWT validation themselves.
    """
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "expires_at": current_user.get("expires_at"),
        "issued_at": current_user.get("issued_at")
    }


# Password Management Endpoints

@router.post(
    "/validate-password",
    summary="Validate password strength",
    description="Check if a password meets security requirements"
)
async def validate_password(
    password: str = Body(..., embed=True, description="Password to validate"),
    auth_service: AuthService = Depends(get_auth_service_dependency)
) -> Dict[str, Any]:
    """
    Validate password strength against security requirements.
    
    Returns validation result and list of requirements if password is weak.
    Useful for client-side password validation.
    """
    is_valid, requirements = auth_service.validate_password_strength(password)
    
    return {
        "valid": is_valid,
        "requirements": requirements if not is_valid else [],
        "message": "Password meets all requirements" if is_valid else "Password does not meet requirements"
    }


# Health Check for Auth Service

@router.get(
    "/health",
    summary="Authentication service health check",
    description="Check if authentication service is operational"
)
async def auth_health_check() -> Dict[str, str]:
    """
    Health check endpoint for the authentication service.
    
    Returns service status and version information.
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "1.0.0",
        "message": "Authentication service is operational"
    } 