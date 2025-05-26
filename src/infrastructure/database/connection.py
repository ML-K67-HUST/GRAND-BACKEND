"""
Database connection management with SQLAlchemy and connection pooling.

This module provides:
- Async SQLAlchemy engine with connection pooling
- Session management with proper cleanup
- Database health checks
- Connection lifecycle management
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text, event
from sqlalchemy.exc import SQLAlchemyError

from core.config import settings
from core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database connection manager with connection pooling and health checks.
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._is_connected = False
    
    async def initialize(self) -> None:
        """Initialize database connection and session factory"""
        try:
            logger.info("Starting database initialization...")
            logger.info(f"Database Host: {settings.database.host}")
            logger.info(f"Database Port: {settings.database.port}")
            logger.info(f"Database Name: {settings.database.db}")
            logger.info(f"Database URL: {settings.database_async_url}")
            
            # Create async engine with connection pooling
            self._engine = create_async_engine(
                settings.database_async_url,
                # Connection pool settings
                poolclass=QueuePool,
                pool_size=settings.database.pool_size,
                max_overflow=settings.database.max_overflow,
                pool_timeout=settings.database.pool_timeout,
                pool_recycle=settings.database.pool_recycle,
                pool_pre_ping=True,  # Validate connections before use
                # Logging
                echo=settings.debug,
                echo_pool=settings.debug,
                # Connection arguments
                connect_args={
                    "server_settings": {
                        "application_name": settings.app_name,
                    }
                }
            )
            
            # Create session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Test connection
            logger.info("Testing database connection...")
            await self.health_check()
            self._is_connected = True
            logger.info("Database connection test passed")
            
            logger.info(
                f"Database initialized successfully with "
                f"pool_size={settings.database.pool_size}, "
                f"max_overflow={settings.database.max_overflow}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
    
    async def close(self) -> None:
        """Close database connections and cleanup resources"""
        if self._engine:
            await self._engine.dispose()
            self._is_connected = False
            logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """
        Perform database health check.
        
        Returns:
            bool: True if database is healthy, False otherwise
        """
        if not self._engine:
            return False
        
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with automatic cleanup.
        
        Usage:
            async with db_manager.get_session() as session:
                # Use session here
                pass
        """
        if not self._session_factory:
            raise DatabaseError("Database not initialized")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            await session.close()
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._is_connected
    
    @property
    def engine(self) -> Optional[AsyncEngine]:
        """Get SQLAlchemy engine"""
        return self._engine


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get database session.
    
    Usage in route:
        async def some_endpoint(db: AsyncSession = Depends(get_db_session)):
            # Use db session here
    """
    async with db_manager.get_session() as session:
        yield session


# Event handlers for connection monitoring
@event.listens_for(QueuePool, "connect")
def on_connect(dbapi_conn, connection_record):
    """Log new database connections"""
    logger.debug("New database connection established")


@event.listens_for(QueuePool, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkout from pool"""
    logger.debug("Connection checked out from pool")


@event.listens_for(QueuePool, "checkin")
def on_checkin(dbapi_conn, connection_record):
    """Log connection checkin to pool"""
    logger.debug("Connection checked in to pool")


@event.listens_for(QueuePool, "invalidate")
def on_invalidate(dbapi_conn, connection_record, exception):
    """Log connection invalidation"""
    logger.warning(f"Connection invalidated: {exception}")


# Application lifecycle management
async def startup_database():
    """Initialize database on application startup"""
    await db_manager.initialize()


async def shutdown_database():
    """Close database connections on application shutdown"""
    await db_manager.close()


# Database utilities
async def execute_raw_query(
    query: str, 
    params: Optional[tuple] = None,
    fetch_one: bool = False,
    fetch_all: bool = False
) -> Optional[any]:
    """
    Execute raw SQL query with proper connection management.
    
    Args:
        query: SQL query string
        params: Query parameters
        fetch_one: Whether to fetch one result
        fetch_all: Whether to fetch all results
        
    Returns:
        Query result or None
    """
    async with db_manager.get_session() as session:
        try:
            result = await session.execute(text(query), params or {})
            
            if fetch_one:
                return result.fetchone()
            elif fetch_all:
                return result.fetchall()
            else:
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"Raw query execution failed: {e}")
            raise DatabaseError(f"Query execution failed: {e}")


async def check_table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = :table_name
        );
    """
    
    try:
        result = await execute_raw_query(
            query, 
            {"table_name": table_name}, 
            fetch_one=True
        )
        return bool(result[0]) if result else False
    except Exception as e:
        logger.error(f"Failed to check if table {table_name} exists: {e}")
        return False 