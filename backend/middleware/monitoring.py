"""Monitoring middleware for FastAPI application."""

import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from backend.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance and errors."""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with monitoring."""
        # Skip monitoring for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Log request metrics
            await self._log_request_metrics(
                request=request,
                response=response,
                response_time=response_time
            )
            
            return response
            
        except Exception as e:
            # Log error
            response_time = time.time() - start_time
            
            await monitoring_service.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                request_path=request.url.path,
                severity="error"
            )
            
            # Log failed request metrics
            await self._log_request_metrics(
                request=request,
                response=None,
                response_time=response_time,
                error=True
            )
            
            # Re-raise the exception
            raise
    
    async def _log_request_metrics(
        self,
        request: Request,
        response: Response = None,
        response_time: float = 0.0,
        error: bool = False
    ):
        """Log request metrics."""
        try:
            # Extract user information if available
            user_id = getattr(request.state, 'user_id', None)
            business_id = getattr(request.state, 'business_id', None)
            
            # Determine status code
            status_code = response.status_code if response else HTTP_500_INTERNAL_SERVER_ERROR
            
            # Log structured request data
            log_data = {
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "response_time": response_time,
                "user_id": user_id,
                "business_id": business_id,
                "user_agent": request.headers.get("user-agent", ""),
                "remote_addr": request.client.host if request.client else "",
                "error": error
            }
            
            # Log with appropriate level
            if error or status_code >= 500:
                logger.error("Request failed", extra=log_data)
            elif status_code >= 400:
                logger.warning("Client error", extra=log_data)
            else:
                logger.info("Request completed", extra=log_data)
            
            # Store metrics for monitoring
            operation_name = f"{request.method}_{request.url.path.replace('/', '_')}"
            async with monitoring_service.track_performance(operation_name):
                pass  # Metrics are tracked in the context manager
                
        except Exception as e:
            logger.error(f"Failed to log request metrics: {e}")


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track and handle application errors."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error tracking."""
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            # Extract context information
            user_id = getattr(request.state, 'user_id', None)
            business_id = getattr(request.state, 'business_id', None)
            
            # Determine error severity
            severity = "critical" if isinstance(e, (SystemError, MemoryError)) else "error"
            
            # Log error with full context
            await monitoring_service.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=self._get_stack_trace(e),
                request_path=f"{request.method} {request.url.path}",
                user_id=user_id,
                business_id=business_id,
                severity=severity
            )
            
            # Re-raise the exception to be handled by FastAPI
            raise
    
    def _get_stack_trace(self, exception: Exception) -> str:
        """Get formatted stack trace from exception."""
        import traceback
        return ''.join(traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__
        ))