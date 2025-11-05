"""
Database connection management and session handling.

This module provides database connection setup, session management,
and dependency injection for the FastAPI application.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from backend.config import get_settings

logger = logging.getLogger(__name__)

# Create declarative base for models
Base = declarative_base()

# Global variables for engine and session maker
engine = None
async_session_maker = None


def create_database_engine():
    """Create and configure the database engine."""
    global engine

    settings = get_settings()

    # Configure engine based on database type
    if "sqlite" in settings.database_url:
        # SQLite-specific configuration
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 20,
            },
        )
    else:
        # PostgreSQL configuration
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
        )

    logger.info(f"Database engine created for: {settings.database_url.split('://')[0]}")
    return engine


def create_session_maker():
    """Create async session maker."""
    global async_session_maker, engine

    if engine is None:
        engine = create_database_engine()

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )

    logger.info("Session maker created")
    return async_session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session for FastAPI endpoints.

    Yields:
        AsyncSession: Database session
    """
    if async_session_maker is None:
        create_session_maker()

    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of FastAPI.

    Yields:
        AsyncSession: Database session
    """
    if async_session_maker is None:
        create_session_maker()

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """Initialize database tables using Alembic migrations."""
    global engine

    if engine is None:
        engine = create_database_engine()

    # Import all models to ensure they are registered
    from backend.db import models  # noqa: F401

    # Check if database is properly migrated
    try:
        async with engine.begin() as conn:
            # Test connection by running a simple query
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


async def check_database_health() -> bool:
    """Check database connectivity and health.

    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        if engine is None:
            create_database_engine()

        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def close_database():
    """Close database connections."""
    global engine, async_session_maker

    if engine:
        await engine.dispose()
        engine = None
        async_session_maker = None
        logger.info("Database connections closed")
