"""Performance monitoring and error tracking service."""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import psutil
from sqlalchemy import text
import redis.asyncio as redis

from backend.config import get_settings
from backend.db.database import get_db_session

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    active_connections: int = 0
    error_count: int = 0
    request_count: int = 0


@dataclass
class ErrorEvent:
    """Error event data structure."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    request_path: str = ""
    user_id: Optional[str] = None
    business_id: Optional[str] = None
    severity: str = "error"  # error, warning, critical


class MonitoringService:
    """Service for performance monitoring and error tracking."""

    def __init__(self):
        self._metrics_cache: List[PerformanceMetrics] = []
        self._error_cache: List[ErrorEvent] = []
        self._redis_client: Optional[redis.Redis] = None
        self._monitoring_active = True

    async def initialize(self):
        """Initialize monitoring service."""
        try:
            self._redis_client = redis.from_url(settings.REDIS_URL)
            await self._redis_client.ping()
            logger.info("Monitoring service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize monitoring service: {e}")
            self._redis_client = None

    async def shutdown(self):
        """Shutdown monitoring service."""
        self._monitoring_active = False
        if self._redis_client:
            await self._redis_client.close()

    @asynccontextmanager
    async def track_performance(self, operation_name: str):
        """Context manager to track operation performance."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        try:
            yield
        except Exception as e:
            await self.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                request_path=operation_name,
                severity="error",
            )
            raise
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            metrics = PerformanceMetrics(
                response_time=end_time - start_time,
                memory_usage=end_memory - start_memory,
                cpu_usage=psutil.cpu_percent(),
            )

            await self._store_metrics(operation_name, metrics)

    async def log_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: str = "",
        request_path: str = "",
        user_id: Optional[str] = None,
        business_id: Optional[str] = None,
        severity: str = "error",
    ):
        """Log error event."""
        error_event = ErrorEvent(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            request_path=request_path,
            user_id=user_id,
            business_id=business_id,
            severity=severity,
        )

        # Log to application logger
        log_level = getattr(logging, severity.upper(), logging.ERROR)
        logger.log(
            log_level,
            f"Error in {request_path}: {error_type} - {error_message}",
            extra={
                "error_type": error_type,
                "user_id": user_id,
                "business_id": business_id,
                "stack_trace": stack_trace,
            },
        )

        # Store in cache for metrics
        self._error_cache.append(error_event)

        # Store in Redis for real-time monitoring
        if self._redis_client:
            try:
                error_key = (
                    f"errors:{datetime.now(timezone.utc).strftime('%Y-%m-%d:%H')}"
                )
                await self._redis_client.lpush(error_key, error_event.__dict__)
                await self._redis_client.expire(error_key, 86400)  # 24 hours
            except Exception as e:
                logger.error(f"Failed to store error in Redis: {e}")

    async def get_performance_metrics(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get performance metrics for a time range."""
        if not start_time:
            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        if not end_time:
            end_time = datetime.now(timezone.utc)

        # Filter metrics by time range
        filtered_metrics = [
            m for m in self._metrics_cache if start_time <= m.timestamp <= end_time
        ]

        if not filtered_metrics:
            return {
                "avg_response_time": 0.0,
                "max_response_time": 0.0,
                "avg_memory_usage": 0.0,
                "max_memory_usage": 0.0,
                "avg_cpu_usage": 0.0,
                "max_cpu_usage": 0.0,
                "total_requests": 0,
                "error_rate": 0.0,
            }

        # Calculate aggregated metrics
        response_times = [m.response_time for m in filtered_metrics]
        memory_usage = [m.memory_usage for m in filtered_metrics]
        cpu_usage = [m.cpu_usage for m in filtered_metrics]

        # Filter errors by time range
        filtered_errors = [
            e for e in self._error_cache if start_time <= e.timestamp <= end_time
        ]

        return {
            "avg_response_time": sum(response_times) / len(response_times),
            "max_response_time": max(response_times),
            "avg_memory_usage": sum(memory_usage) / len(memory_usage),
            "max_memory_usage": max(memory_usage),
            "avg_cpu_usage": sum(cpu_usage) / len(cpu_usage),
            "max_cpu_usage": max(cpu_usage),
            "total_requests": len(filtered_metrics),
            "total_errors": len(filtered_errors),
            "error_rate": (
                len(filtered_errors) / len(filtered_metrics)
                if filtered_metrics
                else 0.0
            ),
        }

    async def get_error_summary(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get error summary for a time range."""
        if not start_time:
            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        if not end_time:
            end_time = datetime.now(timezone.utc)

        # Filter errors by time range
        filtered_errors = [
            e for e in self._error_cache if start_time <= e.timestamp <= end_time
        ]

        if not filtered_errors:
            return {
                "total_errors": 0,
                "error_types": {},
                "severity_breakdown": {},
                "recent_errors": [],
            }

        # Group by error type
        error_types = {}
        for error in filtered_errors:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1

        # Group by severity
        severity_breakdown = {}
        for error in filtered_errors:
            severity_breakdown[error.severity] = (
                severity_breakdown.get(error.severity, 0) + 1
            )

        # Get recent errors (last 10)
        recent_errors = sorted(
            filtered_errors, key=lambda x: x.timestamp, reverse=True
        )[:10]
        recent_errors_data = [
            {
                "timestamp": error.timestamp.isoformat(),
                "error_type": error.error_type,
                "error_message": error.error_message,
                "request_path": error.request_path,
                "severity": error.severity,
            }
            for error in recent_errors
        ]

        return {
            "total_errors": len(filtered_errors),
            "error_types": error_types,
            "severity_breakdown": severity_breakdown,
            "recent_errors": recent_errors_data,
        }

    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Database health
            db_health = await self._check_database_health()

            # Redis health
            redis_health = await self._check_redis_health()

            # Recent error rate
            recent_errors = len(
                [
                    e
                    for e in self._error_cache
                    if e.timestamp > datetime.now(timezone.utc) - timedelta(minutes=5)
                ]
            )

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "load_average": (
                        psutil.getloadavg()
                        if hasattr(psutil, "getloadavg")
                        else [0, 0, 0]
                    ),
                },
                "database": db_health,
                "redis": redis_health,
                "application": {
                    "recent_errors": recent_errors,
                    "error_rate": recent_errors / 5.0,  # errors per minute
                    "uptime": time.time() - psutil.Process().create_time(),
                },
            }
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }

    async def _store_metrics(self, operation_name: str, metrics: PerformanceMetrics):
        """Store performance metrics."""
        # Add to local cache
        self._metrics_cache.append(metrics)

        # Keep only last 1000 metrics in memory
        if len(self._metrics_cache) > 1000:
            self._metrics_cache = self._metrics_cache[-1000:]

        # Store in Redis for real-time monitoring
        if self._redis_client:
            try:
                timestamp_str = datetime.now(timezone.utc).strftime('%Y-%m-%d:%H:%M')
                metrics_key = f"metrics:{operation_name}:{timestamp_str}"
                metrics_data = {
                    "timestamp": metrics.timestamp.isoformat(),
                    "response_time": metrics.response_time,
                    "memory_usage": metrics.memory_usage,
                    "cpu_usage": metrics.cpu_usage,
                }
                await self._redis_client.hset(metrics_key, mapping=metrics_data)
                await self._redis_client.expire(metrics_key, 3600)  # 1 hour
            except Exception as e:
                logger.error(f"Failed to store metrics in Redis: {e}")

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            async for db in get_db_session():
                start_time = time.time()
                await db.execute(text("SELECT 1"))
                response_time = (time.time() - start_time) * 1000

                # Get connection count
                result = await db.execute(
                    text(
                        """
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity
                    WHERE state = 'active'
                """
                    )
                )
                active_connections = result.scalar()

                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "active_connections": active_connections,
                }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health."""
        if not self._redis_client:
            return {"status": "unavailable", "error": "Redis client not initialized"}

        try:
            start_time = time.time()
            await self._redis_client.ping()
            response_time = (time.time() - start_time) * 1000

            info = await self._redis_client.info()

            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global monitoring service instance
monitoring_service = MonitoringService()
