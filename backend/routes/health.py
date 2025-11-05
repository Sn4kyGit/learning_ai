"""
Health check endpoints for monitoring and status verification.

This module provides health check endpoints to verify system status,
database connectivity, and service availability.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging
from datetime import datetime, timezone

from backend.db.database import get_db_session
from backend.db.schemas import HealthCheckResponse
from backend.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Basic health check endpoint.

    Returns:
        HealthCheckResponse: Basic health status
    """
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version="1.0.0",
        database="not_checked",
    )


@router.get("/health/detailed", response_model=HealthCheckResponse)
async def detailed_health_check(db: AsyncSession = Depends(get_db_session)):
    """Detailed health check with database connectivity verification.

    Args:
        db: Database session dependency

    Returns:
        HealthCheckResponse: Detailed health status

    Raises:
        HTTPException: If health check fails
    """
    try:
        # Test database connectivity
        result = await db.execute(text("SELECT 1"))
        db_status = "connected" if result.scalar() == 1 else "error"

        # TODO: Add Redis connectivity check
        redis_status = "not_configured"

        # TODO: Add external API connectivity checks
        # - OpenAI API
        # - Anthropic API
        # - Google Places API

        overall_status = "healthy" if db_status == "connected" else "unhealthy"

        response = HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            database=db_status,
            redis=redis_status,
        )

        if overall_status == "unhealthy":
            raise HTTPException(status_code=503, detail="Service unhealthy")

        return response

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/health/readiness")
async def readiness_check(db: AsyncSession = Depends(get_db_session)):
    """Kubernetes readiness probe endpoint.

    Args:
        db: Database session dependency

    Returns:
        dict: Readiness status

    Raises:
        HTTPException: If service is not ready
    """
    try:
        # Check database connectivity
        await db.execute(text("SELECT 1"))

        # TODO: Check if all required services are initialized
        # - AI service connections
        # - Cache connections
        # - External API availability

        return {"status": "ready", "timestamp": datetime.now(timezone.utc)}

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint.

    Returns:
        dict: Liveness status
    """
    # Simple liveness check - just verify the application is running
    return {"status": "alive", "timestamp": datetime.now(timezone.utc)}


@router.get("/version")
async def version_info():
    """Get application version information.

    Returns:
        dict: Version and build information
    """
    settings = get_settings()

    return {
        "version": "1.0.0",
        "environment": settings.environment,
        "debug": settings.debug,
        "timestamp": datetime.now(timezone.utc),
    }
