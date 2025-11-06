"""
Unit tests for Scheduler Service.

Tests the SchedulerService including automated review processing,
analytics refresh scheduling, and cache cleanup.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime, timedelta

from backend.services.scheduler_service import SchedulerService


class MockReviewProcessor:
    """Mock review processor for testing."""

    def __init__(self):
        self.process_calls = []

    async def process_new_reviews(self, business_id):
        """Mock process new reviews."""
        self.process_calls.append(business_id)
        
        from backend.services.review.processor import ProcessingResult
        return ProcessingResult(
            processed_count=5,
            success_count=5,
            error_count=0,
            critical_reviews_found=1,
            processing_time_ms=2500,
            errors=[],
        )


class MockAnalyticsService:
    """Mock analytics service for testing."""

    def __init__(self):
        self.update_calls = []
        self.refresh_calls = 0
        self.cleanup_calls = 0

    async def update_business_analytics(self, business_id):
        """Mock update business analytics."""
        self.update_calls.append(business_id)

    async def schedule_cache_refresh(self):
        """Mock schedule cache refresh."""
        self.refresh_calls += 1

    async def cleanup_expired_cache(self):
        """Mock cleanup expired cache."""
        self.cleanup_calls += 1
        return 3  # Number of entries cleaned

    async def get_cache_stats(self):
        """Mock get cache stats."""
        return {
            "total_entries": 10,
            "active_entries": 8,
            "expired_entries": 2,
            "cache_ttl_hours": 4,
        }


class MockGooglePlacesClient:
    """Mock Google Places client for testing."""

    def __init__(self):
        self.import_calls = []

    async def import_reviews(self, google_place_id, business_id):
        """Mock import reviews."""
        self.import_calls.append((google_place_id, business_id))
        
        # Return a mock object with the expected attributes
        result = Mock()
        result.imported_count = 3
        result.skipped_count = 2
        result.total_available = 5
        result.error_count = 0  # Add this missing attribute
        result.errors = []  # Add this missing attribute
        return result
    
    async def import_reviews_with_retry(self, business_id):
        """Mock import reviews with retry."""
        return await self.import_reviews(f"place-{business_id}", business_id)


class MockBusinessRepository:
    """Mock business repository for testing."""

    def __init__(self):
        self.businesses = []

    async def get_businesses_needing_analysis(self, limit=1000):
        """Mock get businesses needing analysis."""
        return self.businesses[:limit]

    def add_business(self, business_id=None, name="Test Business", google_place_id="test-place-123"):
        """Helper to add business."""
        if business_id is None:
            business_id = uuid4()
        
        business = Mock()
        business.id = business_id
        business.name = name
        business.google_place_id = google_place_id
        
        self.businesses.append(business)
        return business


class TestSchedulerService:
    """Test suite for SchedulerService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.review_processor = MockReviewProcessor()
        self.analytics_service = MockAnalyticsService()
        self.google_places_client = MockGooglePlacesClient()
        self.business_repo = MockBusinessRepository()
        
        self.service = SchedulerService(
            review_processor=self.review_processor,
            analytics_service=self.analytics_service,
            review_import_service=self.google_places_client,  # Using mock as import service
            business_repository=self.business_repo,
        )

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_trigger_daily_review_processing_success(self):
        """Test manual trigger of daily review processing."""
        # Arrange
        business1 = self.business_repo.add_business(name="Restaurant 1")
        business2 = self.business_repo.add_business(name="Restaurant 2")

        # Act
        result = await self.service.trigger_daily_review_processing()

        # Assert
        assert result["businesses_processed"] == 2
        assert result["total_reviews_processed"] == 10  # 5 per business
        assert result["total_errors"] == 0
        assert len(result["business_results"]) == 2

        # Verify each business was processed
        business_results = result["business_results"]
        assert business_results[0]["business_name"] == "Restaurant 1"
        assert business_results[0]["processed_reviews"] == 5
        assert business_results[0]["critical_reviews"] == 1
        assert business_results[1]["business_name"] == "Restaurant 2"

        # Verify services were called
        assert len(self.google_places_client.import_calls) == 2
        assert len(self.review_processor.process_calls) == 2
        assert len(self.analytics_service.update_calls) == 2

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_trigger_daily_review_processing_no_businesses(self):
        """Test daily review processing with no businesses."""
        # Arrange - no businesses added

        # Act
        result = await self.service.trigger_daily_review_processing()

        # Assert
        assert result["businesses_processed"] == 0
        assert result["total_reviews_processed"] == 0
        assert result["total_errors"] == 0
        assert len(result["business_results"]) == 0

        # Verify no services were called
        assert len(self.google_places_client.import_calls) == 0
        assert len(self.review_processor.process_calls) == 0
        assert len(self.analytics_service.update_calls) == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_trigger_daily_review_processing_with_errors(self):
        """Test daily review processing handles individual business errors."""
        # Arrange
        business1 = self.business_repo.add_business(name="Restaurant 1")
        business2 = self.business_repo.add_business(name="Restaurant 2")

        # Mock Google Places client to fail for second business
        original_import = self.google_places_client.import_reviews
        
        async def mock_import_with_error(google_place_id, business_id):
            if business_id == business2.id:
                raise Exception("API rate limit exceeded")
            return await original_import(google_place_id, business_id)
        
        self.google_places_client.import_reviews = mock_import_with_error

        # Act
        result = await self.service.trigger_daily_review_processing()

        # Assert
        assert result["businesses_processed"] == 2
        assert result["total_reviews_processed"] == 5  # Only first business succeeded
        assert result["total_errors"] == 1

        # Verify error is recorded
        business_results = result["business_results"]
        assert "error" not in business_results[0]  # First business succeeded
        assert "error" in business_results[1]  # Second business failed
        assert "API rate limit" in business_results[1]["error"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_trigger_analytics_refresh(self):
        """Test manual trigger of analytics refresh."""
        # Act
        result = await self.service.trigger_analytics_refresh()

        # Assert
        assert result["status"] == "completed"
        assert "timestamp" in result
        assert "cache_stats" in result
        assert result["cache_stats"]["total_entries"] == 10

        # Verify analytics service was called
        assert self.analytics_service.refresh_calls == 1

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_scheduler_status_not_running(self):
        """Test getting scheduler status when not running."""
        # Act
        status = await self.service.get_scheduler_status()

        # Assert
        assert status["running"] is False
        assert status["active_tasks"] == 0
        assert status["total_tasks"] == 0
        assert len(status["task_status"]) == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_scheduler_status_running(self):
        """Test getting scheduler status when running."""
        # Arrange
        await self.service.start()

        try:
            # Act
            status = await self.service.get_scheduler_status()

            # Assert
            assert status["running"] is True
            assert status["total_tasks"] == 3  # 3 background tasks
            assert len(status["task_status"]) == 3

        finally:
            # Cleanup
            await self.service.stop()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_health_check_not_running(self):
        """Test health check when scheduler is not running."""
        # Act
        is_healthy = await self.service.health_check()

        # Assert
        assert is_healthy is False

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_health_check_running(self):
        """Test health check when scheduler is running."""
        # Arrange
        await self.service.start()

        try:
            # Act
            is_healthy = await self.service.health_check()

            # Assert
            assert is_healthy is True

        finally:
            # Cleanup
            await self.service.stop()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self):
        """Test scheduler start and stop lifecycle."""
        # Verify initial state
        assert self.service._running is False
        assert len(self.service._tasks) == 0

        # Start scheduler
        await self.service.start()

        # Verify running state
        assert self.service._running is True
        assert len(self.service._tasks) == 3

        # Stop scheduler
        await self.service.stop()

        # Verify stopped state
        assert self.service._running is False
        assert len(self.service._tasks) == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test starting scheduler when already running."""
        # Arrange
        await self.service.start()

        try:
            # Act - Try to start again
            await self.service.start()

            # Assert - Should still be running with same tasks
            assert self.service._running is True
            assert len(self.service._tasks) == 3

        finally:
            # Cleanup
            await self.service.stop()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stopping scheduler when not running."""
        # Act - Should not raise error
        await self.service.stop()

        # Assert
        assert self.service._running is False
        assert len(self.service._tasks) == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_daily_processing_comprehensive_result(self):
        """Test daily processing returns comprehensive result data."""
        # Arrange
        business = self.business_repo.add_business(
            name="Test Restaurant",
            google_place_id="place-123"
        )

        # Act
        result = await self.service.trigger_daily_review_processing()

        # Assert
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)
        
        business_result = result["business_results"][0]
        assert business_result["business_id"] == str(business.id)
        assert business_result["business_name"] == "Test Restaurant"
        assert business_result["imported_reviews"] == 3
        assert business_result["processed_reviews"] == 5
        assert business_result["critical_reviews"] == 1
        assert business_result["processing_errors"] == []

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_processing_with_mixed_results(self):
        """Test processing with mix of successful and failed businesses."""
        # Arrange
        success_business = self.business_repo.add_business(name="Success Restaurant")
        error_business = self.business_repo.add_business(name="Error Restaurant")

        # Mock review processor to fail for error business
        original_process = self.review_processor.process_new_reviews
        
        async def mock_process_with_error(business_id):
            if business_id == error_business.id:
                raise Exception("Processing failed")
            return await original_process(business_id)
        
        self.review_processor.process_new_reviews = mock_process_with_error

        # Act
        result = await self.service.trigger_daily_review_processing()

        # Assert
        assert result["businesses_processed"] == 2
        assert result["total_errors"] == 1

        # Check individual business results
        business_results = {br["business_name"]: br for br in result["business_results"]}
        
        success_result = business_results["Success Restaurant"]
        assert "error" not in success_result
        assert success_result["processed_reviews"] == 5

        error_result = business_results["Error Restaurant"]
        assert "error" in error_result
        assert "Processing failed" in error_result["error"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_analytics_refresh_error_handling(self):
        """Test analytics refresh handles errors gracefully."""
        # Arrange
        self.analytics_service.schedule_cache_refresh = AsyncMock(
            side_effect=Exception("Cache refresh failed")
        )

        # Act & Assert
        with pytest.raises(Exception, match="Cache refresh failed"):
            await self.service.trigger_analytics_refresh()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_concurrent_processing_safety(self):
        """Test that concurrent processing calls are handled safely."""
        # Arrange
        businesses = [
            self.business_repo.add_business(name=f"Restaurant {i}")
            for i in range(3)
        ]

        # Act - Trigger multiple concurrent processing calls
        tasks = [
            self.service.trigger_daily_review_processing()
            for _ in range(2)
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        # Both calls should succeed
        assert len(results) == 2
        for result in results:
            assert result["businesses_processed"] == 3
            assert result["total_errors"] == 0

        # Verify all businesses were processed in both calls
        # (Each call processes all businesses independently)
        total_process_calls = len(self.review_processor.process_calls)
        assert total_process_calls == 6  # 3 businesses * 2 calls

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_large_business_count_handling(self):
        """Test handling of large number of businesses."""
        # Arrange - Add many businesses
        businesses = [
            self.business_repo.add_business(name=f"Restaurant {i}")
            for i in range(50)
        ]

        # Act
        result = await self.service.trigger_daily_review_processing()

        # Assert
        assert result["businesses_processed"] == 50
        assert result["total_reviews_processed"] == 250  # 5 per business
        assert len(result["business_results"]) == 50

        # Verify all services were called for each business
        assert len(self.google_places_client.import_calls) == 50
        assert len(self.review_processor.process_calls) == 50
        assert len(self.analytics_service.update_calls) == 50