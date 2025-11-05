"""
Report generation API endpoints.

This module provides REST API endpoints for generating and managing
weekly business reports and custom analytics reports.
"""

import logging
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.db.database import get_db_session
from backend.db.repositories.business import BusinessRepository
from backend.services.business_advisory_service import BusinessAdvisoryService
from backend.services.auth_dependencies import get_current_user, RequireAdmin
from backend.ai.factory import get_business_advisor
from backend.ai.cost_tracker import DatabaseCostTracker
from backend.db.repositories.conversation import ConversationRepository
from backend.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


# Request/Response models
class ReportConfigurationRequest(BaseModel):
    """Report configuration request model."""
    report_day: int = Field(..., ge=1, le=7, description="Day of week (1=Monday, 7=Sunday)")
    delivery_method: str = Field(..., pattern="^(web_only|web_and_email)$", description="Delivery method")
    language: str = Field("en", description="Report language")
    include_sections: List[str] = Field(
        default=["sentiment_analysis", "top_topics", "competitor_mentions", "action_items"],
        description="Report sections to include"
    )


class ReportConfigurationResponse(BaseModel):
    """Report configuration response model."""
    business_id: str
    report_day: int
    delivery_method: str
    language: str
    include_sections: List[str]
    next_report_date: str
    created_at: str
    updated_at: str


class WeeklyReportResponse(BaseModel):
    """Weekly report response model."""
    report_id: str
    business_id: str
    report_period_start: str
    report_period_end: str
    language: str
    sections: dict
    action_items: List[str]
    cost_summary: dict
    generated_at: str


class CustomReportRequest(BaseModel):
    """Custom report request model."""
    start_date: date
    end_date: date
    report_type: str = Field(..., pattern="^(sentiment|topics|trends|comprehensive)$")
    language: str = "en"
    include_recommendations: bool = True


async def get_advisory_service(db: AsyncSession = Depends(get_db_session)) -> BusinessAdvisoryService:
    """Dependency to get business advisory service."""
    advisor = await get_business_advisor()
    conversation_repo = ConversationRepository(db)
    business_repo = BusinessRepository(db)
    cost_tracker = DatabaseCostTracker(db)
    
    return BusinessAdvisoryService(
        advisor=advisor,
        conversation_repository=conversation_repo,
        business_repository=business_repo,
        cost_tracker=cost_tracker,
    )


