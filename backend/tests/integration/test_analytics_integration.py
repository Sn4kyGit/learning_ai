"""
Integration tests for analytics service.

Tests the AnalyticsService with real database operations,
cache management, and dashboard data generation.
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta

from backend.services.analytics_service import AnalyticsService
from backend.db.repositories.review import ReviewRepository
from backend.db.repositories.classification import ClassificationRepository
from backend.db.repositories.business import BusinessRepository
from backend.db.models import Review, Classification, Business


class TestAnalyticsIntegration:
    """Integration test suite for analytics service."""

    @pytest.fixture
    async def repositories(self, test_db_session):
        """Create repository instances."""
        return {
            "review": ReviewRepository(test_db_session),
            "classification": ClassificationRepository(test_db_session),
            "business": BusinessRepository(test_db_session),
        }

    @pytest.fixture
    async def analytics_service(self, repositories):
        """Create analytics service."""
        return AnalyticsService(
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            business_repository=repositories["business"],
            cache_ttl_hours=1,  # Short TTL for testing
        )

    @pytest.fixture
    async def business_with_reviews(self, test_db_session, test_business):
        """Create business with reviews and classifications."""
        # Create reviews with different sentiments and ratings
        reviews_data = [
            {
                "author_name": "Happy Customer 1",
                "rating": 5,
                "text": "Excellent food and outstanding service!",
                "sentiment": "positive",
                "topics": ["food_quality", "service"],
                "urgency": "low",
            },
            {
                "author_name": "Happy Customer 2", 
                "rating": 5,
                "text": "Amazing ambiance and delicious meals!",
                "sentiment": "positive",
                "topics": ["ambiance", "food_quality"],
                "urgency": "low",
            },
            {
                "author_name": "Satisfied Customer",
                "rating": 4,
                "text": "Good food, reasonable prices.",
                "sentiment": "positive",
                "topics": ["food_quality", "price"],
                "urgency": "low",
            },
            {
                "author_name": "Neutral Customer",
                "rating": 3,
                "text": "Average experience, nothing special.",
                "sentiment": "neutral",
                "topics": ["service"],
                "urgency": "low",
            },
            {
                "author_name": "Disappointed Customer",
                "rating": 2,
                "text": "Slow service and cold food.",
                "sentiment": "negative",
                "topics": ["service", "food_quality"],
                "urgency": "high",
            },
            {
                "author_name": "Unhappy Customer",
                "rating": 1,
                "text": "Terrible experience, dirty restaurant.",
                "sentiment": "negative",
                "topics": ["cleanliness", "service"],
                "urgency": "high",
            },
        ]

        reviews = []
        classifications = []

        for i, review_data in enumerate(reviews_data):
            # Create review
            review = Review(
                business_id=test_business.id,
                author_name=review_data["author_name"],
                rating=review_data["rating"],
                text=review_data["text"],
                language="en",
                published_at=datetime.utcnow() - timedelta(days=i),
                source="google",
                external_id=f"integration-review-{i}",
            )
            test_db_session.add(review)
            reviews.append(review)

        await test_db_session.commit()

        # Refresh reviews to get IDs
        for review in reviews:
            await test_db_session.refresh(review)

        # Create classifications
        for i, (review, review_data) in enumerate(zip(reviews, reviews_data)):
            classification = Classification(
                review_id=review.id,
                sentiment=review_data["sentiment"],
                topics=review_data["topics"],
                urgency=review_data["urgency"],
                competitor_mentioned=False,
                confidence_score=0.90 + (i * 0.01),  # Varying confidence
                ai_model="test-model",
                processing_time_ms=100 + (i * 10),
            )
            test_db_session.add(classification)
            classifications.append(classification)

        await test_db_session.commit()

        return {
            "business": test_business,
            "reviews": reviews,
            "classifications": classifications,
        }

    @pytest.mark.asyncio
    async def test_dashboard_data_calculation_integration(
        self, business_with_reviews, analytics_service
    ):
        """Test dashboard data calculation with real database data."""
        # Arrange
        business = business_with_reviews["business"]

        # Act
        dashboard_data = await analytics_service.get_dashboard_data(business.id)

        # Assert
        assert dashboard_data.business_id == str(business.id)
        assert dashboard_data.total_reviews == 6
        
        # Verify average rating calculation
        expected_avg = (5 + 5 + 4 + 3 + 2 + 1) / 6  # 3.33
        assert abs(float(dashboard_data.avg_rating) - expected_avg) < 0.01

        # Verify sentiment distribution
        sentiment_dist = dashboard_data.sentiment_distribution
        assert abs(sentiment_dist["positive"] - 50.0) < 0.1  # 3 out of 6
        assert abs(sentiment_dist["neutral"] - 16.67) < 0.1  # 1 out of 6 (rounded)
        assert abs(sentiment_dist["negative"] - 33.33) < 0.1  # 2 out of 6 (rounded)

        # Verify top topics
        assert "food_quality" in dashboard_data.top_topics
        assert "service" in dashboard_data.top_topics

        # Verify data freshness
        assert dashboard_data.last_updated is not None
        time_diff = datetime.utcnow() - dashboard_data.last_updated
        assert time_diff.total_seconds() < 60  # Should be very recent

    @pytest.mark.asyncio
    async def test_trend_analysis_integration(
        self, business_with_reviews, analytics_service
    ):
        """Test trend analysis with real database data."""
        # Arrange
        business = business_with_reviews["business"]

        # Act
        trend_analysis = await analytics_service.get_trend_analysis(business.id, days=7)

        # Assert
        assert trend_analysis.period_start is not None
        assert trend_analysis.period_end is not None
        assert (trend_analysis.period_end - trend_analysis.period_start).days == 7

        assert trend_analysis.sentiment_trend in ["improving", "declining", "stable"]
        assert trend_analysis.rating_trend in ["improving", "declining", "stable"]
        assert trend_analysis.review_volume_trend in ["increasing", "decreasing", "stable"]
        assert len(trend_analysis.key_insights) > 0

    @pytest.mark.asyncio
    async def test_business_score_calculation_integration(
        self, business_with_reviews, analytics_service
    ):
        """Test business score calculation with real data."""
        # Arrange
        business = business_with_reviews["business"]

        # Act
        business_score = await analytics_service.get_business_score(business.id)

        # Assert
        assert "overall_score" in business_score
        assert "rating_score" in business_score
        assert "sentiment_score" in business_score
        assert "volume_score" in business_score
        assert "grade" in business_score
        assert "recommendations" in business_score

        # Verify score ranges
        assert 0 <= business_score["overall_score"] <= 100
        assert business_score["grade"] in ["A", "B", "C", "D", "F"]
        assert len(business_score["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_cache_behavior_integration(
        self, business_with_reviews, analytics_service
    ):
        """Test cache behavior with real database operations."""
        # Arrange
        business = business_with_reviews["business"]

        # Act - First call should calculate and cache
        start_time = datetime.utcnow()
        dashboard_data_1 = await analytics_service.get_dashboard_data(business.id)
        first_call_time = (datetime.utcnow() - start_time).total_seconds()

        # Act - Second call should use cache (should be faster)
        start_time = datetime.utcnow()
        dashboard_data_2 = await analytics_service.get_dashboard_data(business.id)
        second_call_time = (datetime.utcnow() - start_time).total_seconds()

        # Assert
        assert dashboard_data_1.business_id == dashboard_data_2.business_id
        assert dashboard_data_1.total_reviews == dashboard_data_2.total_reviews
        assert dashboard_data_1.avg_rating == dashboard_data_2.avg_rating

        # Second call should be significantly faster (cached)
        assert second_call_time < first_call_time * 0.5

        # Verify cache statistics
        cache_stats = await analytics_service.get_cache_stats()
        assert cache_stats["total_entries"] >= 1
        assert cache_stats["active_entries"] >= 1

    @pytest.mark.asyncio
    async def test_cache_invalidation_integration(
        self, business_with_reviews, analytics_service, test_db_session
    ):
        """Test cache invalidation when business data changes."""
        # Arrange
        business = business_with_reviews["business"]

        # Get initial dashboard data (cached)
        dashboard_data_1 = await analytics_service.get_dashboard_data(business.id)
        assert dashboard_data_1.total_reviews == 6

        # Add a new review
        new_review = Review(
            business_id=business.id,
            author_name="New Customer",
            rating=5,
            text="Great new experience!",
            language="en",
            published_at=datetime.utcnow(),
            source="google",
            external_id="new-integration-review",
        )
        test_db_session.add(new_review)
        await test_db_session.commit()

        # Update analytics (should invalidate cache)
        await analytics_service.update_business_analytics(business.id)

        # Act - Get dashboard data again
        dashboard_data_2 = await analytics_service.get_dashboard_data(business.id)

        # Assert
        assert dashboard_data_2.total_reviews == 7  # Should include new review
        assert dashboard_data_2.avg_rating != dashboard_data_1.avg_rating  # Should be recalculated

    @pytest.mark.asyncio
    async def test_multi_business_dashboard_integration(
        self, test_db_session, test_organization, analytics_service
    ):
        """Test multi-business dashboard with real database data."""
        # Arrange - Create multiple businesses with reviews
        businesses = []
        for i in range(3):
            business = Business(
                name=f"Multi Test Restaurant {i}",
                google_place_id=f"multi-test-place-{i}",
                category="restaurant",
                address=f"123 Multi Test Street {i}",
                organization_id=test_organization.id,
                avg_rating=4.0 + i * 0.2,
                total_reviews=10 + i * 5,
            )
            test_db_session.add(business)
            businesses.append(business)

        await test_db_session.commit()

        # Refresh to get IDs
        for business in businesses:
            await test_db_session.refresh(business)

        # Create reviews for each business
        for business in businesses:
            review = Review(
                business_id=business.id,
                author_name="Multi Customer",
                rating=4,
                text="Good experience",
                language="en",
                published_at=datetime.utcnow(),
                source="google",
                external_id=f"multi-review-{business.id}",
            )
            test_db_session.add(review)

        await test_db_session.commit()

        # Act
        business_ids = [business.id for business in businesses]
        multi_dashboard = await analytics_service.get_multi_business_dashboard(business_ids)

        # Assert
        assert len(multi_dashboard) == 3
        for business_id in business_ids:
            assert str(business_id) in multi_dashboard
            dashboard_data = multi_dashboard[str(business_id)]
            assert dashboard_data.total_reviews >= 1  # At least our test review

    @pytest.mark.asyncio
    async def test_consolidated_metrics_integration(
        self, test_db_session, test_organization, analytics_service
    ):
        """Test consolidated metrics calculation with real data."""
        # Arrange - Create businesses with different performance
        business_data = [
            {"name": "Excellent Restaurant", "avg_rating": 4.8, "total_reviews": 100},
            {"name": "Good Restaurant", "avg_rating": 4.2, "total_reviews": 50},
            {"name": "Average Restaurant", "avg_rating": 3.5, "total_reviews": 25},
        ]

        businesses = []
        for data in business_data:
            business = Business(
                name=data["name"],
                google_place_id=f"consolidated-{data['name'].lower().replace(' ', '-')}",
                category="restaurant",
                address=f"123 {data['name']} Street",
                organization_id=test_organization.id,
                avg_rating=data["avg_rating"],
                total_reviews=data["total_reviews"],
            )
            test_db_session.add(business)
            businesses.append(business)

        await test_db_session.commit()

        # Act
        business_ids = [business.id for business in businesses]
        consolidated_metrics = await analytics_service.get_consolidated_metrics(business_ids)

        # Assert
        assert consolidated_metrics["total_businesses"] == 3
        assert consolidated_metrics["total_reviews"] >= 0
        assert 0 <= consolidated_metrics["avg_rating"] <= 5
        assert "overall_sentiment" in consolidated_metrics
        assert "top_topics" in consolidated_metrics

    @pytest.mark.asyncio
    async def test_scheduled_cache_refresh_integration(
        self, business_with_reviews, analytics_service, repositories
    ):
        """Test scheduled cache refresh with real database operations."""
        # Arrange
        business = business_with_reviews["business"]

        # Populate cache first
        await analytics_service.get_dashboard_data(business.id)
        initial_cache_stats = await analytics_service.get_cache_stats()

        # Act
        await analytics_service.schedule_cache_refresh()

        # Assert
        final_cache_stats = await analytics_service.get_cache_stats()
        assert final_cache_stats["active_entries"] >= initial_cache_stats["active_entries"]

    @pytest.mark.asyncio
    async def test_analytics_with_no_data_integration(
        self, test_business, analytics_service
    ):
        """Test analytics service behavior with business that has no reviews."""
        # Act
        dashboard_data = await analytics_service.get_dashboard_data(test_business.id)

        # Assert
        assert dashboard_data.business_id == str(test_business.id)
        assert dashboard_data.total_reviews == 0
        assert dashboard_data.avg_rating == Decimal("0.0")
        assert len(dashboard_data.sentiment_distribution) == 0
        assert len(dashboard_data.top_topics) == 0

        # Trend analysis should still work
        trend_analysis = await analytics_service.get_trend_analysis(test_business.id)
        assert "Insufficient data" in trend_analysis.key_insights[0]

    @pytest.mark.asyncio
    async def test_concurrent_analytics_requests_integration(
        self, business_with_reviews, analytics_service
    ):
        """Test concurrent analytics requests don't cause data corruption."""
        # Arrange
        business = business_with_reviews["business"]

        # Act - Make concurrent requests
        import asyncio
        tasks = [
            analytics_service.get_dashboard_data(business.id),
            analytics_service.get_trend_analysis(business.id),
            analytics_service.get_business_score(business.id),
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        dashboard_data, trend_analysis, business_score = results

        # All requests should succeed
        assert dashboard_data.business_id == str(business.id)
        assert trend_analysis.period_start is not None
        assert business_score["overall_score"] >= 0

        # Cache should be populated
        cache_stats = await analytics_service.get_cache_stats()
        assert cache_stats["active_entries"] >= 3

    @pytest.mark.asyncio
    async def test_analytics_update_integration(
        self, business_with_reviews, analytics_service, repositories
    ):
        """Test complete analytics update process."""
        # Arrange
        business = business_with_reviews["business"]

        # Get initial business stats
        initial_business = await repositories["business"].get_by_id(business.id)
        initial_avg_rating = initial_business.avg_rating
        initial_total_reviews = initial_business.total_reviews

        # Act
        await analytics_service.update_business_analytics(business.id)

        # Assert
        updated_business = await repositories["business"].get_by_id(business.id)
        
        # Business stats should be updated
        assert updated_business.avg_rating != initial_avg_rating
        assert updated_business.total_reviews != initial_total_reviews
        assert updated_business.total_reviews == 6  # Our test reviews

        # Expected average: (5+5+4+3+2+1)/6 = 3.33
        expected_avg = 20.0 / 6
        assert abs(float(updated_business.avg_rating) - expected_avg) < 0.01

    @pytest.mark.asyncio
    async def test_cache_expiration_integration(
        self, business_with_reviews, analytics_service
    ):
        """Test cache expiration behavior in integration environment."""
        # Arrange
        business = business_with_reviews["business"]

        # Create analytics service with very short cache TTL
        short_cache_service = AnalyticsService(
            review_repository=analytics_service._review_repo,
            classification_repository=analytics_service._classification_repo,
            business_repository=analytics_service._business_repo,
            cache_ttl_hours=0.001,  # ~3.6 seconds
        )

        # Act
        # Get data (should be cached)
        dashboard_data_1 = await short_cache_service.get_dashboard_data(business.id)
        
        # Wait for cache to expire
        import asyncio
        await asyncio.sleep(4)
        
        # Get data again (should recalculate)
        dashboard_data_2 = await short_cache_service.get_dashboard_data(business.id)

        # Assert
        # Data should be the same (same underlying data)
        assert dashboard_data_1.total_reviews == dashboard_data_2.total_reviews
        
        # But timestamps should be different (indicating recalculation)
        assert dashboard_data_2.last_updated > dashboard_data_1.last_updated

    @pytest.mark.asyncio
    async def test_error_handling_integration(
        self, business_with_reviews, test_db_session
    ):
        """Test error handling in analytics service with database issues."""
        # Arrange
        from backend.db.repositories.review import ReviewRepository
        from backend.db.repositories.classification import ClassificationRepository
        from backend.db.repositories.business import BusinessRepository
        
        # Create analytics service with closed session (will cause errors)
        await test_db_session.close()
        
        closed_repositories = {
            "review": ReviewRepository(test_db_session),
            "classification": ClassificationRepository(test_db_session),
            "business": BusinessRepository(test_db_session),
        }
        
        error_analytics_service = AnalyticsService(
            review_repository=closed_repositories["review"],
            classification_repository=closed_repositories["classification"],
            business_repository=closed_repositories["business"],
        )

        business = business_with_reviews["business"]

        # Act & Assert
        # Should handle database errors gracefully
        dashboard_data = await error_analytics_service.get_dashboard_data(business.id)
        
        # Should return empty/default data instead of crashing
        assert dashboard_data.business_id == str(business.id)
        assert dashboard_data.total_reviews == 0
        assert dashboard_data.avg_rating == Decimal("0.0")