"""
Review processing API endpoints.

This module provides REST API endpoints for review processing,
classification, and review management.
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
from backend.services.review.processor import ReviewProcessingService
from backend.services.scheduler_service import SchedulerService
from backend.services.analytics_service import AnalyticsService
from backend.services.auth_dependencies import get_current_user
from backend.db.models import User
from backend.ai.factory import get_review_classifier
from backend.ai.language_detector import LanguageDetector
from backend.ai.cost_tracker import DatabaseCostTracker
from backend.services.notification.alert_service import AlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["reviews"])


async def get_review_processing_service(db: AsyncSession = Depends(get_db_session)) -> ReviewProcessingService:
    """Dependency to get review processing service."""
    # Get AI services
    classifier = await get_review_classifier()
    language_detector = LanguageDetector()
    cost_tracker = DatabaseCostTracker(db)
    
    # Get repositories
    review_repo = ReviewRepository(db)
    classification_repo = ClassificationRepository(db)
    
    # Get alert service (simplified for now)
    alert_service = AlertService(
        email_service=None,  # TODO: Implement email service
        sms_service=None,    # TODO: Implement SMS service
        push_service=None,   # TODO: Implement push service
    )
    
    return ReviewProcessingService(
        classifier=classifier,
        language_detector=language_detector,
        review_repository=review_repo,
        classification_repository=classification_repo,
        cost_tracker=cost_tracker,
        alert_service=alert_service,
    )


async def get_scheduler_service(db: AsyncSession = Depends(get_db_session)) -> SchedulerService:
    """Dependency to get scheduler service."""
    # Get processing service
    processing_service = await get_review_processing_service(db)
    
    # Get analytics service
    review_repo = ReviewRepository(db)
    classification_repo = ClassificationRepository(db)
    business_repo = BusinessRepository(db)
    analytics_service = AnalyticsService(
        review_repository=review_repo,
        classification_repository=classification_repo,
        business_repository=business_repo,
    )
    
    # TODO: Get Google Places client
    from unittest.mock import AsyncMock
    google_places_client = AsyncMock()
    
    return SchedulerService(
        review_processor=processing_service,
        analytics_service=analytics_service,
        google_places_client=google_places_client,
        business_repository=business_repo,
    )


@router.post("/process/{business_id}")
async def process_business_reviews(
    business_id: UUID,
    processing_service: ReviewProcessingService = Depends(get_review_processing_service),
    current_user: User = Depends(get_current_user),
):
    """Process all unclassified reviews for a business."""
    try:
        # TODO: Add permission check for business access
        
        result = await processing_service.process_new_reviews(business_id)
        
        return {
            "business_id": str(business_id),
            "processed_count": result.processed_count,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "critical_reviews_found": result.critical_reviews_found,
            "processing_time_ms": result.processing_time_ms,
            "errors": result.errors,
        }
        
    except Exception as e:
        logger.error(f"Failed to process reviews for business {business_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process reviews")


@router.post("/process/single/{review_id}")
async def process_single_review(
    review_id: UUID,
    processing_service: ReviewProcessingService = Depends(get_review_processing_service),
    current_user: User = Depends(get_current_user),
):
    """Process a single review."""
    try:
        # TODO: Add permission check for review access
        
        success = await processing_service.process_single_review(review_id)
        
        if success:
            return {
                "review_id": str(review_id),
                "status": "processed",
                "message": "Review processed successfully",
            }
        else:
            return {
                "review_id": str(review_id),
                "status": "failed",
                "message": "Failed to process review",
            }
        
    except Exception as e:
        logger.error(f"Failed to process review {review_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process review")


@router.get("/{business_id}")
async def get_business_reviews(
    business_id: UUID,
    skip: int = Query(0, ge=0, description="Number of reviews to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of reviews to return"),
    include_classifications: bool = Query(True, description="Include classification data"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get reviews for a business."""
    try:
        # TODO: Add permission check for business access
        
        review_repo = ReviewRepository(db)
        reviews = await review_repo.get_by_business(
            business_id, skip=skip, limit=limit, include_classifications=include_classifications
        )
        
        result = []
        for review in reviews:
            review_data = {
                "id": str(review.id),
                "business_id": str(review.business_id),
                "author_name": review.author_name,
                "rating": review.rating,
                "text": review.text,
                "language": review.language,
                "published_at": review.published_at.isoformat(),
                "source": review.source,
                "external_id": review.external_id,
                "created_at": review.created_at.isoformat(),
            }
            
            if include_classifications and hasattr(review, 'classifications') and review.classifications:
                classification = review.classifications[0]  # Assuming one classification per review
                review_data["classification"] = {
                    "sentiment": classification.sentiment,
                    "topics": classification.topics,
                    "urgency": classification.urgency,
                    "competitor_mentioned": classification.competitor_mentioned,
                    "confidence_score": float(classification.confidence_score),
                    "ai_model": classification.ai_model,
                    "processing_time_ms": classification.processing_time_ms,
                }
            
            result.append(review_data)
        
        return {
            "reviews": result,
            "total_returned": len(result),
            "skip": skip,
            "limit": limit,
        }
        
    except Exception as e:
        logger.error(f"Failed to get reviews for business {business_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get reviews")


@router.get("/unclassified/{business_id}")
async def get_unclassified_reviews(
    business_id: UUID,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of reviews to return"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get unclassified reviews for a business."""
    try:
        # TODO: Add permission check for business access
        
        review_repo = ReviewRepository(db)
        reviews = await review_repo.get_unclassified_reviews(business_id, limit=limit)
        
        result = []
        for review in reviews:
            result.append({
                "id": str(review.id),
                "business_id": str(review.business_id),
                "author_name": review.author_name,
                "rating": review.rating,
                "text": review.text,
                "language": review.language,
                "published_at": review.published_at.isoformat(),
                "source": review.source,
                "external_id": review.external_id,
                "created_at": review.created_at.isoformat(),
            })
        
        return {
            "unclassified_reviews": result,
            "count": len(result),
        }
        
    except Exception as e:
        logger.error(f"Failed to get unclassified reviews for business {business_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get unclassified reviews")


@router.post("/schedule/daily-processing")
async def trigger_daily_processing(
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger daily review processing for all businesses."""
    try:
        # TODO: Add admin permission check
        
        result = await scheduler_service.trigger_daily_review_processing()
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to trigger daily processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger daily processing")


@router.post("/schedule/analytics-refresh")
async def trigger_analytics_refresh(
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger analytics refresh."""
    try:
        # TODO: Add admin permission check
        
        result = await scheduler_service.trigger_analytics_refresh()
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to trigger analytics refresh: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger analytics refresh")


@router.get("/schedule/status")
async def get_scheduler_status(
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
    current_user: User = Depends(get_current_user),
):
    """Get scheduler service status."""
    try:
        # TODO: Add admin permission check
        
        status = await scheduler_service.get_scheduler_status()
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scheduler status")


@router.get("/statistics/{business_id}")
async def get_review_statistics(
    business_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive review statistics for a business."""
    try:
        # TODO: Add permission check for business access
        
        review_repo = ReviewRepository(db)
        classification_repo = ClassificationRepository(db)
        
        # Get review statistics
        review_stats = await review_repo.get_review_statistics(business_id)
        
        # Get classification statistics
        classification_stats = await classification_repo.get_classification_statistics(business_id)
        
        return {
            "business_id": str(business_id),
            "review_statistics": review_stats,
            "classification_statistics": classification_stats,
        }
        
    except Exception as e:
        logger.error(f"Failed to get review statistics for business {business_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get review statistics")