@router.post(
    "/{business_id}/configuration",
    response_model=ReportConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": dict, "description": "Business not found"},
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def configure_weekly_reports(
    business_id: UUID,
    config: ReportConfigurationRequest,
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> ReportConfigurationResponse:
    """Configure weekly report settings for a business.
    
    Args:
        business_id: Business ID
        config: Report configuration
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        ReportConfigurationResponse: Created configuration
        
    Raises:
        HTTPException: If configuration fails
    """
    try:
        # TODO: Add business access validation
        
        configuration = await advisory_service.configure_weekly_reports(
            business_id=business_id,
            user_id=current_user.id,
            report_day=config.report_day,
            delivery_method=config.delivery_method,
            language=config.language,
            include_sections=config.include_sections,
        )
        
        return ReportConfigurationResponse(
            business_id=str(configuration.business_id),
            report_day=configuration.report_day,
            delivery_method=configuration.delivery_method,
            language=configuration.language,
            include_sections=configuration.include_sections,
            next_report_date=configuration.next_report_date.isoformat(),
            created_at=configuration.created_at.isoformat(),
            updated_at=configuration.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to configure reports for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report configuration failed"
        )


@router.get(
    "/{business_id}/configuration",
    response_model=ReportConfigurationResponse,
    responses={
        404: {"model": dict, "description": "Configuration not found"},
    },
)
async def get_report_configuration(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> ReportConfigurationResponse:
    """Get current report configuration for a business.
    
    Args:
        business_id: Business ID
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        ReportConfigurationResponse: Current configuration
        
    Raises:
        HTTPException: If configuration not found
    """
    try:
        # TODO: Add business access validation
        
        configuration = await advisory_service.get_report_configuration(business_id)
        
        if not configuration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report configuration not found"
            )
        
        return ReportConfigurationResponse(
            business_id=str(configuration.business_id),
            report_day=configuration.report_day,
            delivery_method=configuration.delivery_method,
            language=configuration.language,
            include_sections=configuration.include_sections,
            next_report_date=configuration.next_report_date.isoformat(),
            created_at=configuration.created_at.isoformat(),
            updated_at=configuration.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report configuration for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve report configuration"
        )


@router.put(
    "/{business_id}/configuration",
    response_model=ReportConfigurationResponse,
    responses={
        404: {"model": dict, "description": "Configuration not found"},
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def update_report_configuration(
    business_id: UUID,
    config: ReportConfigurationRequest,
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> ReportConfigurationResponse:
    """Update report configuration for a business.
    
    Args:
        business_id: Business ID
        config: Updated report configuration
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        ReportConfigurationResponse: Updated configuration
        
    Raises:
        HTTPException: If update fails
    """
    try:
        # TODO: Add business access validation
        
        configuration = await advisory_service.update_report_configuration(
            business_id=business_id,
            user_id=current_user.id,
            report_day=config.report_day,
            delivery_method=config.delivery_method,
            language=config.language,
            include_sections=config.include_sections,
        )
        
        if not configuration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report configuration not found"
            )
        
        return ReportConfigurationResponse(
            business_id=str(configuration.business_id),
            report_day=configuration.report_day,
            delivery_method=configuration.delivery_method,
            language=configuration.language,
            include_sections=configuration.include_sections,
            next_report_date=configuration.next_report_date.isoformat(),
            created_at=configuration.created_at.isoformat(),
            updated_at=configuration.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update report configuration for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report configuration update failed"
        )


@router.post(
    "/{business_id}/generate-weekly",
    response_model=WeeklyReportResponse,
    responses={
        404: {"model": dict, "description": "Business not found"},
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def generate_weekly_report(
    business_id: UUID,
    background_tasks: BackgroundTasks,
    force_regenerate: bool = Query(False, description="Force regenerate if report already exists"),
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> WeeklyReportResponse:
    """Generate weekly report for a business.
    
    Args:
        business_id: Business ID
        background_tasks: Background tasks for async processing
        force_regenerate: Force regenerate existing report
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        WeeklyReportResponse: Generated report
        
    Raises:
        HTTPException: If generation fails
    """
    try:
        # TODO: Add business access validation
        
        report = await advisory_service.generate_weekly_report(
            business_id=business_id,
            force_regenerate=force_regenerate,
        )
        
        # Schedule email delivery if configured
        configuration = await advisory_service.get_report_configuration(business_id)
        if configuration and configuration.delivery_method == "web_and_email":
            background_tasks.add_task(
                advisory_service.send_report_email,
                business_id,
                report.report_id,
                current_user.email
            )
        
        return WeeklyReportResponse(
            report_id=str(report.report_id),
            business_id=str(report.business_id),
            report_period_start=report.report_period_start.isoformat(),
            report_period_end=report.report_period_end.isoformat(),
            language=report.language,
            sections=report.sections,
            action_items=report.action_items,
            cost_summary=report.cost_summary,
            generated_at=report.generated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate weekly report for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Weekly report generation failed"
        )


@router.get(
    "/{business_id}/weekly",
    response_model=List[WeeklyReportResponse],
    responses={
        404: {"model": dict, "description": "Business not found"},
    },
)
async def get_weekly_reports(
    business_id: UUID,
    skip: int = Query(0, ge=0, description="Number of reports to skip"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of reports to return"),
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> List[WeeklyReportResponse]:
    """Get historical weekly reports for a business.
    
    Args:
        business_id: Business ID
        skip: Number of reports to skip
        limit: Maximum number of reports to return
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        List[WeeklyReportResponse]: List of weekly reports
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # TODO: Add business access validation
        
        reports = await advisory_service.get_weekly_reports(
            business_id=business_id,
            skip=skip,
            limit=limit,
        )
        
        return [
            WeeklyReportResponse(
                report_id=str(report.report_id),
                business_id=str(report.business_id),
                report_period_start=report.report_period_start.isoformat(),
                report_period_end=report.report_period_end.isoformat(),
                language=report.language,
                sections=report.sections,
                action_items=report.action_items,
                cost_summary=report.cost_summary,
                generated_at=report.generated_at.isoformat(),
            )
            for report in reports
        ]
        
    except Exception as e:
        logger.error(f"Failed to get weekly reports for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve weekly reports"
        )


@router.get(
    "/{business_id}/weekly/{report_id}",
    response_model=WeeklyReportResponse,
    responses={
        404: {"model": dict, "description": "Report not found"},
    },
)
async def get_weekly_report(
    business_id: UUID,
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> WeeklyReportResponse:
    """Get a specific weekly report.
    
    Args:
        business_id: Business ID
        report_id: Report ID
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        WeeklyReportResponse: Weekly report
        
    Raises:
        HTTPException: If report not found
    """
    try:
        # TODO: Add business access validation
        
        report = await advisory_service.get_weekly_report(report_id)
        
        if not report or report.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        return WeeklyReportResponse(
            report_id=str(report.report_id),
            business_id=str(report.business_id),
            report_period_start=report.report_period_start.isoformat(),
            report_period_end=report.report_period_end.isoformat(),
            language=report.language,
            sections=report.sections,
            action_items=report.action_items,
            cost_summary=report.cost_summary,
            generated_at=report.generated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get weekly report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve weekly report"
        )


@router.post(
    "/{business_id}/custom",
    responses={
        404: {"model": dict, "description": "Business not found"},
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def generate_custom_report(
    business_id: UUID,
    report_request: CustomReportRequest,
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
):
    """Generate a custom report for specific date range and type.
    
    Args:
        business_id: Business ID
        report_request: Custom report parameters
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        dict: Generated custom report
        
    Raises:
        HTTPException: If generation fails
    """
    try:
        # TODO: Add business access validation
        
        # Validate date range
        if report_request.start_date >= report_request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        report = await advisory_service.generate_custom_report(
            business_id=business_id,
            start_date=report_request.start_date,
            end_date=report_request.end_date,
            report_type=report_request.report_type,
            language=report_request.language,
            include_recommendations=report_request.include_recommendations,
        )
        
        return {
            "business_id": str(business_id),
            "report_type": report_request.report_type,
            "period_start": report_request.start_date.isoformat(),
            "period_end": report_request.end_date.isoformat(),
            "language": report_request.language,
            "report_data": report.report_data,
            "recommendations": report.recommendations if report_request.include_recommendations else [],
            "cost_info": report.cost_info,
            "generated_at": report.generated_at.isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate custom report for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Custom report generation failed"
        )


@router.post(
    "/{business_id}/email/{report_id}",
    responses={
        404: {"model": dict, "description": "Report not found"},
        400: {"model": dict, "description": "Bad Request"},
    },
)
async def send_report_email(
    business_id: UUID,
    report_id: UUID,
    background_tasks: BackgroundTasks,
    recipient_email: Optional[str] = Query(None, description="Override recipient email"),
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
):
    """Send a report via email.
    
    Args:
        business_id: Business ID
        report_id: Report ID
        background_tasks: Background tasks for async processing
        recipient_email: Optional recipient email override
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        dict: Email sending confirmation
        
    Raises:
        HTTPException: If sending fails
    """
    try:
        # TODO: Add business access validation
        
        email = recipient_email or current_user.email
        
        # Schedule email sending as background task
        background_tasks.add_task(
            advisory_service.send_report_email,
            business_id,
            report_id,
            email
        )
        
        return {
            "message": "Report email scheduled for delivery",
            "recipient": email,
            "report_id": str(report_id),
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule report email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule report email"
        )


@router.delete(
    "/{business_id}/weekly/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": dict, "description": "Report not found"},
        403: {"model": dict, "description": "Insufficient permissions"},
    },
)
async def delete_weekly_report(
    business_id: UUID,
    report_id: UUID,
    current_user: RequireAdmin,
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> None:
    """Delete a weekly report (Admin+ only).
    
    Args:
        business_id: Business ID
        report_id: Report ID
        current_user: Current authenticated admin user
        advisory_service: Business advisory service
        
    Raises:
        HTTPException: If report not found or deletion fails
    """
    try:
        # TODO: Add business access validation
        
        deleted = await advisory_service.delete_weekly_report(report_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete weekly report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report deletion failed"
        )