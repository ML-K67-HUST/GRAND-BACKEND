"""
Main FastAPI application with clean architecture integration.

This module provides:
- FastAPI app configuration with middleware
- API router integration
- Database lifecycle management
- Error handling and logging
- OpenAPI documentation
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi


from core.config import settings
from core.exceptions import BaseTimeNestException

from infrastructure.database.connection import startup_database, shutdown_database

from api.middleware.error_handler import ErrorHandlerMiddleware
from api.middleware.authentication import AuthenticationMiddleware, OptionalAuthenticationMiddleware
from services.auth_service import get_auth_service

from api.endpoints.tasks import router as tasks_router
from api.endpoints.auth import router as auth_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.value),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log') if not settings.debug else logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment.value}")
    logger.info(f"Debug mode: {settings.debug}")
    
    try:
        await startup_database()
        logger.info("Database initialized successfully")
   
        
        yield 
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        logger.info("Shutting down application")
        
        try:
            await shutdown_database()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## TimeNest Backend API

    A comprehensive task management backend with clean architecture.

    ### Features
    - **Authentication**: JWT-based authentication with refresh tokens
    - **Task Management**: Full CRUD operations with schedule conflict detection
    - **Advanced Filtering**: Search and filter tasks by multiple criteria
    - **Statistics**: Comprehensive task analytics and reporting
    - **Bulk Operations**: Efficient bulk task operations
    - **Real-time**: WebSocket support for real-time updates (coming soon)

    ### Security
    - JWT tokens with blacklisting support
    - Password strength validation
    - Rate limiting and CORS protection
    - Input validation and sanitization

    ### Architecture
    - Clean Architecture with separation of concerns
    - Repository pattern for data access
    - Service layer for business logic
    - Comprehensive error handling
    - Async/await throughout for performance
    """,
    contact={
        "name": "TimeNest Development Team",
        "email": "dev@timenest.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    debug=settings.debug,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)


if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.timenest.com", "timenest.com", "localhost"]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins_list,
    allow_credentials=settings.security.cors_allow_credentials,
    allow_methods=settings.security.cors_methods_list,
    allow_headers=settings.security.cors_headers_list,
)

app.add_middleware(
    ErrorHandlerMiddleware,
    debug=settings.debug
)


auth_service = get_auth_service()
app.add_middleware(
    OptionalAuthenticationMiddleware,
    auth_service=auth_service,
    exclude_paths={
        "/docs", "/redoc", "/openapi.json",
        "/health", "/metrics",
        "/api/v1/auth/login", "/api/v1/auth/register",
        "/api/v1/auth/refresh", "/api/v1/auth/health"
    }
)


API_V1_PREFIX = "/api/v1"

app.include_router(
    auth_router,
    prefix=API_V1_PREFIX,
    tags=["Authentication"]
)

app.include_router(
    tasks_router,
    prefix=API_V1_PREFIX,
    tags=["Tasks"]
)



@app.get(
    "/",
    summary="Root endpoint",
    description="API root with basic information"
)
async def root() -> Dict[str, Any]:
    """
    Root endpoint with API information.
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment.value,
        "docs_url": "/docs" if not settings.is_production else "Documentation disabled in production",
        "api_prefix": API_V1_PREFIX,
        "endpoints": {
            "authentication": f"{API_V1_PREFIX}/auth",
            "tasks": f"{API_V1_PREFIX}/tasks",
            "health": "/health"
        }
    }


@app.get(
    "/health",
    summary="Health check",
    description="Application health status",
    tags=["Health"]
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancers.
    """
    from infrastructure.database.connection import db_manager
    
    db_healthy = await db_manager.health_check()
    
    healthy = db_healthy
    status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    health_data = {
        "status": "healthy" if healthy else "unhealthy",
        "timestamp": "2024-01-15T10:00:00Z", 
        "version": settings.app_version,
        "environment": settings.environment.value,
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "authentication": "healthy",  # Could add actual auth service check
        },
        "uptime_seconds": 0, 
    }
    
    if not healthy:
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
    
    return health_data


@app.get(
    "/metrics",
    summary="Application metrics",
    description="Basic application metrics for monitoring",
    tags=["Monitoring"]
)
async def get_metrics() -> Dict[str, Any]:
    """
    Application metrics endpoint.
    
    In production, this would typically be secured or use Prometheus format.
    """
    from infrastructure.database.connection import db_manager
    
    return {
        "application": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment.value,
            "uptime_seconds": 0,  # Track actual uptime
        },
        "database": {
            "connected": db_manager.is_connected,
            "pool_size": settings.database.pool_size,
            "max_overflow": settings.database.max_overflow,
        },
        "requests": {
            "total": 0,  
            "errors": 0, 
        }
    }


# Custom OpenAPI Schema

def custom_openapi():
    """
    Custom OpenAPI schema with enhanced documentation.
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description=app.description,
        routes=app.routes,
        contact=app.contact,
        license_info=app.license_info,
    )
    
    # Add custom security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token for authentication"
        }
    }
    
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://timenest.com/logo.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi



@app.exception_handler(BaseTimeNestException)
async def custom_exception_handler(request: Request, exc: BaseTimeNestException):
    """
    Global exception handler for custom exceptions.
    
    This provides a fallback in case the middleware doesn't catch the exception.
    """
    logger.error(f"Unhandled custom exception: {exc.__class__.__name__}: {exc.message}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers=exc.headers
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """
    Handle unexpected 500 errors.
    """
    logger.error(f"Internal server error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": "2024-01-15T10:00:00Z" 
            }
        }
    )



if settings.debug:
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """Debug endpoint to view configuration (development only)"""
        return {
            "environment": settings.environment.value,
            "debug": settings.debug,
            "database_host": settings.database.host,
            "log_level": settings.log_level.value,
            "cors_origins": settings.security.cors_origins_list,
        }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {settings.app_name} in {settings.environment.value} mode")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.debug,
        log_level=settings.log_level.value.lower(),
        access_log=True,
    )