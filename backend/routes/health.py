"""Health check and monitoring endpoints."""

import time
from typing import Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from backend.db.database import get_db_session
from backend.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Local Business Intelligence Bot",
        "version": "1.0.0",
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Detailed health check with dependency status."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Local Business Intelligence Bot",
        "version": "1.0.0",
        "checks": {},
    }

    overall_healthy = True

    # Database health check
    try:
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        db_response_time = (time.time() - start_time) * 1000

        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2),
            "message": "Database connection successful",
        }
    except Exception as e:
        overall_healthy = False
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed",
        }

    # Redis health check
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        start_time = time.time()
        await redis_client.ping()
        redis_response_time = (time.time() - start_time) * 1000
        await redis_client.close()

        health_status["checks"]["redis"] = {
            "status": "healthy",
            "response_time_ms": round(redis_response_time, 2),
            "message": "Redis connection successful",
        }
    except Exception as e:
        overall_healthy = False
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Redis connection failed",
        }

    # AI Services health check
    ai_services_healthy = True
    ai_errors = []

    # Check OpenAI API key
    if not settings.OPENAI_API_KEY:
        ai_services_healthy = False
        ai_errors.append("OpenAI API key not configured")

    # Check Anthropic API key
    if not settings.ANTHROPIC_API_KEY:
        ai_services_healthy = False
        ai_errors.append("Anthropic API key not configured")

    if ai_services_healthy:
        health_status["checks"]["ai_services"] = {
            "status": "healthy",
            "message": "AI service credentials configured",
        }
    else:
        overall_healthy = False
        health_status["checks"]["ai_services"] = {
            "status": "unhealthy",
            "errors": ai_errors,
            "message": "AI service configuration issues",
        }

    # External APIs health check
    external_apis_healthy = True
    external_errors = []

    if not settings.GOOGLE_PLACES_API_KEY:
        external_apis_healthy = False
        external_errors.append("Google Places API key not configured")

    if external_apis_healthy:
        health_status["checks"]["external_apis"] = {
            "status": "healthy",
            "message": "External API credentials configured",
        }
    else:
        overall_healthy = False
        health_status["checks"]["external_apis"] = {
            "status": "unhealthy",
            "errors": external_errors,
            "message": "External API configuration issues",
        }

    # Update overall status
    health_status["status"] = "healthy" if overall_healthy else "unhealthy"

    if not overall_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status
        )

    return health_status


@router.get("/health/readiness")
async def readiness_check(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Readiness check for Kubernetes."""
    try:
        # Check if database is ready
        await db.execute(text("SELECT 1"))

        # Check if Redis is ready
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()

        return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


@router.get("/health/liveness")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/version")
async def version_info() -> Dict[str, Any]:
    """Version information endpoint."""
    return {
        "version": "1.0.0",
        "environment": (
            settings.ENVIRONMENT if hasattr(settings, "ENVIRONMENT") else "development"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Local Business Intelligence Bot",
    }


@router.get("/metrics")
async def metrics_endpoint(
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Prometheus-style metrics endpoint."""
    try:
        # Database metrics
        db_pool_stats = await get_database_metrics(db)

        # Redis metrics
        redis_stats = await get_redis_metrics()

        # Application metrics
        app_metrics = await get_application_metrics(db)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": db_pool_stats,
            "redis": redis_stats,
            "application": app_metrics,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to collect metrics: {str(e)}",
        )


async def get_database_metrics(db: AsyncSession) -> Dict[str, Any]:
    """Collect database-related metrics."""
    try:
        # Get database size
        size_query = text(
            """
            SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                   pg_database_size(current_database()) as size_bytes
        """
        )
        size_result = await db.execute(size_query)
        size_data = size_result.fetchone()

        # Get connection count
        conn_query = text(
            """
            SELECT count(*) as active_connections
            FROM pg_stat_activity
            WHERE state = 'active'
        """
        )
        conn_result = await db.execute(conn_query)
        conn_data = conn_result.fetchone()

        # Get table statistics
        stats_query = text(
            """
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_tuples
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
            LIMIT 10
        """
        )
        stats_result = await db.execute(stats_query)
        table_stats = [dict(row._mapping) for row in stats_result.fetchall()]

        return {
            "size": size_data.size if size_data else "unknown",
            "size_bytes": size_data.size_bytes if size_data else 0,
            "active_connections": conn_data.active_connections if conn_data else 0,
            "table_statistics": table_stats,
        }
    except Exception as e:
        return {"error": str(e)}


async def get_redis_metrics() -> Dict[str, Any]:
    """Collect Redis-related metrics."""
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        info = await redis_client.info()
        await redis_client.close()

        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
        }
    except Exception as e:
        return {"error": str(e)}


async def get_application_metrics(db: AsyncSession) -> Dict[str, Any]:
    """Collect application-specific metrics."""
    try:
        # Get business count
        business_query = text("SELECT COUNT(*) as count FROM businesses")
        business_result = await db.execute(business_query)
        business_count = business_result.scalar()

        # Get review count
        review_query = text("SELECT COUNT(*) as count FROM reviews")
        review_result = await db.execute(review_query)
        review_count = review_result.scalar()

        # Get classification count
        classification_query = text("SELECT COUNT(*) as count FROM classifications")
        classification_result = await db.execute(classification_query)
        classification_count = classification_result.scalar()

        # Get user count
        user_query = text("SELECT COUNT(*) as count FROM users")
        user_result = await db.execute(user_query)
        user_count = user_result.scalar()

        # Get recent activity (last 24 hours)
        recent_reviews_query = text(
            """
            SELECT COUNT(*) as count 
            FROM reviews 
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """
        )
        recent_reviews_result = await db.execute(recent_reviews_query)
        recent_reviews_count = recent_reviews_result.scalar()

        return {
            "total_businesses": business_count or 0,
            "total_reviews": review_count or 0,
            "total_classifications": classification_count or 0,
            "total_users": user_count or 0,
            "recent_reviews_24h": recent_reviews_count or 0,
        }
    except Exception as e:
        return {"error": str(e)}
