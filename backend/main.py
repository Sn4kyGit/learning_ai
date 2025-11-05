"""
FastAPI application entry point for Local Business Intelligence Bot.

This module initializes the FastAPI application with health check endpoints
and basic configuration management.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.routes import health

# Initialize settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="Local Business Intelligence Bot API",
    description="AI-powered platform for restaurant review analysis and business intelligence",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])

# Import and include all API routes
from backend.routes import (
    auth, users, businesses, reviews, analytics, 
    chat, reports, notifications, budget, gdpr, backup
)

app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/users", tags=["user-management"])
app.include_router(businesses.router, prefix="/api/businesses", tags=["businesses"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(budget.router, tags=["budget"])
app.include_router(gdpr.router, tags=["gdpr-compliance"])
app.include_router(backup.router, tags=["backup"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
    )
