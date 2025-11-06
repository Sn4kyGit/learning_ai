"""
Unit tests for cost tracking system.

Tests the DatabaseCostTracker for AI usage logging,
cost calculations, and budget management.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.cost_tracker import (
    DatabaseCostTracker, 
    CostLimitExceededException, 
    BudgetWarningException
)
from backend.db.models import AIUsageLog, MonthlyCostSummary, Business, Organization


class TestDatabaseCostTracker:
    """Test suite for DatabaseCostTracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = AsyncMock(spec=AsyncSession)
        # Configure the AsyncMock methods to return proper values
        self.mock_db.commit = AsyncMock()
        self.mock_db.rollback = AsyncMock()
        self.mock_db.add = Mock()  # add is not async
        self.mock_db.execute = AsyncMock()
        
        self.default_limit = Decimal("100.00")
        self.tracker = DatabaseCostTracker(
            db_session=self.mock_db,
            default_cost_limit=self.default_limit
        )
        
        # Mock the private methods to avoid warnings
        self.tracker._get_cost_limit = AsyncMock(return_value=self.default_limit)
        self.tracker._update_monthly_summary = AsyncMock()

    @pytest.mark.asyncio
    async def test_init_creates_tracker_with_session_and_limit(self):
        """Test tracker initialization with database session and limit."""
        # Act
        tracker = DatabaseCostTracker(self.mock_db, Decimal("200.00"))
        
        # Assert
        assert tracker._db == self.mock_db
        assert tracker._default_cost_limit == Decimal("200.00")

    @pytest.mark.asyncio
    async def test_log_usage_creates_usage_log_entry(self):
        """Test that usage logging creates database entry."""
        # Arrange
        business_id = "test-business-id"
        ai_service = "gpt5_nano"
        operation = "classify"
        tokens_used = 150
        cost_usd = Decimal("0.003")
        processing_time_ms = 250
        
        # Act
        await self.tracker.log_usage(
            business_id=business_id,
            ai_service=ai_service,
            operation=operation,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            processing_time_ms=processing_time_ms
        )
        
        # Assert
        self.mock_db.add.assert_called_once()
        added_log = self.mock_db.add.call_args[0][0]
        assert isinstance(added_log, AIUsageLog)
        assert added_log.business_id == business_id
        assert added_log.ai_service == ai_service
        assert added_log.operation == operation
        assert added_log.tokens_used == tokens_used
        assert added_log.cost_usd == cost_usd
        assert added_log.processing_time_ms == processing_time_ms
        
        self.mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_usage_handles_database_error(self):
        """Test error handling during usage logging."""
        # Arrange
        self.mock_db.commit.side_effect = Exception("Database error")
        
        # Act
        await self.tracker.log_usage(
            business_id="test-id",
            ai_service="gpt5_nano",
            operation="classify",
            tokens_used=100,
            cost_usd=Decimal("0.001"),
            processing_time_ms=200
        )
        
        # Assert
        self.mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_monthly_cost_returns_summary_total(self):
        """Test getting monthly cost from existing summary."""
        # Arrange
        business_id = "test-business-id"
        expected_cost = Decimal("25.50")
        
        mock_summary = MagicMock()
        mock_summary.total_cost = expected_cost
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_summary
        self.mock_db.execute.return_value = mock_result
        
        # Act
        result = await self.tracker.get_monthly_cost(business_id)
        
        # Assert
        assert result == expected_cost
        self.mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_monthly_cost_calculates_from_logs_when_no_summary(self):
        """Test calculating monthly cost from logs when summary doesn't exist."""
        # Arrange
        business_id = "test-business-id"
        
        # Mock no summary found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        # Mock the calculation method
        expected_cost = Decimal("15.75")
        with patch.object(self.tracker, '_calculate_monthly_cost_from_logs', return_value=expected_cost):
            # Act
            result = await self.tracker.get_monthly_cost(business_id)
            
            # Assert
            assert result == expected_cost

    @pytest.mark.asyncio
    async def test_get_monthly_cost_handles_error(self):
        """Test error handling in monthly cost calculation."""
        # Arrange
        self.mock_db.execute.side_effect = Exception("Database error")
        
        # Act
        result = await self.tracker.get_monthly_cost("test-id")
        
        # Assert
        assert result == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_check_cost_limit_returns_true_when_within_limit(self):
        """Test cost limit check when within limits."""
        # Arrange
        business_id = "test-business-id"
        current_cost = Decimal("50.00")
        cost_limit = Decimal("100.00")
        
        with patch.object(self.tracker, 'get_monthly_cost', return_value=current_cost):
            with patch.object(self.tracker, '_get_cost_limit', return_value=cost_limit):
                # Act
                result = await self.tracker.check_cost_limit(business_id)
                
                # Assert
                assert result is True

    @pytest.mark.asyncio
    async def test_check_cost_limit_returns_false_when_exceeded(self):
        """Test cost limit check when limit is exceeded."""
        # Arrange
        business_id = "test-business-id"
        current_cost = Decimal("150.00")
        cost_limit = Decimal("100.00")
        
        with patch.object(self.tracker, 'get_monthly_cost', return_value=current_cost):
            with patch.object(self.tracker, '_get_cost_limit', return_value=cost_limit):
                # Act
                result = await self.tracker.check_cost_limit(business_id)
                
                # Assert
                assert result is False

    @pytest.mark.asyncio
    async def test_check_cost_limit_handles_error_gracefully(self):
        """Test that cost limit check allows operations when error occurs."""
        # Arrange
        with patch.object(self.tracker, 'get_monthly_cost', side_effect=Exception("Error")):
            # Act
            result = await self.tracker.check_cost_limit("test-id")
            
            # Assert
            assert result is True  # Allow operations on error

    @pytest.mark.asyncio
    async def test_get_cost_summary_returns_detailed_breakdown(self):
        """Test getting detailed cost summary."""
        # Arrange
        business_id = "test-business-id"
        
        mock_summary = MagicMock()
        mock_summary.total_cost = Decimal("45.75")
        mock_summary.cost_limit = Decimal("100.00")
        mock_summary.usage_percentage = Decimal("45.75")
        mock_summary.classification_cost = Decimal("25.50")
        mock_summary.chat_cost = Decimal("15.25")
        mock_summary.report_cost = Decimal("5.00")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_summary
        self.mock_db.execute.return_value = mock_result
        
        # Act
        result = await self.tracker.get_cost_summary(business_id)
        
        # Assert
        assert result["current_month_cost"] == Decimal("45.75")
        assert result["cost_limit"] == Decimal("100.00")
        assert result["usage_percentage"] == Decimal("45.75")
        assert result["remaining_budget"] == Decimal("54.25")
        assert result["classification_cost"] == Decimal("25.50")
        assert result["chat_cost"] == Decimal("15.25")
        assert result["report_cost"] == Decimal("5.00")

    @pytest.mark.asyncio
    async def test_get_cost_summary_creates_summary_when_missing(self):
        """Test cost summary creation when none exists."""
        # Arrange
        business_id = "test-business-id"
        
        # Mock no summary found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        cost_limit = Decimal("100.00")
        current_cost = Decimal("30.00")
        
        with patch.object(self.tracker, '_get_cost_limit', return_value=cost_limit):
            with patch.object(self.tracker, '_calculate_monthly_cost_from_logs', return_value=current_cost):
                # Act
                result = await self.tracker.get_cost_summary(business_id)
                
                # Assert
                assert result["current_month_cost"] == current_cost
                assert result["cost_limit"] == cost_limit
                assert result["usage_percentage"] == 30.0
                assert result["remaining_budget"] == Decimal("70.00")

    @pytest.mark.asyncio
    async def test_update_monthly_summary_creates_new_summary(self):
        """Test creating new monthly summary."""
        # Arrange
        business_id = "test-business-id"
        ai_service = "gpt5_nano"
        cost_usd = Decimal("5.00")
        cost_limit = Decimal("100.00")
        
        # Mock no existing summary - make sure execute returns an awaitable
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        # Mock _get_cost_limit to return the cost limit
        async def mock_get_cost_limit(business_id):
            return cost_limit
        
        # Remove the mock for this test to test the actual method
        delattr(self.tracker, '_update_monthly_summary')
        
        with patch.object(self.tracker, '_get_cost_limit', side_effect=mock_get_cost_limit):
            # Act
            await self.tracker._update_monthly_summary(business_id, ai_service, cost_usd)
            
            # Assert
            self.mock_db.execute.assert_called_once()
            self.mock_db.add.assert_called_once()
            self.mock_db.commit.assert_called_once()
            
            added_summary = self.mock_db.add.call_args[0][0]
            assert isinstance(added_summary, MonthlyCostSummary)
            assert added_summary.business_id == business_id

    @pytest.mark.asyncio
    async def test_update_monthly_summary_updates_classification_cost(self):
        """Test updating classification cost in summary."""
        # Remove the mock for this test to test the actual method
        delattr(self.tracker, '_update_monthly_summary')
        
        # Arrange
        business_id = "test-business-id"
        ai_service = "gpt5_nano"
        cost_usd = Decimal("3.00")
        cost_limit = Decimal("100.00")
        
        mock_summary = MagicMock()
        mock_summary.classification_cost = Decimal("10.00")
        mock_summary.chat_cost = Decimal("5.00")
        mock_summary.report_cost = Decimal("2.00")
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_summary
        self.mock_db.execute.return_value = mock_result
        
        # Mock _get_cost_limit to return the cost limit
        async def mock_get_cost_limit(business_id):
            return cost_limit
        
        with patch.object(self.tracker, '_get_cost_limit', side_effect=mock_get_cost_limit):
            # Act
            await self.tracker._update_monthly_summary(business_id, ai_service, cost_usd)
            
            # Assert
            assert mock_summary.classification_cost == Decimal("13.00")
            assert mock_summary.total_cost == Decimal("20.00")  # 13 + 5 + 2
            self.mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cost_limit_returns_organization_limit(self):
        """Test getting cost limit from organization."""
        # Remove the mock for this test to test the actual method
        delattr(self.tracker, '_get_cost_limit')
        
        # Arrange
        business_id = "test-business-id"
        org_limit = Decimal("250.00")
        
        mock_org = MagicMock()
        mock_org.cost_limit_monthly = org_limit
        
        mock_business = MagicMock()
        mock_business.organization = mock_org
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_business
        self.mock_db.execute.return_value = mock_result
        
        # Act
        result = await self.tracker._get_cost_limit(business_id)
        
        # Assert
        assert result == org_limit

    @pytest.mark.asyncio
    async def test_get_cost_limit_returns_default_when_no_organization(self):
        """Test getting default cost limit when no organization."""
        # Remove the mock for this test to test the actual method
        delattr(self.tracker, '_get_cost_limit')
        
        # Arrange
        business_id = "test-business-id"
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        # Act
        result = await self.tracker._get_cost_limit(business_id)
        
        # Assert
        assert result == self.default_limit

    @pytest.mark.asyncio
    async def test_calculate_monthly_cost_from_logs_sums_usage(self):
        """Test calculating monthly cost from usage logs."""
        # Arrange
        business_id = "test-business-id"
        month = date(2024, 1, 1)
        total_cost = Decimal("42.50")
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = total_cost
        self.mock_db.execute.return_value = mock_result
        
        # Act
        result = await self.tracker._calculate_monthly_cost_from_logs(business_id, month)
        
        # Assert
        assert result == total_cost

    @pytest.mark.asyncio
    async def test_calculate_monthly_cost_from_logs_handles_none_result(self):
        """Test handling None result from cost calculation."""
        # Arrange
        business_id = "test-business-id"
        month = date(2024, 1, 1)
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        # Act
        result = await self.tracker._calculate_monthly_cost_from_logs(business_id, month)
        
        # Assert
        assert result == Decimal("0.00")

    # Budget Management Tests

    @pytest.mark.asyncio
    async def test_check_budget_status_returns_comprehensive_info(self):
        """Test budget status check returns all required information."""
        # Arrange
        business_id = "test-business-id"
        current_cost = Decimal("75.00")
        cost_limit = Decimal("100.00")
        
        with patch.object(self.tracker, 'get_monthly_cost', return_value=current_cost):
            with patch.object(self.tracker, '_get_cost_limit', return_value=cost_limit):
                # Act
                result = await self.tracker.check_budget_status(business_id)
                
                # Assert
                assert result["current_cost"] == current_cost
                assert result["cost_limit"] == cost_limit
                assert result["usage_percentage"] == 75.0
                assert result["remaining_budget"] == Decimal("25.00")
                assert result["is_warning"] is False  # Below 80% threshold
                assert result["is_exceeded"] is False
                assert result["disabled_operations"] == []

    @pytest.mark.asyncio
    async def test_check_budget_status_detects_warning_threshold(self):
        """Test budget status detects warning threshold at 80%."""
        # Arrange
        business_id = "test-business-id"
        current_cost = Decimal("85.00")  # 85% of 100
        cost_limit = Decimal("100.00")
        
        with patch.object(self.tracker, 'get_monthly_cost', return_value=current_cost):
            with patch.object(self.tracker, '_get_cost_limit', return_value=cost_limit):
                # Act
                result = await self.tracker.check_budget_status(business_id)
                
                # Assert
                assert result["is_warning"] is True
                assert result["usage_percentage"] == 85.0

    @pytest.mark.asyncio
    async def test_check_budget_status_detects_exceeded_limit(self):
        """Test budget status detects when limit is exceeded."""
        # Arrange
        business_id = "test-business-id"
        current_cost = Decimal("120.00")  # Over limit
        cost_limit = Decimal("100.00")
        
        with patch.object(self.tracker, 'get_monthly_cost', return_value=current_cost):
            with patch.object(self.tracker, '_get_cost_limit', return_value=cost_limit):
                # Act
                result = await self.tracker.check_budget_status(business_id)
                
                # Assert
                assert result["is_exceeded"] is True
                assert result["remaining_budget"] == Decimal("-20.00")

    @pytest.mark.asyncio
    async def test_validate_operation_allows_when_within_budget(self):
        """Test operation validation allows operations within budget."""
        # Arrange
        business_id = "test-business-id"
        operation = "classify"
        
        mock_budget_status = {
            "current_cost": Decimal("50.00"),
            "cost_limit": Decimal("100.00"),
            "usage_percentage": 50.0,
            "is_warning": False,
            "is_exceeded": False,
            "disabled_operations": []
        }
        
        with patch.object(self.tracker, 'check_budget_status', return_value=mock_budget_status):
            # Act
            result = await self.tracker.validate_operation(business_id, operation)
            
            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_operation_raises_warning_at_threshold(self):
        """Test operation validation raises warning at 80% threshold."""
        # Arrange
        business_id = "test-business-id"
        operation = "classify"
        
        mock_budget_status = {
            "current_cost": Decimal("85.00"),
            "cost_limit": Decimal("100.00"),
            "usage_percentage": 85.0,
            "is_warning": True,
            "is_exceeded": False,
            "disabled_operations": []
        }
        
        with patch.object(self.tracker, 'check_budget_status', return_value=mock_budget_status):
            # Act & Assert
            with pytest.raises(BudgetWarningException) as exc_info:
                await self.tracker.validate_operation(business_id, operation)
            
            assert exc_info.value.usage_percentage == 85.0
            assert exc_info.value.threshold == 80.0

    @pytest.mark.asyncio
    async def test_validate_operation_raises_exception_when_exceeded(self):
        """Test operation validation raises exception when limit exceeded."""
        # Arrange
        business_id = "test-business-id"
        operation = "classify"
        
        mock_budget_status = {
            "current_cost": Decimal("120.00"),
            "cost_limit": Decimal("100.00"),
            "usage_percentage": 120.0,
            "is_warning": True,
            "is_exceeded": True,
            "disabled_operations": []
        }
        
        with patch.object(self.tracker, 'check_budget_status', return_value=mock_budget_status):
            with patch.object(self.tracker, '_disable_non_essential_operations') as mock_disable:
                # Act & Assert
                with pytest.raises(CostLimitExceededException) as exc_info:
                    await self.tracker.validate_operation(business_id, operation)
                
                assert exc_info.value.current_cost == Decimal("120.00")
                assert exc_info.value.cost_limit == Decimal("100.00")
                mock_disable.assert_called_once_with(business_id)

    @pytest.mark.asyncio
    async def test_validate_operation_blocks_disabled_operations(self):
        """Test operation validation blocks disabled operations."""
        # Arrange
        business_id = "test-business-id"
        operation = "chat"
        
        mock_budget_status = {
            "current_cost": Decimal("50.00"),
            "cost_limit": Decimal("100.00"),
            "usage_percentage": 50.0,
            "is_warning": False,
            "is_exceeded": False,
            "disabled_operations": ["chat", "report"]
        }
        
        with patch.object(self.tracker, 'check_budget_status', return_value=mock_budget_status):
            # Act
            result = await self.tracker.validate_operation(business_id, operation)
            
            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_disable_non_essential_operations_disables_chat_and_report(self):
        """Test disabling non-essential operations."""
        # Arrange
        business_id = "test-business-id"
        
        # Act
        await self.tracker._disable_non_essential_operations(business_id)
        
        # Assert
        assert business_id in self.tracker._disabled_operations
        assert "chat" in self.tracker._disabled_operations[business_id]
        assert "report" in self.tracker._disabled_operations[business_id]
        assert "classify" not in self.tracker._disabled_operations[business_id]

    @pytest.mark.asyncio
    async def test_enable_all_operations_clears_disabled_list(self):
        """Test enabling all operations clears disabled list."""
        # Arrange
        business_id = "test-business-id"
        self.tracker._disabled_operations[business_id] = ["chat", "report"]
        
        # Act
        await self.tracker.enable_all_operations(business_id)
        
        # Assert
        assert business_id not in self.tracker._disabled_operations

    @pytest.mark.asyncio
    async def test_get_cost_breakdown_by_period_returns_detailed_breakdown(self):
        """Test getting detailed cost breakdown by period."""
        # Arrange
        business_id = "test-business-id"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Mock database result
        mock_row = MagicMock()
        mock_row.ai_service = "gpt5_nano"
        mock_row.operation = "classify"
        mock_row.total_cost = Decimal("25.50")
        mock_row.total_tokens = 1500
        mock_row.operation_count = 100
        mock_row.avg_processing_time = 250.0
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        self.mock_db.execute.return_value = mock_result
        
        # Act
        result = await self.tracker.get_cost_breakdown_by_period(business_id, start_date, end_date)
        
        # Assert
        assert result["period"]["start_date"] == start_date
        assert result["period"]["end_date"] == end_date
        assert result["total_cost"] == Decimal("25.50")
        assert result["total_tokens"] == 1500
        assert result["total_operations"] == 100
        assert "gpt5_nano" in result["services"]
        assert result["services"]["gpt5_nano"]["operations"]["classify"]["cost"] == Decimal("25.50")

    @pytest.mark.asyncio
    async def test_get_projected_monthly_cost_calculates_projection(self):
        """Test projected monthly cost calculation."""
        # Arrange
        business_id = "test-business-id"
        current_cost = Decimal("30.00")  # Cost for 10 days
        
        with patch.object(self.tracker, 'get_monthly_cost', return_value=current_cost):
            with patch('backend.ai.cost_tracker.date') as mock_date:
                # Mock current date as 10th of month
                mock_today = date(2024, 1, 10)
                mock_date.today.return_value = mock_today
                
                # Act
                result = await self.tracker.get_projected_monthly_cost(business_id)
                
                # Assert
                # Daily average: 30/10 = 3, projected: 3*31 = 93
                assert result == Decimal("93.00")

    @pytest.mark.asyncio
    async def test_get_projected_monthly_cost_handles_zero_days(self):
        """Test projected cost calculation handles zero days elapsed."""
        # Arrange
        business_id = "test-business-id"
        
        with patch.object(self.tracker, 'get_monthly_cost', return_value=Decimal("0.00")):
            with patch('backend.ai.cost_tracker.date') as mock_date:
                # Mock current date as 1st of month (day = 1, so days_elapsed = 1)
                mock_today = date(2024, 1, 1)
                mock_date.today.return_value = mock_today
                
                # Act
                result = await self.tracker.get_projected_monthly_cost(business_id)
                
                # Assert
                # With 0 cost and 1 day elapsed: 0/1 * 31 = 0
                assert result == Decimal("0.00")