"""
Unit tests for Analytics Service.

Tests the AnalyticsService including dashboard data calculation,
caching, trend analysis, and multi-business metrics.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from backend.services.analytics_service import AnalyticsService, CacheEntry
from backend.services.analytics.calculator import DashboardData, TrendAnalysis


class MockAnalyticsCalculator:
    """Mock analytics calculator for testing."""

    def __init__(self):
        self.dashboard_data_calls = []
        self.trends_calls = []
        self.score_calls = []

    async def calculate_dashboard_data(self, business_id):
        """Mock calculate dashboard data."""
        self.dashboard_data_calls.append(business_id)
        
        return DashboardData(
            business_id=str(business_id),
            avg_rating=Decimal("4.2"),
            total_reviews=150,
            sentiment_distribution={"positive": 60.0, "neutral": 25.0, "negative": 15.0},
            top_topics=["food_quality", "service", "ambiance"],
            competitor_mentions=2,
            response_rate=Decimal("75.0"),
            avg_response_time_hours=Decimal("2.5"),
            trend_data=[
                {"date": "2024-01-01", "avg_rating": 4.1, "review_count": 5},
                {"date": "2024-01-02", "avg_rating": 4.3, "review_count": 8},
            ],
            last_updated=datetime.now(timezone.utc),
        )

    async def calculate_trends(self, business_id, days=30):
        """Mock calculate trends."""
        self.trends_calls.append((business_id, days))
        
        return TrendAnalysis(
            period_start=datetime.now().date() - timedelta(days=days),
            period_end=datetime.now().date(),
            sentiment_trend="improving",
            rating_trend="stable",
            review_volume_trend="increasing",
            key_insights=[
                "Customer sentiment has improved",
                "Review volume is increasing",
                "Food quality remains top topic",
            ],
        )

    async def calculate_business_score(self, business_id):
        """Mock calculate business score."""
        self.score_calls.append(business_id)
        
        return {
            "overall_score": 85.5,
            "rating_score": 84.0,
            "sentiment_score": 90.0,
            "volume_score": 82.0,
            "grade": "B",
            "recommendations": [
                "Continue excellent service",
                "Monitor food quality",
                "Encourage more reviews",
            ],
        }


class MockBusinessRepository:
    """Mock business repository for testing."""

    def __init__(self):
        self.businesses = {}
        self.rating_updates = []

    async def calculate_rating_stats(self, business_id):
        """Mock calculate rating stats."""
        return 4.2, 150

    async def update_rating_stats(self, business_id, avg_rating, total_reviews):
        """Mock update rating stats."""
        self.rating_updates.append((business_id, avg_rating, total_reviews))

    async def get_businesses_needing_analysis(self, limit=100):
        """Mock get businesses needing analysis."""
        return [
            Mock(id=uuid4(), name=f"Business {i}")
            for i in range(min(3, limit))
        ]

    def add_business(self, business_id, name="Test Business"):
        """Helper to add business."""
        business = Mock()
        business.id = business_id
        business.name = name
        self.businesses[business_id] = business
        return business


class TestAnalyticsService:
    """Test suite for AnalyticsService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.review_repo = AsyncMock()
        self.classification_repo = AsyncMock()
        self.business_repo = MockBusinessRepository()
        
        self.service = AnalyticsService(
            review_repository=self.review_repo,
            classification_repository=self.classification_repo,
            business_repository=self.business_repo,
            cache_ttl_hours=4,
        )
        
        # Replace calculator with mock
        self.mock_calculator = MockAnalyticsCalculator()
        self.service._calculator = self.mock_calculator

        # Test data
        self.business_id = uuid4()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_dashboard_data_fresh_calculation(self):
        """Test getting dashboard data with fresh calculation."""
        # Act
        result = await self.service.get_dashboard_data(self.business_id)

        # Assert
        assert result.business_id == str(self.business_id)
        assert result.avg_rating == Decimal("4.2")
        assert result.total_reviews == 150
        assert result.sentiment_distribution["positive"] == 60.0
        assert len(result.top_topics) == 3
        assert "food_quality" in result.top_topics

        # Verify calculator was called
        assert len(self.mock_calculator.dashboard_data_calls) == 1
        assert self.mock_calculator.dashboard_data_calls[0] == self.business_id

        # Verify data was cached
        cache_key = f"dashboard_{self.business_id}"
        assert cache_key in self.service._cache

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_dashboard_data_from_cache(self):
        """Test getting dashboard data from cache."""
        # Arrange - First call to populate cache
        await self.service.get_dashboard_data(self.business_id)
        
        # Reset calculator call tracking
        self.mock_calculator.dashboard_data_calls.clear()

        # Act - Second call should use cache
        result = await self.service.get_dashboard_data(self.business_id)

        # Assert
        assert result.avg_rating == Decimal("4.2")

        # Verify calculator was NOT called again
        assert len(self.mock_calculator.dashboard_data_calls) == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_dashboard_data_force_refresh(self):
        """Test getting dashboard data with force refresh."""
        # Arrange - First call to populate cache
        await self.service.get_dashboard_data(self.business_id)
        
        # Reset calculator call tracking
        self.mock_calculator.dashboard_data_calls.clear()

        # Act - Force refresh should bypass cache
        result = await self.service.get_dashboard_data(self.business_id, force_refresh=True)

        # Assert
        assert result.avg_rating == Decimal("4.2")

        # Verify calculator was called again
        assert len(self.mock_calculator.dashboard_data_calls) == 1

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_trend_analysis_with_caching(self):
        """Test getting trend analysis with caching."""
        # Act - First call
        result1 = await self.service.get_trend_analysis(self.business_id, days=30)

        # Assert
        assert result1.sentiment_trend == "improving"
        assert result1.rating_trend == "stable"
        assert len(result1.key_insights) == 3

        # Verify calculator was called
        assert len(self.mock_calculator.trends_calls) == 1

        # Act - Second call should use cache
        result2 = await self.service.get_trend_analysis(self.business_id, days=30)

        # Assert - Same result
        assert result2.sentiment_trend == "improving"

        # Verify calculator was NOT called again
        assert len(self.mock_calculator.trends_calls) == 1

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_trend_analysis_different_periods(self):
        """Test trend analysis with different time periods."""
        # Act
        result_30d = await self.service.get_trend_analysis(self.business_id, days=30)
        result_7d = await self.service.get_trend_analysis(self.business_id, days=7)

        # Assert
        assert result_30d.sentiment_trend == "improving"
        assert result_7d.sentiment_trend == "improving"

        # Verify calculator was called twice (different cache keys)
        assert len(self.mock_calculator.trends_calls) == 2
        assert self.mock_calculator.trends_calls[0] == (self.business_id, 30)
        assert self.mock_calculator.trends_calls[1] == (self.business_id, 7)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_business_score_with_caching(self):
        """Test getting business score with caching."""
        # Act - First call
        result1 = await self.service.get_business_score(self.business_id)

        # Assert
        assert result1["overall_score"] == 85.5
        assert result1["grade"] == "B"
        assert len(result1["recommendations"]) == 3

        # Verify calculator was called
        assert len(self.mock_calculator.score_calls) == 1

        # Act - Second call should use cache
        result2 = await self.service.get_business_score(self.business_id)

        # Assert - Same result
        assert result2["overall_score"] == 85.5

        # Verify calculator was NOT called again
        assert len(self.mock_calculator.score_calls) == 1

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_update_business_analytics(self):
        """Test updating business analytics."""
        # Arrange - Populate cache first
        await self.service.get_dashboard_data(self.business_id)
        cache_key = f"dashboard_{self.business_id}"
        assert cache_key in self.service._cache

        # Act
        await self.service.update_business_analytics(self.business_id)

        # Assert
        # Verify rating stats were updated
        assert len(self.business_repo.rating_updates) == 1
        update = self.business_repo.rating_updates[0]
        assert update[0] == self.business_id
        assert update[1] == 4.2  # avg_rating
        assert update[2] == 150  # total_reviews

        # Verify cache was invalidated and repopulated
        assert cache_key in self.service._cache  # Should be repopulated

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_multi_business_dashboard(self):
        """Test getting dashboard data for multiple businesses."""
        # Arrange
        business_ids = [uuid4(), uuid4(), uuid4()]

        # Act
        result = await self.service.get_multi_business_dashboard(business_ids)

        # Assert
        assert len(result) == 3
        for business_id in business_ids:
            assert str(business_id) in result
            dashboard_data = result[str(business_id)]
            assert dashboard_data.avg_rating == Decimal("4.2")
            assert dashboard_data.total_reviews == 150

        # Verify calculator was called for each business
        assert len(self.mock_calculator.dashboard_data_calls) == 3

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_multi_business_dashboard_with_error(self):
        """Test multi-business dashboard handles individual business errors."""
        # Arrange
        business_ids = [uuid4(), uuid4()]
        
        # Mock calculator to fail for second business
        original_method = self.mock_calculator.calculate_dashboard_data
        
        async def mock_with_error(business_id):
            if business_id == business_ids[1]:
                raise Exception("Database error")
            return await original_method(business_id)
        
        self.mock_calculator.calculate_dashboard_data = mock_with_error

        # Act
        result = await self.service.get_multi_business_dashboard(business_ids)

        # Assert
        assert len(result) == 2

        # First business should have normal data
        assert result[str(business_ids[0])].avg_rating == Decimal("4.2")

        # Second business should have empty data
        assert result[str(business_ids[1])].avg_rating == Decimal("0.0")
        assert result[str(business_ids[1])].total_reviews == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_consolidated_metrics(self):
        """Test getting consolidated metrics across multiple businesses."""
        # Arrange
        business_ids = [uuid4(), uuid4()]

        # Act
        result = await self.service.get_consolidated_metrics(business_ids)

        # Assert
        assert result["total_businesses"] == 2
        assert result["total_reviews"] == 300  # 150 * 2
        assert result["avg_rating"] == 4.2  # Same rating for both
        assert "positive" in result["overall_sentiment"]
        assert result["overall_sentiment"]["positive"] == 60.0
        assert len(result["top_topics"]) > 0
        assert "food_quality" in result["top_topics"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_consolidated_metrics_no_reviews(self):
        """Test consolidated metrics when no reviews exist."""
        # Arrange
        business_ids = [uuid4()]
        
        # Mock calculator to return empty data
        async def mock_empty_dashboard(business_id):
            return DashboardData(
                business_id=str(business_id),
                avg_rating=Decimal("0.0"),
                total_reviews=0,
                sentiment_distribution={},
                top_topics=[],
                competitor_mentions=0,
                response_rate=Decimal("0.0"),
                avg_response_time_hours=None,
                trend_data=[],
                last_updated=datetime.now(timezone.utc),
            )
        
        self.mock_calculator.calculate_dashboard_data = mock_empty_dashboard

        # Act
        result = await self.service.get_consolidated_metrics(business_ids)

        # Assert
        assert result["total_businesses"] == 1
        assert result["total_reviews"] == 0
        assert result["avg_rating"] == 0.0
        assert result["overall_sentiment"]["positive"] == 0
        assert len(result["top_topics"]) == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_schedule_cache_refresh(self):
        """Test scheduled cache refresh."""
        # Act
        await self.service.schedule_cache_refresh()

        # Assert
        # Verify calculator was called for businesses needing analysis
        # (MockBusinessRepository returns 3 businesses)
        assert len(self.mock_calculator.dashboard_data_calls) == 3

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation for a business."""
        # Arrange - Populate cache with multiple entries
        await self.service.get_dashboard_data(self.business_id)
        await self.service.get_trend_analysis(self.business_id, days=30)
        await self.service.get_business_score(self.business_id)
        
        # Verify cache has entries
        assert len(self.service._cache) == 3

        # Act
        await self.service._invalidate_business_cache(self.business_id)

        # Assert
        # All entries for this business should be removed
        assert len(self.service._cache) == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test getting cache statistics."""
        # Arrange - Add some cache entries
        await self.service.get_dashboard_data(self.business_id)
        await self.service.get_trend_analysis(self.business_id, days=30)

        # Act
        stats = await self.service.get_cache_stats()

        # Assert
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        assert stats["expired_entries"] == 0
        assert stats["cache_ttl_hours"] == 4

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache expiration handling."""
        # Arrange - Manually add expired cache entry
        expired_entry = CacheEntry(
            data=Mock(),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired 1 hour ago
        )
        self.service._cache["expired_key"] = expired_entry

        # Add fresh entry
        await self.service.get_dashboard_data(self.business_id)

        # Act
        stats = await self.service.get_cache_stats()

        # Assert
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 1

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_cleanup_expired_cache(self):
        """Test cleanup of expired cache entries."""
        # Arrange - Add expired and active entries
        expired_entry = CacheEntry(
            data=Mock(),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        self.service._cache["expired_key"] = expired_entry

        await self.service.get_dashboard_data(self.business_id)  # Active entry

        # Verify initial state
        assert len(self.service._cache) == 2

        # Act
        removed_count = await self.service.cleanup_expired_cache()

        # Assert
        assert removed_count == 1
        assert len(self.service._cache) == 1
        assert "expired_key" not in self.service._cache

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing all cache."""
        # Arrange - Populate cache
        await self.service.get_dashboard_data(self.business_id)
        await self.service.get_trend_analysis(self.business_id, days=30)
        
        assert len(self.service._cache) == 2

        # Act
        await self.service.clear_cache()

        # Assert
        assert len(self.service._cache) == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_error_handling_with_fallback_cache(self):
        """Test error handling falls back to expired cache when available."""
        # Arrange - Populate cache first
        await self.service.get_dashboard_data(self.business_id)
        
        # Manually expire the cache entry
        cache_key = f"dashboard_{self.business_id}"
        self.service._cache[cache_key].expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Mock calculator to fail
        self.mock_calculator.calculate_dashboard_data = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Act
        result = await self.service.get_dashboard_data(self.business_id)

        # Assert
        # Should return expired cached data instead of raising exception
        assert result.avg_rating == Decimal("4.2")

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """Test concurrent access to cache doesn't cause issues."""
        # Arrange
        business_ids = [uuid4() for _ in range(5)]

        # Act - Concurrent requests for different businesses
        tasks = [
            self.service.get_dashboard_data(business_id)
            for business_id in business_ids
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 5
        for result in results:
            assert result.avg_rating == Decimal("4.2")

        # Verify cache has entries for all businesses
        assert len(self.service._cache) == 5