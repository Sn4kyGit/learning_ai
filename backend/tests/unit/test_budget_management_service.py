"""
Unit tests for budget management service.

Tests the BudgetManagementService for comprehensive budget
management, warnings, and operation control.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.budget_management_service import BudgetManagementService
from backend.ai.cost_tracker import (
    DatabaseCostTracker, 
    CostLimitExceededException, 
    BudgetWarningException
)
from backend.services.notification.alert_service import AlertService
from backend.db.models import Business, Organization, MonthlyCostSummary


class TestBudgetManagementService:
    """Test suite for BudgetManagementService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_cost_tracker = AsyncMock(spec=DatabaseCostTracker)
        self.mock_alert_service = AsyncMock(spec=AlertService)
        self.mock_db = AsyncMock(spec=AsyncSession)
        
        self.service = BudgetManagementService(
            cost_tracker=self.mock_cost_tracker,
            alert_service=self.mock_alert_service,
            db_session=self.mock_db
        )

    @pytest.mark.asyncio
    async def test_init_creates_service_with_dependencies(self):
        """Test service initialization with dependencies."""
        # Act
        service = BudgetManagementService(
            self.mock_cost_tracker,
            self.mock_alert_service,
            self.mock_db
        )
        
        # Assert
        assert service._cost_tracker == self.mock_cost_tracker
        assert service._alert_service == self.mock_alert_service
        assert service._db == self.mock_db

    @pytest.mark.asyncio
    async def test_check_and_enforce_budget_allows_operation_within_budget(self):
        """Test budget enforcement allows operations within budget."""
        # Arrange
        business_id = "test-business-id"
        operation = "classify"
        
        self.mock_cost_tracker.validate_operation.return_value = True
        
        # Act
        result = await self.service.check_and_enforce_budget(business_id, operation)
        
        # Assert
        assert result is True
        self.mock_cost_tracker.validate_operation.assert_called_once_with(business_id, operation)

    @pytest.mark.asyncio
    async def test_check_and_enforce_budget_blocks_disabled_operation(self):
        """Test budget enforcement blocks disabled operations."""
        # Arrange
        business_id = "test-business-id"
        operation = "chat"
        
        self.mock_cost_tracker.validate_operation.return_value = False
        
        # Act
        result = await self.service.check_and_enforce_budget(business_id, operation)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_and_enforce_budget_handles_warning_exception(self):
        """Test budget enforcement handles warning exception."""
        # Arrange
        business_id = "test-business-id"
        operation = "classify"
        
        warning_exception = BudgetWarningException("Warning", 85.0)
        self.mock_cost_tracker.validate_operation.side_effect = warning_exception
        
        with patch.object(self.service, '_send_budget_warning') as mock_send_warning:
            # Act
            result = await self.service.check_and_enforce_budget(business_id, operation)
            
            # Assert
            assert result is True  # Operation allowed despite warning
            mock_send_warning.assert_called_once_with(business_id, 85.0)

    @pytest.mark.asyncio
    async def test_check_and_enforce_budget_handles_limit_exceeded_exception(self):
        """Test budget enforcement handles limit exceeded exception."""
        # Arrange
        business_id = "test-business-id"
        operation = "chat"
        
        limit_exception = CostLimitExceededException(
            "Limit exceeded", 
            Decimal("120.00"), 
            Decimal("100.00")
        )
        self.mock_cost_tracker.validate_operation.side_effect = limit_exception
        
        with patch.object(self.service, '_send_cost_limit_exceeded_notification') as mock_send_notification:
            # Act
            result = await self.service.check_and_enforce_budget(business_id, operation)
            
            # Assert
            assert result is False  # Operation blocked
            mock_send_notification.assert_called_once_with(
                business_id, 
                Decimal("120.00"), 
                Decimal("100.00")
            )

    @pytest.mark.asyncio
    async def test_get_comprehensive_budget_status_returns_detailed_info(self):
        """Test comprehensive budget status returns all required information."""
        # Arrange
        business_id = "test-business-id"
        
        mock_budget_status = {
            "current_cost": Decimal("75.00"),
            "cost_limit": Decimal("100.00"),
            "usage_percentage": 75.0,
            "remaining_budget": Decimal("25.00"),
            "is_warning": False,
            "is_exceeded": False,
            "disabled_operations": []
        }
        
        projected_cost = Decimal("95.00")
        mock_breakdown = {
            "total_cost": Decimal("75.00"),
            "services": {"gpt5_nano": {"total_cost": Decimal("50.00")}}
        }
        
        self.mock_cost_tracker.check_budget_status.return_value = mock_budget_status
        self.mock_cost_tracker.get_projected_monthly_cost.return_value = projected_cost
        self.mock_cost_tracker.get_cost_breakdown_by_period.return_value = mock_breakdown
        
        with patch.object(self.service, '_generate_budget_recommendations', return_value=["Test recommendation"]):
            with patch.object(self.service, '_get_days_remaining_in_month', return_value=15):
                # Act
                result = await self.service.get_comprehensive_budget_status(business_id)
                
                # Assert
                assert result["current_cost"] == Decimal("75.00")
                assert result["projected_monthly_cost"] == projected_cost
                assert result["cost_breakdown"] == mock_breakdown
                assert result["recommendations"] == ["Test recommendation"]
                assert result["days_remaining"] == 15
                assert result["is_projected_over_budget"] is False

    @pytest.mark.asyncio
    async def test_get_comprehensive_budget_status_detects_projected_over_budget(self):
        """Test comprehensive budget status detects projected over-budget."""
        # Arrange
        business_id = "test-business-id"
        
        mock_budget_status = {
            "current_cost": Decimal("75.00"),
            "cost_limit": Decimal("100.00"),
            "usage_percentage": 75.0,
            "remaining_budget": Decimal("25.00"),
            "is_warning": False,
            "is_exceeded": False,
            "disabled_operations": []
        }
        
        projected_cost = Decimal("120.00")  # Over budget
        
        self.mock_cost_tracker.check_budget_status.return_value = mock_budget_status
        self.mock_cost_tracker.get_projected_monthly_cost.return_value = projected_cost
        self.mock_cost_tracker.get_cost_breakdown_by_period.return_value = {}
        
        with patch.object(self.service, '_generate_budget_recommendations', return_value=[]):
            with patch.object(self.service, '_get_days_remaining_in_month', return_value=15):
                # Act
                result = await self.service.get_comprehensive_budget_status(business_id)
                
                # Assert
                assert result["is_projected_over_budget"] is True

    @pytest.mark.asyncio
    async def test_update_cost_limit_updates_organization_limit(self):
        """Test updating cost limit updates organization."""
        # Arrange
        business_id = "test-business-id"
        new_limit = Decimal("200.00")
        
        # Mock business with organization
        mock_org = MagicMock()
        mock_org.id = "org-id"
        
        mock_business = MagicMock()
        mock_business.organization = mock_org
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_business
        self.mock_db.execute.return_value = mock_result
        
        self.mock_cost_tracker.get_monthly_cost.return_value = Decimal("150.00")
        
        # Act
        result = await self.service.update_cost_limit(business_id, new_limit)
        
        # Assert
        assert result is True
        self.mock_db.execute.assert_called()
        self.mock_db.commit.assert_called_once()
        self.mock_cost_tracker.enable_all_operations.assert_called_once_with(business_id)

    @pytest.mark.asyncio
    async def test_update_cost_limit_handles_missing_business(self):
        """Test updating cost limit handles missing business."""
        # Arrange
        business_id = "test-business-id"
        new_limit = Decimal("200.00")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        # Act
        result = await self.service.update_cost_limit(business_id, new_limit)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_historical_cost_trends_returns_monthly_summaries(self):
        """Test getting historical cost trends."""
        # Arrange
        business_id = "test-business-id"
        months = 3
        
        # Mock monthly summaries
        mock_summary1 = MagicMock()
        mock_summary1.month = date(2024, 1, 1)
        mock_summary1.total_cost = Decimal("85.00")
        mock_summary1.classification_cost = Decimal("50.00")
        mock_summary1.chat_cost = Decimal("25.00")
        mock_summary1.report_cost = Decimal("10.00")
        mock_summary1.cost_limit = Decimal("100.00")
        mock_summary1.usage_percentage = Decimal("85.00")
        
        mock_summary2 = MagicMock()
        mock_summary2.month = date(2024, 2, 1)
        mock_summary2.total_cost = Decimal("92.00")
        mock_summary2.classification_cost = Decimal("55.00")
        mock_summary2.chat_cost = Decimal("27.00")
        mock_summary2.report_cost = Decimal("10.00")
        mock_summary2.cost_limit = Decimal("100.00")
        mock_summary2.usage_percentage = Decimal("92.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_summary1, mock_summary2]
        self.mock_db.execute.return_value = mock_result
        
        # Act
        result = await self.service.get_historical_cost_trends(business_id, months)
        
        # Assert
        assert len(result) == 2
        assert result[0]["month"] == date(2024, 1, 1)
        assert result[0]["total_cost"] == Decimal("85.00")
        assert result[1]["month"] == date(2024, 2, 1)
        assert result[1]["total_cost"] == Decimal("92.00")

    @pytest.mark.asyncio
    async def test_generate_budget_recommendations_suggests_limit_increase(self):
        """Test budget recommendations suggest limit increase when projected over budget."""
        # Arrange
        business_id = "test-business-id"
        budget_status = {
            "usage_percentage": 75.0,
            "cost_limit": Decimal("100.00"),
            "disabled_operations": []
        }
        projected_cost = Decimal("120.00")  # Over limit
        
        # Act
        result = await self.service._generate_budget_recommendations(
            business_id, budget_status, projected_cost
        )
        
        # Assert
        assert len(result) > 0
        assert "exceeds limit" in result[0]
        assert "increasing your budget" in result[0]

    @pytest.mark.asyncio
    async def test_generate_budget_recommendations_warns_at_90_percent(self):
        """Test budget recommendations warn at 90% usage."""
        # Arrange
        business_id = "test-business-id"
        budget_status = {
            "usage_percentage": 95.0,
            "cost_limit": Decimal("100.00"),
            "disabled_operations": []
        }
        projected_cost = Decimal("98.00")
        
        # Act
        result = await self.service._generate_budget_recommendations(
            business_id, budget_status, projected_cost
        )
        
        # Assert
        assert any("approaching your monthly budget limit" in rec for rec in result)

    @pytest.mark.asyncio
    async def test_generate_budget_recommendations_suggests_optimization(self):
        """Test budget recommendations suggest optimization at 70% usage."""
        # Arrange
        business_id = "test-business-id"
        budget_status = {
            "usage_percentage": 75.0,
            "cost_limit": Decimal("100.00"),
            "disabled_operations": []
        }
        projected_cost = Decimal("95.00")
        
        # Act
        result = await self.service._generate_budget_recommendations(
            business_id, budget_status, projected_cost
        )
        
        # Assert
        assert any("reviewing your AI usage patterns" in rec for rec in result)

    @pytest.mark.asyncio
    async def test_generate_budget_recommendations_mentions_disabled_operations(self):
        """Test budget recommendations mention disabled operations."""
        # Arrange
        business_id = "test-business-id"
        budget_status = {
            "usage_percentage": 50.0,
            "cost_limit": Decimal("100.00"),
            "disabled_operations": ["chat", "report"]
        }
        projected_cost = Decimal("60.00")
        
        # Act
        result = await self.service._generate_budget_recommendations(
            business_id, budget_status, projected_cost
        )
        
        # Assert
        assert any("operations are disabled" in rec for rec in result)
        assert any("chat, report" in rec for rec in result)

    def test_get_days_remaining_in_month_calculates_correctly(self):
        """Test days remaining calculation."""
        # Arrange & Act
        with patch('backend.services.budget_management_service.date') as mock_date:
            mock_date.today.return_value = date(2024, 1, 15)  # 15th of January
            
            result = self.service._get_days_remaining_in_month()
            
            # Assert
            # From Jan 15 to Feb 1 = 17 days
            assert result == 17

    def test_get_days_remaining_handles_december(self):
        """Test days remaining calculation handles December correctly."""
        # Arrange & Act
        with patch('backend.services.budget_management_service.date') as mock_date:
            mock_date.today.return_value = date(2024, 12, 20)  # 20th of December
            
            result = self.service._get_days_remaining_in_month()
            
            # Assert
            # From Dec 20 to Jan 1 = 12 days
            assert result == 12