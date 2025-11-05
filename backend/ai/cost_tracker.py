"""
Cost tracking implementation for AI service usage.

This module tracks AI API usage and calculates associated costs
for budget management and monitoring.
"""

from decimal import Decimal
import logging
from datetime import datetime, date
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from backend.ai.base import CostTracker
from backend.db.models import AIUsageLog, MonthlyCostSummary, Business, Organization

logger = logging.getLogger(__name__)


class CostLimitExceededException(Exception):
    """Raised when monthly cost limits are exceeded."""
    
    def __init__(self, message: str, current_cost: Decimal, cost_limit: Decimal):
        super().__init__(message)
        self.current_cost = current_cost
        self.cost_limit = cost_limit


class BudgetWarningException(Exception):
    """Raised when budget threshold is reached."""
    
    def __init__(self, message: str, usage_percentage: float, threshold: float = 80.0):
        super().__init__(message)
        self.usage_percentage = usage_percentage
        self.threshold = threshold


class DatabaseCostTracker(CostTracker):
    """Database-backed cost tracking implementation."""

    def __init__(
        self, 
        db_session: AsyncSession, 
        default_cost_limit: Decimal = Decimal("100.00"),
        warning_threshold: float = 80.0
    ):
        """Initialize cost tracker with database session.

        Args:
            db_session: Async database session for persistence
            default_cost_limit: Default monthly cost limit
            warning_threshold: Percentage threshold for budget warnings (default 80%)
        """
        self._db = db_session
        self._default_cost_limit = default_cost_limit
        self._warning_threshold = warning_threshold
        self._disabled_operations: Dict[str, List[str]] = {}  # business_id -> [operations]

    async def log_usage(
        self,
        business_id: str,
        ai_service: str,
        operation: str,
        tokens_used: int,
        cost_usd: Decimal,
        processing_time_ms: int,
    ) -> None:
        """Log AI service usage for cost tracking.

        Args:
            business_id: Business identifier
            ai_service: AI service name (gpt5_nano, claude_haiku)
            operation: Operation type (classify, chat, report)
            tokens_used: Number of tokens consumed
            cost_usd: Cost in USD
            processing_time_ms: Processing time in milliseconds
        """
        try:
            # Create usage log entry
            usage_log = AIUsageLog(
                business_id=business_id,
                ai_service=ai_service,
                operation=operation,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                processing_time_ms=processing_time_ms
            )
            
            self._db.add(usage_log)
            await self._db.commit()
            
            # Update monthly cost summary
            await self._update_monthly_summary(business_id, ai_service, cost_usd)
            
            logger.info(
                f"AI usage logged - Business: {business_id}, "
                f"Service: {ai_service}, Operation: {operation}, "
                f"Tokens: {tokens_used}, Cost: ${cost_usd}, "
                f"Time: {processing_time_ms}ms"
            )
        except Exception as e:
            logger.error(f"Failed to log AI usage: {e}")
            await self._db.rollback()

    async def get_monthly_cost(self, business_id: str) -> Decimal:
        """Get current month's AI usage cost for a business.

        Args:
            business_id: Business identifier

        Returns:
            Total cost for current month
        """
        try:
            current_month = date.today().replace(day=1)
            
            # Query monthly cost summary
            stmt = select(MonthlyCostSummary).where(
                MonthlyCostSummary.business_id == business_id,
                MonthlyCostSummary.month == current_month
            )
            result = await self._db.execute(stmt)
            summary = result.scalar_one_or_none()
            
            if summary:
                return summary.total_cost
            else:
                # Calculate from usage logs if summary doesn't exist
                return await self._calculate_monthly_cost_from_logs(business_id, current_month)
                
        except Exception as e:
            logger.error(f"Failed to get monthly cost: {e}")
            return Decimal("0.00")

    async def check_cost_limit(self, business_id: str) -> bool:
        """Check if business is within cost limits.

        Args:
            business_id: Business identifier

        Returns:
            True if within limits, False if exceeded
        """
        try:
            current_cost = await self.get_monthly_cost(business_id)
            cost_limit = await self._get_cost_limit(business_id)

            return current_cost <= cost_limit
        except Exception as e:
            logger.error(f"Failed to check cost limit: {e}")
            return True  # Allow operations if check fails

    async def get_cost_summary(self, business_id: str) -> dict:
        """Get detailed cost summary for a business.

        Args:
            business_id: Business identifier

        Returns:
            Dictionary with cost breakdown and usage statistics
        """
        try:
            current_month = date.today().replace(day=1)
            
            # Get monthly cost summary
            stmt = select(MonthlyCostSummary).where(
                MonthlyCostSummary.business_id == business_id,
                MonthlyCostSummary.month == current_month
            )
            result = await self._db.execute(stmt)
            summary = result.scalar_one_or_none()
            
            if summary:
                return {
                    "current_month_cost": summary.total_cost,
                    "cost_limit": summary.cost_limit,
                    "usage_percentage": summary.usage_percentage,
                    "remaining_budget": summary.cost_limit - summary.total_cost,
                    "classification_cost": summary.classification_cost,
                    "chat_cost": summary.chat_cost,
                    "report_cost": summary.report_cost,
                }
            else:
                # Create summary if it doesn't exist
                cost_limit = await self._get_cost_limit(business_id)
                current_cost = await self._calculate_monthly_cost_from_logs(business_id, current_month)
                
                return {
                    "current_month_cost": current_cost,
                    "cost_limit": cost_limit,
                    "usage_percentage": float((current_cost / cost_limit) * 100) if cost_limit > 0 else 0.0,
                    "remaining_budget": cost_limit - current_cost,
                    "classification_cost": Decimal("0.00"),
                    "chat_cost": Decimal("0.00"),
                    "report_cost": Decimal("0.00"),
                }
        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}")
            return {
                "current_month_cost": Decimal("0.00"),
                "cost_limit": self._default_cost_limit,
                "usage_percentage": 0.0,
                "remaining_budget": self._default_cost_limit,
            }

    async def _update_monthly_summary(self, business_id: str, ai_service: str, cost_usd: Decimal) -> None:
        """Update monthly cost summary with new usage.

        Args:
            business_id: Business identifier
            ai_service: AI service name
            cost_usd: Cost to add
        """
        try:
            current_month = date.today().replace(day=1)
            cost_limit = await self._get_cost_limit(business_id)
            
            # Get or create monthly summary
            stmt = select(MonthlyCostSummary).where(
                MonthlyCostSummary.business_id == business_id,
                MonthlyCostSummary.month == current_month
            )
            result = await self._db.execute(stmt)
            summary = result.scalar_one_or_none()
            
            if not summary:
                summary = MonthlyCostSummary(
                    business_id=business_id,
                    month=current_month,
                    cost_limit=cost_limit,
                    classification_cost=Decimal("0.00"),
                    chat_cost=Decimal("0.00"),
                    report_cost=Decimal("0.00"),
                    total_cost=Decimal("0.00"),
                    usage_percentage=Decimal("0.00")
                )
                self._db.add(summary)
            
            # Update appropriate cost category
            if ai_service in ["gpt5_nano", "gpt-4o-mini"]:
                summary.classification_cost += cost_usd
            elif ai_service in ["claude_haiku", "claude-3-haiku"]:
                if "chat" in ai_service.lower():
                    summary.chat_cost += cost_usd
                else:
                    summary.report_cost += cost_usd
            
            # Update totals
            summary.total_cost = summary.classification_cost + summary.chat_cost + summary.report_cost
            summary.usage_percentage = float((summary.total_cost / cost_limit) * 100) if cost_limit > 0 else 0.0
            
            await self._db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update monthly summary: {e}")
            await self._db.rollback()

    async def _get_cost_limit(self, business_id: str) -> Decimal:
        """Get cost limit for a business.

        Args:
            business_id: Business identifier

        Returns:
            Monthly cost limit
        """
        try:
            # Query business and organization for cost limit
            stmt = select(Business).options(selectinload(Business.organization)).where(
                Business.id == business_id
            )
            result = await self._db.execute(stmt)
            business = result.scalar_one_or_none()
            
            if business and business.organization:
                return business.organization.cost_limit_monthly
            else:
                return self._default_cost_limit
                
        except Exception as e:
            logger.error(f"Failed to get cost limit: {e}")
            return self._default_cost_limit

    async def check_budget_status(self, business_id: str) -> Dict:
        """Check budget status and return warnings/limits info.

        Args:
            business_id: Business identifier

        Returns:
            Dictionary with budget status information
        """
        try:
            current_cost = await self.get_monthly_cost(business_id)
            cost_limit = await self._get_cost_limit(business_id)
            usage_percentage = float((current_cost / cost_limit) * 100) if cost_limit > 0 else 0.0
            
            status = {
                "current_cost": current_cost,
                "cost_limit": cost_limit,
                "usage_percentage": usage_percentage,
                "remaining_budget": cost_limit - current_cost,
                "is_warning": usage_percentage >= self._warning_threshold,
                "is_exceeded": current_cost > cost_limit,
                "disabled_operations": self._disabled_operations.get(business_id, [])
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to check budget status: {e}")
            return {
                "current_cost": Decimal("0.00"),
                "cost_limit": self._default_cost_limit,
                "usage_percentage": 0.0,
                "remaining_budget": self._default_cost_limit,
                "is_warning": False,
                "is_exceeded": False,
                "disabled_operations": []
            }

    async def validate_operation(self, business_id: str, operation: str) -> bool:
        """Validate if an AI operation can be performed within budget limits.

        Args:
            business_id: Business identifier
            operation: Operation type (classify, chat, report)

        Returns:
            True if operation is allowed, False if disabled due to cost limits

        Raises:
            CostLimitExceededException: If cost limit is exceeded
            BudgetWarningException: If budget warning threshold is reached
        """
        try:
            budget_status = await self.check_budget_status(business_id)
            
            # Check if operation is disabled
            if operation in budget_status["disabled_operations"]:
                return False
            
            # Check if cost limit is exceeded
            if budget_status["is_exceeded"]:
                # Disable non-essential operations
                await self._disable_non_essential_operations(business_id)
                
                raise CostLimitExceededException(
                    f"Monthly cost limit exceeded: ${budget_status['current_cost']} > ${budget_status['cost_limit']}",
                    budget_status["current_cost"],
                    budget_status["cost_limit"]
                )
            
            # Check if warning threshold is reached
            if budget_status["is_warning"] and budget_status["usage_percentage"] >= self._warning_threshold:
                raise BudgetWarningException(
                    f"Budget warning: {budget_status['usage_percentage']:.1f}% of monthly limit used",
                    budget_status["usage_percentage"],
                    self._warning_threshold
                )
            
            return True
            
        except (CostLimitExceededException, BudgetWarningException):
            raise
        except Exception as e:
            logger.error(f"Failed to validate operation: {e}")
            return True  # Allow operations if validation fails

    async def _disable_non_essential_operations(self, business_id: str) -> None:
        """Disable non-essential AI operations when cost limit is exceeded.

        Args:
            business_id: Business identifier
        """
        try:
            # Define non-essential operations (keep classify as essential)
            non_essential_ops = ["chat", "report"]
            
            if business_id not in self._disabled_operations:
                self._disabled_operations[business_id] = []
            
            for operation in non_essential_ops:
                if operation not in self._disabled_operations[business_id]:
                    self._disabled_operations[business_id].append(operation)
            
            logger.warning(
                f"Disabled non-essential AI operations for business {business_id}: "
                f"{self._disabled_operations[business_id]}"
            )
            
        except Exception as e:
            logger.error(f"Failed to disable non-essential operations: {e}")

    async def enable_all_operations(self, business_id: str) -> None:
        """Re-enable all AI operations for a business.

        Args:
            business_id: Business identifier
        """
        try:
            if business_id in self._disabled_operations:
                del self._disabled_operations[business_id]
            
            logger.info(f"Re-enabled all AI operations for business {business_id}")
            
        except Exception as e:
            logger.error(f"Failed to enable operations: {e}")

    async def get_cost_breakdown_by_period(
        self, 
        business_id: str, 
        start_date: date, 
        end_date: date
    ) -> Dict:
        """Get detailed cost breakdown by service and time period.

        Args:
            business_id: Business identifier
            start_date: Start date for the period
            end_date: End date for the period

        Returns:
            Dictionary with cost breakdown by service and time
        """
        try:
            # Query usage logs for the period
            stmt = select(
                AIUsageLog.ai_service,
                AIUsageLog.operation,
                func.sum(AIUsageLog.cost_usd).label("total_cost"),
                func.sum(AIUsageLog.tokens_used).label("total_tokens"),
                func.count(AIUsageLog.id).label("operation_count"),
                func.avg(AIUsageLog.processing_time_ms).label("avg_processing_time")
            ).where(
                and_(
                    AIUsageLog.business_id == business_id,
                    func.date(AIUsageLog.created_at) >= start_date,
                    func.date(AIUsageLog.created_at) <= end_date
                )
            ).group_by(
                AIUsageLog.ai_service,
                AIUsageLog.operation
            )
            
            result = await self._db.execute(stmt)
            breakdown_data = result.fetchall()
            
            # Organize data by service and operation
            breakdown = {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "total_cost": Decimal("0.00"),
                "total_tokens": 0,
                "total_operations": 0,
                "services": {}
            }
            
            for row in breakdown_data:
                service = row.ai_service
                operation = row.operation
                cost = Decimal(str(row.total_cost)) if row.total_cost else Decimal("0.00")
                tokens = row.total_tokens or 0
                count = row.operation_count or 0
                avg_time = float(row.avg_processing_time) if row.avg_processing_time else 0.0
                
                if service not in breakdown["services"]:
                    breakdown["services"][service] = {
                        "total_cost": Decimal("0.00"),
                        "total_tokens": 0,
                        "total_operations": 0,
                        "operations": {}
                    }
                
                breakdown["services"][service]["operations"][operation] = {
                    "cost": cost,
                    "tokens": tokens,
                    "count": count,
                    "avg_processing_time_ms": avg_time
                }
                
                # Update service totals
                breakdown["services"][service]["total_cost"] += cost
                breakdown["services"][service]["total_tokens"] += tokens
                breakdown["services"][service]["total_operations"] += count
                
                # Update overall totals
                breakdown["total_cost"] += cost
                breakdown["total_tokens"] += tokens
                breakdown["total_operations"] += count
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Failed to get cost breakdown: {e}")
            return {
                "period": {"start_date": start_date, "end_date": end_date},
                "total_cost": Decimal("0.00"),
                "total_tokens": 0,
                "total_operations": 0,
                "services": {}
            }

    async def get_projected_monthly_cost(self, business_id: str) -> Decimal:
        """Calculate projected monthly cost based on current usage trends.

        Args:
            business_id: Business identifier

        Returns:
            Projected cost for the full month
        """
        try:
            current_month = date.today().replace(day=1)
            current_date = date.today()
            days_elapsed = current_date.day
            days_in_month = 31  # Simplified for projection
            
            current_cost = await self.get_monthly_cost(business_id)
            
            if days_elapsed == 0:
                return Decimal("0.00")
            
            # Calculate daily average and project for full month
            daily_average = current_cost / days_elapsed
            projected_cost = daily_average * days_in_month
            
            return projected_cost
            
        except Exception as e:
            logger.error(f"Failed to calculate projected monthly cost: {e}")
            return Decimal("0.00")

    async def _calculate_monthly_cost_from_logs(self, business_id: str, month: date) -> Decimal:
        """Calculate monthly cost from usage logs.

        Args:
            business_id: Business identifier
            month: Month to calculate for

        Returns:
            Total cost for the month
        """
        try:
            # Calculate start and end of month
            if month.month == 12:
                next_month = month.replace(year=month.year + 1, month=1)
            else:
                next_month = month.replace(month=month.month + 1)
            
            # Query usage logs for the month
            stmt = select(func.sum(AIUsageLog.cost_usd)).where(
                AIUsageLog.business_id == business_id,
                AIUsageLog.created_at >= month,
                AIUsageLog.created_at < next_month
            )
            result = await self._db.execute(stmt)
            total_cost = result.scalar()
            
            return Decimal(str(total_cost)) if total_cost else Decimal("0.00")
            
        except Exception as e:
            logger.error(f"Failed to calculate monthly cost from logs: {e}")
            return Decimal("0.00")
