"""
Analytics API endpoints.

This module provides REST API endpoints for business analytics,
dashboard data, and trend analysis.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.db.repositories.review import ReviewRepository
from backend.db.repositories.classification import ClassificationRepository
from backend.db.repositories.business import BusinessRepository
from backend.services.analytics_service import AnalyticsService
from backend.services.auth_dependencies import get_current_user
from backend.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def get_analytics_service(db: AsyncSession = Depends(get_db_session)) -> AnalyticsService:
    """Dependency to get analytics service."""
    review_repo = ReviewRepository(db)
    classification_repo = ClassificationRepository(db)
    business_repo = BusinessRepository(db)
    
    return AnalyticsService(
        review_repository=review_repo,
        classification_repository=classification_repo,
        business_repository=business_repo,
    )


@router.get("/dashboard/{business_id}")
async def get_dashboard_data(
    business_id: UUID,
    force_refresh: bool = Query(False, description="Force refresh cached data"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard data for a business."""
    try:
        # TODO: Add permission check for business access
        
        dashboard_data = await analytics_service.get_dashboard_data(
            business_id, force_refresh=force_refresh
        )
        
        return {
            "business_id": dashboard_data.business_id,
            "avg_rating": float(dashboard_data.avg_rating),
            "total_reviews": dashboard_data.total_reviews,
            "sentiment_distribution": dashboard_data.sentiment_distribution,
            "top_topics": dashboard_data.top_topics,
            "competitor_mentions": dashboard_data.competitor_mentions,
            "response_rate": float(dashboard_data.response_rate),
            "avg_response_time_hours": float(dashboard_data.avg_response_time_hours) if dashboard_data.avg_response_time_hours else None,
            "trend_data": dashboard_data.trend_data,
            "last_updated": dashboard_data.last_updated.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data for business {business_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")


@router.get("/trends/{business_id}")
async def get_trend_analysis(
    business_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    """Get trend analysis for a business."""
    try:
        # TODO: Add permission check for business access
        
        trend_analysis = await analytics_service.get_trend_analysis(business_id, days)
        
        return {
            "period_start": trend_analysis.period_start.isoformat(),
            "period_end": trend_analysis.period_end.isoformat(),
            "sentiment_trend": trend_analysis.sentiment_trend,
            "rating_trend": trend_analysis.rating_trend,
            "review_volume_trend": trend_analysis.review_volume_trend,
            "key_insights": trend_analysis.key_insights,
        }
        
    except Exception as e:
        logger.error(f"Failed to get trend analysis for business {business_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trend analysis")


@router.get("/score/{business_id}")
async def get_business_score(
    business_id: UUID,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    """Get business performance score."""
    try:
        # TODO: Add permission check for business access
        
        business_score = await analytics_service.get_business_score(business_id)
        
        return business_score
        
    except Exception as e:
        logger.error(f"Failed to get business score for business {business_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get business score")


@router.get("/multi-business")
async def get_multi_business_dashboard(
    business_ids: List[UUID] = Query(..., description="List of business IDs"),
    force_refresh: bool = Query(False, description="Force refresh cached data"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard data for multiple businesses."""
    try:
        # TODO: Add permission check for business access
        
        if len(business_ids) > 50:  # Limit to prevent abuse
            raise HTTPException(status_code=400, detail="Too many business IDs (max 50)")
        
        multi_dashboard = await analytics_service.get_multi_business_dashboard(
            business_ids, force_refresh=force_refresh
        )
        
        # Convert Decimal values to float for JSON serialization
        result = {}
        for business_id, dashboard_data in multi_dashboard.items():
            result[business_id] = {
                "business_id": dashboard_data.business_id,
                "avg_rating": float(dashboard_data.avg_rating),
                "total_reviews": dashboard_data.total_reviews,
                "sentiment_distribution": dashboard_data.sentiment_distribution,
                "top_topics": dashboard_data.top_topics,
                "competitor_mentions": dashboard_data.competitor_mentions,
                "response_rate": float(dashboard_data.response_rate),
                "avg_response_time_hours": float(dashboard_data.avg_response_time_hours) if dashboard_data.avg_response_time_hours else None,
                "trend_data": dashboard_data.trend_data,
                "last_updated": dashboard_data.last_updated.isoformat(),
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get multi-business dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get multi-business dashboard data")


@router.get("/consolidated")
async def get_consolidated_metrics(
    business_ids: List[UUID] = Query(..., description="List of business IDs"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    """Get consolidated metrics across multiple businesses."""
    try:
        # TODO: Add permission check for business access
        
        if len(business_ids) > 50:  # Limit to prevent abuse
            raise HTTPException(status_code=400, detail="Too many business IDs (max 50)")
        
        consolidated_metrics = await analytics_service.get_consolidated_metrics(business_ids)
        
        return consolidated_metrics
        
    except Exception as e:
        logger.error(f"Failed to get consolidated metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get consolidated metrics")


@router.post("/refresh/{business_id}")
async def refresh_business_analytics(
    business_id: UUID,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    """Manually refresh analytics for a business."""
    try:
        # TODO: Add permission check for business access
        
        await analytics_service.update_business_analytics(business_id)
        
        return {"message": "Analytics refreshed successfully", "business_id": str(business_id)}
        
    except Exception as e:
        logger.error(f"Failed to refresh analytics for business {business_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh analytics")


@router.get("/cache/stats")
async def get_cache_stats(
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    """Get analytics cache statistics."""
    try:
        # TODO: Add admin permission check
        
        cache_stats = await analytics_service.get_cache_stats()
        
        return cache_stats
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache stats")


@router.post("/cache/clear")
async def clear_cache(
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
):
    """Clear analytics cache."""
    try:
        # TODO: Add admin permission check
        
        await analytics_service.clear_cache()
        
        return {"message": "Cache cleared successfully"}
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")