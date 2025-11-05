"""
Notification configuration API endpoints.

This module provides REST API endpoints for managing notification
preferences, alert settings, and notification delivery methods.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.db.database import get_db_session
from backend.services.auth_dependencies import get_current_user, RequireAdmin
from backend.services.notification.alert_service import AlertService
from backend.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# Request/Response models
class NotificationPreferencesRequest(BaseModel):
    """Notification preferences request model."""
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    email_address: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    phone_number: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    notification_channels: List[str] = Field(
        default=["email", "in_app"],
        description="Enabled notification channels"
    )


class AlertThresholdsRequest(BaseModel):
    """Alert thresholds configuration request model."""
    critical_rating_threshold: float = Field(3.5, ge=1.0, le=5.0, description="Rating threshold for critical alerts")
    sentiment_drop_threshold: float = Field(0.2, ge=0.1, le=1.0, description="Sentiment drop percentage threshold")
    competitor_mention_alerts: bool = True
    crisis_mode_threshold: int = Field(3, ge=1, le=10, description="Number of critical reviews to trigger crisis mode")
    alert_frequency_limit: int = Field(5, ge=1, le=50, description="Maximum alerts per hour")


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences response model."""
    user_id: str
    business_id: Optional[str]
    email_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    email_address: Optional[str]
    phone_number: Optional[str]
    notification_channels: List[str]
    created_at: str
    updated_at: str


class AlertThresholdsResponse(BaseModel):
    """Alert thresholds response model."""
    business_id: str
    critical_rating_threshold: float
    sentiment_drop_threshold: float
    competitor_mention_alerts: bool
    crisis_mode_threshold: int
    alert_frequency_limit: int
    created_at: str
    updated_at: str


class NotificationHistoryResponse(BaseModel):
    """Notification history response model."""
    notification_id: str
    business_id: str
    alert_type: str
    channel: str
    recipient: str
    status: str
    sent_at: str
    delivered_at: Optional[str]
    error_message: Optional[str]


async def get_alert_service() -> AlertService:
    """Dependency to get alert service."""
    # TODO: Properly inject email, SMS, and push services
    return AlertService(
        email_service=None,
        sms_service=None,
        push_service=None,
    )


