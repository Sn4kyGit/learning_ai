"""
Budget management API endpoints.

This module provides REST API endpoints for cost tracking,
budget management, and usage monitoring.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.services.auth_dependencies import get_current_user
from backend.services.budget_management_service import BudgetManagementService
from backend.ai.cost_tracker import DatabaseCostTracker, CostLimitExceededException, BudgetWarningException
from backend.services.notification.alert_service import AlertService
from backend.db.models import User

router = APIRouter(prefix="/api/budget", tags=["budget"])


# Pydantic models for request/response
class BudgetStatusResponse(BaseModel):
    """Budget status response model."""
    current_cost: Decimal
    cost_limit: Decimal
    usage_percentage: float
    remaining_budget: Decimal
    is_warning: bool
    is_exceeded: bool
    disabled_operations: List[str]
    projected_monthly_cost: Decimal
    days_remaining: int
    is_projected_over_budget: bool
    recommendations: List[str]


class CostBreakdownResponse(BaseModel):
    """Cost breakdown response model."""
    period: Dict[str, date]
    total_cost: Decimal
    total_tokens: int
    total_operations: int
    services: Dict[str, Dict]


class UpdateCostLimitRequest(BaseModel):
    """Request model for updating cost limit."""
    new_limit: Decimal = Field(..., gt=0, description="New monthly cost limit in USD")


class HistoricalTrendResponse(BaseModel):
    """Historical cost trend response model."""
    month: date
    total_cost: Decimal
    classification_cost: Decimal
    chat_cost: Decimal
    report_cost: Decimal
    cost_limit: Decimal
    usage_percentage: Decimal


async def get_budget_service(
    db: AsyncSession = Depends(get_db_session)
) -> BudgetManagementService:
    """Dependency to get budget management service."""
    cost_tracker = DatabaseCostTracker(db)
    alert_service = AlertService(None, None, None)  # TODO: Properly inject dependencies
    return BudgetManagementService(cost_tracker, alert_service, db)


@router.get("/status/{business_id}", response_model=BudgetStatusResponse)
async def get_budget_status(
    business_id: str,
    current_user: User = Depends(get_current_user),
    budget_service: BudgetManagementService = Depends(get_budget_service)
):
    """Get comprehensive budget status for a business.
    
    Returns current costs, limits, projections, and recommendations.
    """
    try:
        # TODO: Add business access validation
        status = await budget_service.get_comprehensive_budget_status(business_id)
        
        return BudgetStatusResponse(
            current_cost=status["current_cost"],
            cost_limit=status["cost_limit"],
            usage_percentage=status["usage_percentage"],
            remaining_budget=status["remaining_budget"],
            is_warning=status["is_warning"],
            is_exceeded=status["is_exceeded"],
            disabled_operations=status["disabled_operations"],
            projected_monthly_cost=status["projected_monthly_cost"],
            days_remaining=status["days_remaining"],
            is_projected_over_budget=status["is_projected_over_budget"],
            recommendations=status["recommendations"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get budget status: {str(e)}")


@router.get("/breakdown/{business_id}", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    business_id: str,
    start_date: date = Query(..., description="Start date for cost breakdown"),
    end_date: date = Query(..., description="End date for cost breakdown"),
    current_user: User = Depends(get_current_user),
    budget_service: BudgetManagementService = Depends(get_budget_service)
):
    """Get detailed cost breakdown by service and time period."""
    try:
        # TODO: Add business access validation
        breakdown = await budget_service._cost_tracker.get_cost_breakdown_by_period(
            business_id, start_date, end_date
        )
        
        return CostBreakdownResponse(
            period=breakdown["period"],
            total_cost=breakdown["total_cost"],
            total_tokens=breakdown["total_tokens"],
            total_operations=breakdown["total_operations"],
            services=breakdown["services"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost breakdown: {str(e)}")


@router.put("/limit/{business_id}")
async def update_cost_limit(
    business_id: str,
    request: UpdateCostLimitRequest,
    current_user: User = Depends(get_current_user),
    budget_service: BudgetManagementService = Depends(get_budget_service)
):
    """Update the monthly cost limit for a business.
    
    Only Super-Admins and Admins with appropriate permissions can update limits.
    """
    try:
        # TODO: Add proper authorization check (Super-Admin or business Admin)
        if current_user.role not in ["super_admin", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        success = await budget_service.update_cost_limit(business_id, request.new_limit)
        
        if not success:
            raise HTTPException(status_code=404, detail="Business not found or update failed")
        
        return {"message": f"Cost limit updated to ${request.new_limit}", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update cost limit: {str(e)}")


@router.get("/trends/{business_id}", response_model=List[HistoricalTrendResponse])
async def get_historical_trends(
    business_id: str,
    months: int = Query(6, ge=1, le=24, description="Number of months to retrieve"),
    current_user: User = Depends(get_current_user),
    budget_service: BudgetManagementService = Depends(get_budget_service)
):
    """Get historical cost trends for the past N months."""
    try:
        # TODO: Add business access validation
        trends = await budget_service.get_historical_cost_trends(business_id, months)
        
        return [
            HistoricalTrendResponse(
                month=trend["month"],
                total_cost=trend["total_cost"],
                classification_cost=trend["classification_cost"],
                chat_cost=trend["chat_cost"],
                report_cost=trend["report_cost"],
                cost_limit=trend["cost_limit"],
                usage_percentage=trend["usage_percentage"]
            )
            for trend in trends
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get historical trends: {str(e)}")


@router.post("/validate-operation/{business_id}")
async def validate_operation(
    business_id: str,
    operation: str = Query(..., description="Operation type (classify, chat, report)"),
    current_user: User = Depends(get_current_user),
    budget_service: BudgetManagementService = Depends(get_budget_service)
):
    """Validate if an AI operation can be performed within budget limits.
    
    This endpoint is used by AI services to check budget before operations.
    """
    try:
        # TODO: Add business access validation
        is_allowed = await budget_service.check_and_enforce_budget(business_id, operation)
        
        return {
            "operation": operation,
            "allowed": is_allowed,
            "message": "Operation allowed" if is_allowed else "Operation blocked due to budget limits"
        }
        
    except BudgetWarningException as e:
        return {
            "operation": operation,
            "allowed": True,
            "warning": True,
            "message": str(e),
            "usage_percentage": e.usage_percentage
        }
        
    except CostLimitExceededException as e:
        return {
            "operation": operation,
            "allowed": False,
            "limit_exceeded": True,
            "message": str(e),
            "current_cost": e.current_cost,
            "cost_limit": e.cost_limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate operation: {str(e)}")


@router.post("/enable-operations/{business_id}")
async def enable_all_operations(
    business_id: str,
    current_user: User = Depends(get_current_user),
    budget_service: BudgetManagementService = Depends(get_budget_service)
):
    """Re-enable all AI operations for a business.
    
    This can be used after increasing the cost limit or at the start of a new month.
    """
    try:
        # TODO: Add proper authorization check
        if current_user.role not in ["super_admin", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        await budget_service._cost_tracker.enable_all_operations(business_id)
        
        return {"message": "All AI operations enabled", "success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable operations: {str(e)}")


@router.get("/current-month-summary/{business_id}")
async def get_current_month_summary(
    business_id: str,
    current_user: User = Depends(get_current_user),
    budget_service: BudgetManagementService = Depends(get_budget_service)
):
    """Get current month's cost summary with quick stats."""
    try:
        # TODO: Add business access validation
        current_month = date.today().replace(day=1)
        end_of_month = date.today()
        
        # Get basic budget status
        budget_status = await budget_service._cost_tracker.check_budget_status(business_id)
        
        # Get current month breakdown
        breakdown = await budget_service._cost_tracker.get_cost_breakdown_by_period(
            business_id, current_month, end_of_month
        )
        
        return {
            "month": current_month,
            "current_cost": budget_status["current_cost"],
            "cost_limit": budget_status["cost_limit"],
            "usage_percentage": budget_status["usage_percentage"],
            "remaining_budget": budget_status["remaining_budget"],
            "total_operations": breakdown["total_operations"],
            "total_tokens": breakdown["total_tokens"],
            "services_breakdown": breakdown["services"],
            "is_warning": budget_status["is_warning"],
            "is_exceeded": budget_status["is_exceeded"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current month summary: {str(e)}")