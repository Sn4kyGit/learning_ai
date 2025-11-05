"""
Budget management service for AI cost tracking and control.

This service provides comprehensive budget management functionality
including cost monitoring, warnings, and operation control.
"""

import logging
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.cost_tracker import DatabaseCostTracker, CostLimitExceededException, BudgetWarningException
from backend.db.models import Business, Organization, MonthlyCostSummary
from backend.services.notification.alert_service import AlertService

logger = logging.getLogger(__name__)


class BudgetManagementService:
    """Service for managing AI usage budgets and cost controls."""

    def __init__(
        self,
        cost_tracker: DatabaseCostTracker,
        alert_service: AlertService,
        db_session: AsyncSession
    ):
        """Initialize budget management service.

        Args:
            cost_tracker: Cost tracking implementation
            alert_service: Alert service for notifications
            db_session: Database session
        """
        self._cost_tracker = cost_tracker
        self._alert_service = alert_service
        self._db = db_session

    async def check_and_enforce_budget(self, business_id: str, operation: str) -> bool:
        """Check budget status and enforce limits for an operation.

        Args:
            business_id: Business identifier
            operation: AI operation type

        Returns:
            True if operation is allowed, False if blocked

        Raises:
            CostLimitExceededException: If cost limit is exceeded
            BudgetWarningException: If budget warning threshold is reached
        """
        try:
            # Validate operation against budget limits
            is_allowed = await self._cost_tracker.validate_operation(business_id, operation)
            
            if not is_allowed:
                logger.warning(f"Operation {operation} blocked for business {business_id} due to budget limits")
                return False
            
            return True
            
        except BudgetWarningException as e:
            # Send warning notification but allow operation
            await self._send_budget_warning(business_id, e.usage_percentage)
            return True
            
        except CostLimitExceededException as e:
            # Send limit exceeded notification and block operation
            await self._send_cost_limit_exceeded_notification(business_id, e.current_cost, e.cost_limit)
            return False

    async def get_comprehensive_budget_status(self, business_id: str) -> Dict:
        """Get comprehensive budget status including projections and recommendations.

        Args:
            business_id: Business identifier

        Returns:
            Dictionary with detailed budget information
        """
        try:
            # Get basic budget status
            budget_status = await self._cost_tracker.check_budget_status(business_id)
            
            # Get projected monthly cost
            projected_cost = await self._cost_tracker.get_projected_monthly_cost(business_id)
            
            # Get current month breakdown
            current_month = date.today().replace(day=1)
            end_of_month = date.today()
            cost_breakdown = await self._cost_tracker.get_cost_breakdown_by_period(
                business_id, current_month, end_of_month
            )
            
            # Calculate recommendations
            recommendations = await self._generate_budget_recommendations(business_id, budget_status, projected_cost)
            
            return {
                **budget_status,
                "projected_monthly_cost": projected_cost,
                "cost_breakdown": cost_breakdown,
                "recommendations": recommendations,
                "days_remaining": self._get_days_remaining_in_month(),
                "is_projected_over_budget": projected_cost > budget_status["cost_limit"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive budget status: {e}")
            return {
                "current_cost": Decimal("0.00"),
                "cost_limit": Decimal("100.00"),
                "usage_percentage": 0.0,
                "remaining_budget": Decimal("100.00"),
                "is_warning": False,
                "is_exceeded": False,
                "disabled_operations": [],
                "projected_monthly_cost": Decimal("0.00"),
                "recommendations": [],
                "days_remaining": 0,
                "is_projected_over_budget": False
            }

    async def update_cost_limit(self, business_id: str, new_limit: Decimal) -> bool:
        """Update the cost limit for a business.

        Args:
            business_id: Business identifier
            new_limit: New monthly cost limit

        Returns:
            True if update was successful
        """
        try:
            # Update organization cost limit (assuming business belongs to organization)
            from sqlalchemy import select, update
            from sqlalchemy.orm import selectinload
            
            # Get business with organization
            stmt = select(Business).options(selectinload(Business.organization)).where(
                Business.id == business_id
            )
            result = await self._db.execute(stmt)
            business = result.scalar_one_or_none()
            
            if not business or not business.organization:
                logger.error(f"Business {business_id} or organization not found")
                return False
            
            # Update organization cost limit
            update_stmt = update(Organization).where(
                Organization.id == business.organization.id
            ).values(cost_limit_monthly=new_limit)
            
            await self._db.execute(update_stmt)
            await self._db.commit()
            
            # Re-enable operations if limit was increased
            current_cost = await self._cost_tracker.get_monthly_cost(business_id)
            if current_cost <= new_limit:
                await self._cost_tracker.enable_all_operations(business_id)
            
            logger.info(f"Updated cost limit for business {business_id} to ${new_limit}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update cost limit: {e}")
            await self._db.rollback()
            return False

    async def get_historical_cost_trends(self, business_id: str, months: int = 6) -> List[Dict]:
        """Get historical cost trends for the past N months.

        Args:
            business_id: Business identifier
            months: Number of months to retrieve

        Returns:
            List of monthly cost summaries
        """
        try:
            from sqlalchemy import select, desc
            
            # Calculate date range
            current_month = date.today().replace(day=1)
            start_month = current_month - timedelta(days=months * 31)
            start_month = start_month.replace(day=1)
            
            # Query monthly cost summaries
            stmt = select(MonthlyCostSummary).where(
                MonthlyCostSummary.business_id == business_id,
                MonthlyCostSummary.month >= start_month
            ).order_by(desc(MonthlyCostSummary.month))
            
            result = await self._db.execute(stmt)
            summaries = result.scalars().all()
            
            trends = []
            for summary in summaries:
                trends.append({
                    "month": summary.month,
                    "total_cost": summary.total_cost,
                    "classification_cost": summary.classification_cost,
                    "chat_cost": summary.chat_cost,
                    "report_cost": summary.report_cost,
                    "cost_limit": summary.cost_limit,
                    "usage_percentage": summary.usage_percentage
                })
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get historical cost trends: {e}")
            return []

    async def _send_budget_warning(self, business_id: str, usage_percentage: float) -> None:
        """Send budget warning notification.

        Args:
            business_id: Business identifier
            usage_percentage: Current usage percentage
        """
        try:
            # This would integrate with the alert service to send notifications
            # For now, just log the warning
            logger.warning(
                f"Budget warning for business {business_id}: "
                f"{usage_percentage:.1f}% of monthly limit used"
            )
            
            # TODO: Implement actual notification sending via alert service
            # await self._alert_service.send_budget_warning(business_id, usage_percentage)
            
        except Exception as e:
            logger.error(f"Failed to send budget warning: {e}")

    async def _send_cost_limit_exceeded_notification(
        self, 
        business_id: str, 
        current_cost: Decimal, 
        cost_limit: Decimal
    ) -> None:
        """Send cost limit exceeded notification.

        Args:
            business_id: Business identifier
            current_cost: Current monthly cost
            cost_limit: Monthly cost limit
        """
        try:
            logger.error(
                f"Cost limit exceeded for business {business_id}: "
                f"${current_cost} > ${cost_limit}"
            )
            
            # TODO: Implement actual notification sending via alert service
            # await self._alert_service.send_cost_limit_exceeded(business_id, current_cost, cost_limit)
            
        except Exception as e:
            logger.error(f"Failed to send cost limit exceeded notification: {e}")

    async def _generate_budget_recommendations(
        self, 
        business_id: str, 
        budget_status: Dict, 
        projected_cost: Decimal
    ) -> List[str]:
        """Generate budget management recommendations.

        Args:
            business_id: Business identifier
            budget_status: Current budget status
            projected_cost: Projected monthly cost

        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        try:
            usage_percentage = budget_status["usage_percentage"]
            cost_limit = budget_status["cost_limit"]
            
            if projected_cost > cost_limit:
                recommendations.append(
                    f"Projected monthly cost (${projected_cost}) exceeds limit (${cost_limit}). "
                    "Consider increasing your budget or reducing AI usage."
                )
            
            if usage_percentage >= 90:
                recommendations.append(
                    "You're approaching your monthly budget limit. "
                    "Monitor usage closely to avoid service interruptions."
                )
            elif usage_percentage >= 70:
                recommendations.append(
                    "You've used over 70% of your monthly budget. "
                    "Consider reviewing your AI usage patterns."
                )
            
            if budget_status["disabled_operations"]:
                recommendations.append(
                    f"Some AI operations are disabled due to budget limits: "
                    f"{', '.join(budget_status['disabled_operations'])}. "
                    "Increase your budget to re-enable these features."
                )
            
            # Add usage optimization recommendations
            if usage_percentage > 50:
                recommendations.append(
                    "Consider optimizing AI usage by batching review classifications "
                    "and limiting chat interactions to essential business questions."
                )
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
        
        return recommendations

    def _get_days_remaining_in_month(self) -> int:
        """Get number of days remaining in current month."""
        today = date.today()
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        
        return (next_month - today).days