@router.post(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def set_notification_preferences(
    preferences: NotificationPreferencesRequest,
    business_id: Optional[UUID] = Query(None, description="Business-specific preferences"),
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
) -> NotificationPreferencesResponse:
    """Set notification preferences for current user.
    
    Args:
        preferences: Notification preferences
        business_id: Optional business-specific preferences
        current_user: Current authenticated user
        alert_service: Alert service
        
    Returns:
        NotificationPreferencesResponse: Created preferences
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        # TODO: Add business access validation if business_id provided
        
        prefs = await alert_service.set_notification_preferences(
            user_id=current_user.id,
            business_id=business_id,
            email_enabled=preferences.email_enabled,
            sms_enabled=preferences.sms_enabled,
            push_enabled=preferences.push_enabled,
            email_address=preferences.email_address or current_user.email,
            phone_number=preferences.phone_number,
            notification_channels=preferences.notification_channels,
        )
        
        return NotificationPreferencesResponse(
            user_id=str(prefs.user_id),
            business_id=str(prefs.business_id) if prefs.business_id else None,
            email_enabled=prefs.email_enabled,
            sms_enabled=prefs.sms_enabled,
            push_enabled=prefs.push_enabled,
            email_address=prefs.email_address,
            phone_number=prefs.phone_number,
            notification_channels=prefs.notification_channels,
            created_at=prefs.created_at.isoformat(),
            updated_at=prefs.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set notification preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set notification preferences"
        )


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    responses={
        404: {"model": dict, "description": "Preferences not found"},
    },
)
async def get_notification_preferences(
    business_id: Optional[UUID] = Query(None, description="Business-specific preferences"),
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
) -> NotificationPreferencesResponse:
    """Get notification preferences for current user.
    
    Args:
        business_id: Optional business-specific preferences
        current_user: Current authenticated user
        alert_service: Alert service
        
    Returns:
        NotificationPreferencesResponse: Current preferences
        
    Raises:
        HTTPException: If preferences not found
    """
    try:
        # TODO: Add business access validation if business_id provided
        
        prefs = await alert_service.get_notification_preferences(
            user_id=current_user.id,
            business_id=business_id,
        )
        
        if not prefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification preferences not found"
            )
        
        return NotificationPreferencesResponse(
            user_id=str(prefs.user_id),
            business_id=str(prefs.business_id) if prefs.business_id else None,
            email_enabled=prefs.email_enabled,
            sms_enabled=prefs.sms_enabled,
            push_enabled=prefs.push_enabled,
            email_address=prefs.email_address,
            phone_number=prefs.phone_number,
            notification_channels=prefs.notification_channels,
            created_at=prefs.created_at.isoformat(),
            updated_at=prefs.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get notification preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification preferences"
        )


@router.put(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    responses={
        404: {"model": dict, "description": "Preferences not found"},
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def update_notification_preferences(
    preferences: NotificationPreferencesRequest,
    business_id: Optional[UUID] = Query(None, description="Business-specific preferences"),
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
) -> NotificationPreferencesResponse:
    """Update notification preferences for current user.
    
    Args:
        preferences: Updated notification preferences
        business_id: Optional business-specific preferences
        current_user: Current authenticated user
        alert_service: Alert service
        
    Returns:
        NotificationPreferencesResponse: Updated preferences
        
    Raises:
        HTTPException: If update fails
    """
    try:
        # TODO: Add business access validation if business_id provided
        
        prefs = await alert_service.update_notification_preferences(
            user_id=current_user.id,
            business_id=business_id,
            email_enabled=preferences.email_enabled,
            sms_enabled=preferences.sms_enabled,
            push_enabled=preferences.push_enabled,
            email_address=preferences.email_address or current_user.email,
            phone_number=preferences.phone_number,
            notification_channels=preferences.notification_channels,
        )
        
        if not prefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification preferences not found"
            )
        
        return NotificationPreferencesResponse(
            user_id=str(prefs.user_id),
            business_id=str(prefs.business_id) if prefs.business_id else None,
            email_enabled=prefs.email_enabled,
            sms_enabled=prefs.sms_enabled,
            push_enabled=prefs.push_enabled,
            email_address=prefs.email_address,
            phone_number=prefs.phone_number,
            notification_channels=prefs.notification_channels,
            created_at=prefs.created_at.isoformat(),
            updated_at=prefs.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update notification preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences"
        )


@router.post(
    "/alert-thresholds/{business_id}",
    response_model=AlertThresholdsResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": dict, "description": "Business not found"},
        403: {"model": dict, "description": "Insufficient permissions"},
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def set_alert_thresholds(
    business_id: UUID,
    thresholds: AlertThresholdsRequest,
    current_user: RequireAdmin,
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertThresholdsResponse:
    """Set alert thresholds for a business (Admin+ only).
    
    Args:
        business_id: Business ID
        thresholds: Alert thresholds configuration
        current_user: Current authenticated admin user
        alert_service: Alert service
        
    Returns:
        AlertThresholdsResponse: Created thresholds
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        # TODO: Add business access validation
        
        config = await alert_service.set_alert_thresholds(
            business_id=business_id,
            critical_rating_threshold=thresholds.critical_rating_threshold,
            sentiment_drop_threshold=thresholds.sentiment_drop_threshold,
            competitor_mention_alerts=thresholds.competitor_mention_alerts,
            crisis_mode_threshold=thresholds.crisis_mode_threshold,
            alert_frequency_limit=thresholds.alert_frequency_limit,
        )
        
        return AlertThresholdsResponse(
            business_id=str(config.business_id),
            critical_rating_threshold=config.critical_rating_threshold,
            sentiment_drop_threshold=config.sentiment_drop_threshold,
            competitor_mention_alerts=config.competitor_mention_alerts,
            crisis_mode_threshold=config.crisis_mode_threshold,
            alert_frequency_limit=config.alert_frequency_limit,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set alert thresholds for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set alert thresholds"
        )


@router.get(
    "/alert-thresholds/{business_id}",
    response_model=AlertThresholdsResponse,
    responses={
        404: {"model": dict, "description": "Thresholds not found"},
    },
)
async def get_alert_thresholds(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertThresholdsResponse:
    """Get alert thresholds for a business.
    
    Args:
        business_id: Business ID
        current_user: Current authenticated user
        alert_service: Alert service
        
    Returns:
        AlertThresholdsResponse: Current thresholds
        
    Raises:
        HTTPException: If thresholds not found
    """
    try:
        # TODO: Add business access validation
        
        config = await alert_service.get_alert_thresholds(business_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert thresholds not found"
            )
        
        return AlertThresholdsResponse(
            business_id=str(config.business_id),
            critical_rating_threshold=config.critical_rating_threshold,
            sentiment_drop_threshold=config.sentiment_drop_threshold,
            competitor_mention_alerts=config.competitor_mention_alerts,
            crisis_mode_threshold=config.crisis_mode_threshold,
            alert_frequency_limit=config.alert_frequency_limit,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert thresholds for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert thresholds"
        )


@router.put(
    "/alert-thresholds/{business_id}",
    response_model=AlertThresholdsResponse,
    responses={
        404: {"model": dict, "description": "Thresholds not found"},
        403: {"model": dict, "description": "Insufficient permissions"},
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def update_alert_thresholds(
    business_id: UUID,
    thresholds: AlertThresholdsRequest,
    current_user: RequireAdmin,
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertThresholdsResponse:
    """Update alert thresholds for a business (Admin+ only).
    
    Args:
        business_id: Business ID
        thresholds: Updated alert thresholds
        current_user: Current authenticated admin user
        alert_service: Alert service
        
    Returns:
        AlertThresholdsResponse: Updated thresholds
        
    Raises:
        HTTPException: If update fails
    """
    try:
        # TODO: Add business access validation
        
        config = await alert_service.update_alert_thresholds(
            business_id=business_id,
            critical_rating_threshold=thresholds.critical_rating_threshold,
            sentiment_drop_threshold=thresholds.sentiment_drop_threshold,
            competitor_mention_alerts=thresholds.competitor_mention_alerts,
            crisis_mode_threshold=thresholds.crisis_mode_threshold,
            alert_frequency_limit=thresholds.alert_frequency_limit,
        )
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert thresholds not found"
            )
        
        return AlertThresholdsResponse(
            business_id=str(config.business_id),
            critical_rating_threshold=config.critical_rating_threshold,
            sentiment_drop_threshold=config.sentiment_drop_threshold,
            competitor_mention_alerts=config.competitor_mention_alerts,
            crisis_mode_threshold=config.crisis_mode_threshold,
            alert_frequency_limit=config.alert_frequency_limit,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alert thresholds for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update alert thresholds"
        )


@router.get(
    "/history",
    response_model=List[NotificationHistoryResponse],
    responses={
        401: {"model": dict, "description": "Authentication required"},
    },
)
async def get_notification_history(
    business_id: Optional[UUID] = Query(None, description="Filter by business ID"),
    skip: int = Query(0, ge=0, description="Number of notifications to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of notifications to return"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
) -> List[NotificationHistoryResponse]:
    """Get notification history for current user.
    
    Args:
        business_id: Optional business filter
        skip: Number of notifications to skip
        limit: Maximum number of notifications to return
        alert_type: Optional alert type filter
        current_user: Current authenticated user
        alert_service: Alert service
        
    Returns:
        List[NotificationHistoryResponse]: Notification history
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # TODO: Add business access validation if business_id provided
        
        history = await alert_service.get_notification_history(
            user_id=current_user.id,
            business_id=business_id,
            skip=skip,
            limit=limit,
            alert_type=alert_type,
        )
        
        return [
            NotificationHistoryResponse(
                notification_id=str(notif.notification_id),
                business_id=str(notif.business_id),
                alert_type=notif.alert_type,
                channel=notif.channel,
                recipient=notif.recipient,
                status=notif.status,
                sent_at=notif.sent_at.isoformat(),
                delivered_at=notif.delivered_at.isoformat() if notif.delivered_at else None,
                error_message=notif.error_message,
            )
            for notif in history
        ]
        
    except Exception as e:
        logger.error(f"Failed to get notification history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification history"
        )


@router.post(
    "/test/{business_id}",
    responses={
        404: {"model": dict, "description": "Business not found"},
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def send_test_notification(
    business_id: UUID,
    channel: str = Query(..., pattern="^(email|sms|push|in_app)$", description="Notification channel to test"),
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
):
    """Send a test notification to verify configuration.
    
    Args:
        business_id: Business ID
        channel: Notification channel to test
        current_user: Current authenticated user
        alert_service: Alert service
        
    Returns:
        dict: Test notification result
        
    Raises:
        HTTPException: If test fails
    """
    try:
        # TODO: Add business access validation
        
        result = await alert_service.send_test_notification(
            user_id=current_user.id,
            business_id=business_id,
            channel=channel,
        )
        
        return {
            "message": f"Test notification sent via {channel}",
            "channel": channel,
            "recipient": result.get("recipient"),
            "status": result.get("status"),
            "sent_at": result.get("sent_at"),
        }
        
    except Exception as e:
        logger.error(f"Failed to send test notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification"
        )


@router.get(
    "/channels",
    responses={
        401: {"model": dict, "description": "Authentication required"},
    },
)
async def get_available_channels(
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service),
):
    """Get available notification channels and their status.
    
    Args:
        current_user: Current authenticated user
        alert_service: Alert service
        
    Returns:
        dict: Available notification channels
    """
    try:
        channels = await alert_service.get_available_channels()
        
        return {
            "available_channels": channels,
            "user_preferences": {
                "email": current_user.email,
                "language": current_user.language_preference,
            },
        }
        
    except Exception as e:
        logger.error(f"Failed to get available channels: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available channels"
        )