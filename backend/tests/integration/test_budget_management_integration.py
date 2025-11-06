"""
Integration tests for budget management system.

Tests the complete budget management workflow including
cost tracking, warnings, and operation control.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from backend.db.models import Business, Organization, User, AIUsageLog, MonthlyCostSummary
from backend.ai.cost_tracker import DatabaseCostTracker, CostLimitExceededException, BudgetWarningException
from backend.services.budget_management_service import BudgetManagementService
from backend.services.notification.alert_service import AlertService


class TestBudgetManagementIntegration:
    """Integration tests for budget management system."""

    @pytest.fixture
    def cost_tracker(self, test_db_session: AsyncSession):
        """Create cost tracker instance."""
        return DatabaseCostTracker(test_db_session, default_cost_limit=Decimal("200.00"))

    @pytest.fixture
    def budget_service(self, cost_tracker: DatabaseCostTracker, test_db_session: AsyncSession):
        """Create budget management service."""
        alert_service = AlertService(None, None, None)  # Mock for testing
        return BudgetManagementService(cost_tracker, alert_service, test_db_session)

    @pytest.mark.asyncio
    async def test_complete_budget_tracking_workflow(
        self, 
        test_db_session: AsyncSession, 
        test_business: Business, 
        cost_tracker: DatabaseCostTracker
    ):
        """Test complete budget tracking workflow from logging to limits."""
        business_id = str(test_business.id)
        
        # Step 1: Log AI usage
        await cost_tracker.log_usage(
            business_id=business_id,
            ai_service="gpt5_nano",
            operation="classify",
            tokens_used=1000,
            cost_usd=Decimal("2.50"),
            processing_time_ms=300
        )
        
        await cost_tracker.log_usage(
            business_id=business_id,
            ai_service="claude_haiku",
            operation="chat",
            tokens_used=500,
            cost_usd=Decimal("1.25"),
            processing_time_ms=450
        )
        
        # Step 2: Check monthly cost
        monthly_cost = await cost_tracker.get_monthly_cost(business_id)
        assert monthly_cost == Decimal("3.75")
        
        # Step 3: Check budget status
        budget_status = await cost_tracker.check_budget_status(business_id)
        assert budget_status["current_cost"] == Decimal("3.75")
        assert budget_status["cost_limit"] == Decimal("200.00")  # From test organization
        assert budget_status["usage_percentage"] == 1.875  # 3.75/200 * 100
        assert budget_status["is_warning"] is False
        assert budget_status["is_exceeded"] is False
        
        # Step 4: Validate operations are allowed
        is_allowed = await cost_tracker.validate_operation(business_id, "classify")
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_budget_warning_threshold_detection(
        self, 
        test_db_session: AsyncSession, 
        test_business: Business, 
        cost_tracker: DatabaseCostTracker
    ):
        """Test budget warning detection at 80% threshold."""
        business_id = str(test_business.id)
        
        # Log usage to reach 80% of limit (200 * 0.8 = 160)
        await cost_tracker.log_usage(
            business_id=business_id,
            ai_service="gpt5_nano",
            operation="classify",
            tokens_used=5000,
            cost_usd=Decimal("160.00"),
            processing_time_ms=2000
        )
        
        # Check budget status
        budget_status = await cost_tracker.check_budget_status(business_id)
        assert budget_status["usage_percentage"] == 80.0
        assert budget_status["is_warning"] is True
        
        # Validate operation raises warning
        with pytest.raises(BudgetWarningException) as exc_info:
            await cost_tracker.validate_operation(business_id, "classify")
        
        assert exc_info.value.usage_percentage == 80.0

    @pytest.mark.asyncio
    async def test_cost_limit_exceeded_and_operation_disabling(
        self, 
        test_db_session: AsyncSession, 
        test_business: Business, 
        cost_tracker: DatabaseCostTracker
    ):
        """Test cost limit exceeded detection and operation disabling."""
        business_id = str(test_business.id)
        
        # Log usage to exceed limit (200 + 10 = 210)
        await cost_tracker.log_usage(
            business_id=business_id,
            ai_service="gpt5_nano",
            operation="classify",
            tokens_used=8000,
            cost_usd=Decimal("210.00"),
            processing_time_ms=3000
        )
        
        # Check budget status
        budget_status = await cost_tracker.check_budget_status(business_id)
        assert budget_status["is_exceeded"] is True
        assert budget_status["remaining_budget"] == Decimal("-10.00")
        
        # Validate operation raises exception and disables non-essential ops
        with pytest.raises(CostLimitExceededException) as exc_info:
            await cost_tracker.validate_operation(business_id, "chat")
        
        assert exc_info.value.current_cost == Decimal("210.00")
        assert exc_info.value.cost_limit == Decimal("200.00")
        
        # Check that non-essential operations are disabled
        budget_status_after = await cost_tracker.check_budget_status(business_id)
        assert "chat" in budget_status_after["disabled_operations"]
        assert "report" in budget_status_after["disabled_operations"]
        
        # Essential operations (classify) should still be blocked due to limit
        is_classify_allowed = await cost_tracker.validate_operation(business_id, "classify")
        assert is_classify_allowed is False

    @pytest.mark.asyncio
    async def test_cost_breakdown_by_period(
        self, 
        db_session: AsyncSession, 
        business: Business, 
        cost_tracker: DatabaseCostTracker
    ):
        """Test detailed cost breakdown by service and period."""
        business_id = str(business.id)
        
        # Log various AI usage
        await cost_tracker.log_usage(
            business_id=business_id,
            ai_service="gpt5_nano",
            operation="classify",
            tokens_used=1000,
            cost_usd=Decimal("5.00"),
            processing_time_ms=200
        )
        
        await cost_tracker.log_usage(
            business_id=business_id,
            ai_service="claude_haiku",
            operation="chat",
            tokens_used=500,
            cost_usd=Decimal("3.00"),
            processing_time_ms=400
        )
        
        await cost_tracker.log_usage(
            business_id=business_id,
            ai_service="claude_haiku",
            operation="report",
            tokens_used=800,
            cost_usd=Decimal("4.50"),
            processing_time_ms=600
        )
        
        # Get cost breakdown for current month
        current_month = date.today().replace(day=1)
        end_date = date.today()
        
        breakdown = await cost_tracker.get_cost_breakdown_by_period(
            business_id, current_month, end_date
        )
        
        # Verify breakdown structure
        assert breakdown["total_cost"] == Decimal("12.50")
        assert breakdown["total_tokens"] == 2300
        assert breakdown["total_operations"] == 3
        
        # Verify service breakdown
        assert "gpt5_nano" in breakdown["services"]
        assert "claude_haiku" in breakdown["services"]
        
        gpt_service = breakdown["services"]["gpt5_nano"]
        assert gpt_service["total_cost"] == Decimal("5.00")
        assert gpt_service["operations"]["classify"]["cost"] == Decimal("5.00")
        
        claude_service = breakdown["services"]["claude_haiku"]
        assert claude_service["total_cost"] == Decimal("7.50")  # 3.00 + 4.50

    @pytest.mark.asyncio
    async def test_projected_monthly_cost_calculation(
        self, 
        db_session: AsyncSession, 
        business: Business, 
        cost_tracker: DatabaseCostTracker
    ):
        """Test projected monthly cost calculation."""
        business_id = str(business.id)
        
        # Log some usage (simulate 10 days of usage)
        await cost_tracker.log_usage(
            business_id=business_id,
            ai_service="gpt5_nano",
            operation="classify",
            tokens_used=2000,
            cost_usd=Decimal("30.00"),  # $3/day average
            processing_time_ms=500
        )
        
        # Get projected cost
        projected_cost = await cost_tracker.get_projected_monthly_cost(business_id)
        
        # Should project based on current usage pattern
        # Exact calculation depends on current date, but should be reasonable
        assert projected_cost > Decimal("30.00")  # Should be higher than current
        assert projected_cost < Decimal("300.00")  # Should be reasonable

    @pytest.mark.asyncio
    async def test_budget_service_comprehensive_status(
        self, 
        db_session: AsyncSession, 
        business: Business, 
        budget_service: BudgetManagementService
    ):
        """Test budget service comprehensive status reporting."""
        business_id = str(business.id)
        
        # Log some AI usage
        await budget_service._cost_tracker.log_usage(
            business_id=business_id,
            ai_service="gpt5_nano",
            operation="classify",
            tokens_used=1500,
            cost_usd=Decimal("45.00"),
            processing_time_ms=300
        )
        
        # Get comprehensive status
        status = await budget_service.get_comprehensive_budget_status(business_id)
        
        # Verify comprehensive information
        assert status["current_cost"] == Decimal("45.00")
        assert status["cost_limit"] == Decimal("150.00")
        assert status["usage_percentage"] == 30.0
        assert status["remaining_budget"] == Decimal("105.00")
        assert status["is_warning"] is False
        assert status["is_exceeded"] is False
        assert "projected_monthly_cost" in status
        assert "cost_breakdown" in status
        assert "recommendations" in status
        assert "days_remaining" in status

    @pytest.mark.asyncio
    async def test_cost_limit_update_functionality(
        self, 
        db_session: AsyncSession, 
        business: Business, 
        budget_service: BudgetManagementService
    ):
        """Test updating cost limits."""
        business_id = str(business.id)
        new_limit = Decimal("200.00")
        
        # Update cost limit
        success = await budget_service.update_cost_limit(business_id, new_limit)
        assert success is True
        
        # Verify limit was updated
        budget_status = await budget_service._cost_tracker.check_budget_status(business_id)
        assert budget_status["cost_limit"] == new_limit

    @pytest.mark.asyncio
    async def test_historical_cost_trends(
        self, 
        db_session: AsyncSession, 
        business: Business, 
        budget_service: BudgetManagementService
    ):
        """Test historical cost trends retrieval."""
        business_id = str(business.id)
        
        # Create a monthly cost summary for testing
        current_month = date.today().replace(day=1)
        summary = MonthlyCostSummary(
            business_id=business_id,
            month=current_month,
            classification_cost=Decimal("50.00"),
            chat_cost=Decimal("25.00"),
            report_cost=Decimal("15.00"),
            total_cost=Decimal("90.00"),
            cost_limit=Decimal("150.00"),
            usage_percentage=Decimal("60.00")
        )
        db_session.add(summary)
        await db_session.commit()
        
        # Get historical trends
        trends = await budget_service.get_historical_cost_trends(business_id, months=1)
        
        # Verify trends data
        assert len(trends) == 1
        assert trends[0]["month"] == current_month
        assert trends[0]["total_cost"] == Decimal("90.00")
        assert trends[0]["classification_cost"] == Decimal("50.00")
        assert trends[0]["usage_percentage"] == Decimal("60.00")

    @pytest.mark.asyncio
    async def test_budget_enforcement_workflow(
        self, 
        db_session: AsyncSession, 
        business: Business, 
        budget_service: BudgetManagementService
    ):
        """Test complete budget enforcement workflow."""
        business_id = str(business.id)
        
        # Test operation allowed within budget
        is_allowed = await budget_service.check_and_enforce_budget(business_id, "classify")
        assert is_allowed is True
        
        # Log usage to approach warning threshold
        await budget_service._cost_tracker.log_usage(
            business_id=business_id,
            ai_service="gpt5_nano",
            operation="classify",
            tokens_used=6000,
            cost_usd=Decimal("125.00"),  # 83% of 150 limit
            processing_time_ms=1500
        )
        
        # Test warning is raised but operation allowed
        try:
            is_allowed = await budget_service.check_and_enforce_budget(business_id, "classify")
            assert is_allowed is True
        except BudgetWarningException:
            # Warning exception is expected and handled
            pass
        
        # Log more usage to exceed limit
        await budget_service._cost_tracker.log_usage(
            business_id=business_id,
            ai_service="claude_haiku",
            operation="chat",
            tokens_used=2000,
            cost_usd=Decimal("30.00"),  # Total now 155, over 150 limit
            processing_time_ms=800
        )
        
        # Test operation is blocked when limit exceeded
        is_allowed = await budget_service.check_and_enforce_budget(business_id, "chat")
        assert is_allowed is False