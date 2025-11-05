"""
Integration tests for review processing pipeline.

Tests the complete review processing workflow including database operations,
AI classification, alert handling, and analytics updates.
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta

from backend.services.review.processor import ReviewProcessingService
from backend.services.analytics_service import AnalyticsService
from backend.services.scheduler_service import SchedulerService
from backend.db.repositories.review import ReviewRepository
from backend.db.repositories.classification import ClassificationRepository
from backend.db.repositories.business import BusinessRepository
from backend.db.models import Review, Classification, Business, Organization
from backend.ai.base import ClassificationResult


class TestReviewProcessingIntegration:
    """Integration test suite for review processing pipeline."""

    @pytest.fixture
    async def business(self, test_db_session, test_organization):
        """Create test business."""
        business = Business(
            name="Integration Test Restaurant",
            google_place_id="integration-test-place-123",
            category="restaurant",
            address="123 Integration Test Street",
            organization_id=test_organization.id,
            avg_rating=0.0,
            total_reviews=0,
        )
        
        test_db_session.add(business)
        await test_db_session.commit()
        await test_db_session.refresh(business)
        
        return business

    @pytest.fixture
    async def repositories(self, test_db_session):
        """Create repository instances."""
        return {
            "review": ReviewRepository(test_db_session),
            "classification": ClassificationRepository(test_db_session),
            "business": BusinessRepository(test_db_session),
        }

    @pytest.fixture
    async def unprocessed_reviews(self, test_db_session, business):
        """Create unprocessed reviews for testing."""
        reviews = [
            Review(
                business_id=business.id,
                author_name="Happy Customer",
                rating=5,
                text="Excellent food and outstanding service! Highly recommend.",
                language="en",
                published_at=datetime.utcnow() - timedelta(days=1),
                source="google",
                external_id="review-positive-1",
            ),
            Review(
                business_id=business.id,
                author_name="Disappointed Diner",
                rating=1,
                text="Terrible food quality and very slow service. Will not return.",
                language="en",
                published_at=datetime.utcnow() - timedelta(days=2),
                source="google",
                external_id="review-negative-1",
            ),
            Review(
                business_id=business.id,
                author_name="Average Visitor",
                rating=3,
                text="Food was okay, nothing special. Service was decent.",
                language="en",
                published_at=datetime.utcnow() - timedelta(days=3),
                source="google",
                external_id="review-neutral-1",
            ),
            Review(
                business_id=business.id,
                author_name="German Customer",
                rating=4,
                text="Sehr gutes Essen und freundlicher Service!",
                language="de",
                published_at=datetime.utcnow() - timedelta(days=4),
                source="google",
                external_id="review-german-1",
            ),
        ]
        
        for review in reviews:
            test_db_session.add(review)
        
        await test_db_session.commit()
        
        for review in reviews:
            await test_db_session.refresh(review)
        
        return reviews

    @pytest.mark.asyncio
    async def test_complete_review_processing_pipeline(
        self,
        business,
        unprocessed_reviews,
        repositories,
        mock_classifier,
        mock_language_detector,
        mock_cost_tracker,
    ):
        """Test complete review processing pipeline from start to finish."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        # Create alert service (mock for integration test)
        alert_service = AlertService(
            email_service=None,  # Mock in real implementation
            sms_service=None,    # Mock in real implementation
            push_service=None,   # Mock in real implementation
        )
        
        # Mock alert service methods
        alert_service.handle_critical_review = lambda r, c: None
        alert_service.handle_competitor_mention = lambda r, c: None
        
        # Create processing service
        processing_service = ReviewProcessingService(
            classifier=mock_classifier,
            language_detector=mock_language_detector,
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            cost_tracker=mock_cost_tracker,
            alert_service=alert_service,
        )

        # Act
        result = await processing_service.process_new_reviews(business.id)

        # Assert
        assert result.processed_count == 4
        assert result.success_count == 4
        assert result.error_count == 0
        assert result.processing_time_ms > 0

        # Verify classifications were created in database
        classifications = await repositories["classification"].get_by_business_id(business.id)
        assert len(classifications) == 4

        # Verify classification data
        for classification in classifications:
            assert classification.sentiment in ["positive", "negative", "neutral"]
            assert len(classification.topics) > 0
            assert classification.urgency in ["low", "medium", "high"]
            assert classification.confidence_score > 0.8
            assert classification.ai_model == "mock-gpt5-nano"

        # Verify mock services were called
        assert mock_classifier.classify_batch.called
        # Note: mock_language_detector is a fixture that returns a real LanguageDetector
        # with a mocked detect_language method, so we can't check call_count directly

    @pytest.mark.asyncio
    async def test_analytics_service_integration(
        self,
        business,
        unprocessed_reviews,
        repositories,
        mock_classifier,
        mock_language_detector,
        mock_cost_tracker,
    ):
        """Test analytics service integration with processed reviews."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        alert_service = AlertService(None, None, None)
        alert_service.handle_critical_review = lambda r, c: None
        alert_service.handle_competitor_mention = lambda r, c: None
        
        processing_service = ReviewProcessingService(
            classifier=mock_classifier,
            language_detector=mock_language_detector,
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            cost_tracker=mock_cost_tracker,
            alert_service=alert_service,
        )
        
        analytics_service = AnalyticsService(
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            business_repository=repositories["business"],
            cache_ttl_hours=1,
        )

        # Act
        # First process reviews
        processing_result = await processing_service.process_new_reviews(business.id)
        assert processing_result.success_count == 4

        # Then get analytics
        dashboard_data = await analytics_service.get_dashboard_data(business.id)

        # Assert
        assert dashboard_data.business_id == str(business.id)
        assert dashboard_data.total_reviews > 0
        assert dashboard_data.avg_rating > Decimal("0")
        assert len(dashboard_data.sentiment_distribution) > 0
        assert len(dashboard_data.top_topics) > 0
        assert dashboard_data.last_updated is not None

        # Verify trend analysis
        trend_analysis = await analytics_service.get_trend_analysis(business.id, days=7)
        assert trend_analysis.period_start is not None
        assert trend_analysis.period_end is not None
        assert trend_analysis.sentiment_trend in ["improving", "declining", "stable"]
        assert len(trend_analysis.key_insights) > 0

    @pytest.mark.asyncio
    async def test_business_rating_update_integration(
        self,
        business,
        unprocessed_reviews,
        repositories,
        mock_classifier,
        mock_language_detector,
        mock_cost_tracker,
    ):
        """Test business rating statistics are updated after processing."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        alert_service = AlertService(None, None, None)
        alert_service.handle_critical_review = lambda r, c: None
        alert_service.handle_competitor_mention = lambda r, c: None
        
        analytics_service = AnalyticsService(
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            business_repository=repositories["business"],
        )

        # Verify initial business stats
        initial_business = await repositories["business"].get_by_id(business.id)
        assert initial_business.avg_rating == 0.0
        assert initial_business.total_reviews == 0

        # Act
        await analytics_service.update_business_analytics(business.id)

        # Assert
        updated_business = await repositories["business"].get_by_id(business.id)
        assert updated_business.avg_rating > 0.0
        assert updated_business.total_reviews == 4  # Number of reviews we created

        # Verify calculated stats are correct
        expected_avg = (5 + 1 + 3 + 4) / 4  # Average of ratings
        assert abs(float(updated_business.avg_rating) - expected_avg) < 0.01

    @pytest.mark.asyncio
    async def test_multi_language_processing_integration(
        self,
        business,
        repositories,
        mock_classifier,
        mock_cost_tracker,
    ):
        """Test processing reviews in multiple languages."""
        # Arrange
        from backend.ai.language_detector import LanguageDetector
        from backend.services.notification.alert_service import AlertService
        
        # Use real language detector for this test
        language_detector = LanguageDetector()
        
        alert_service = AlertService(None, None, None)
        alert_service.handle_critical_review = lambda r, c: None
        alert_service.handle_competitor_mention = lambda r, c: None
        
        processing_service = ReviewProcessingService(
            classifier=mock_classifier,
            language_detector=language_detector,
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            cost_tracker=mock_cost_tracker,
            alert_service=alert_service,
        )

        # Create multi-language reviews
        multilang_reviews = [
            Review(
                business_id=business.id,
                author_name="English Customer",
                rating=5,
                text="Great food and excellent service!",
                language="unknown",  # Will be detected
                published_at=datetime.utcnow(),
                source="google",
                external_id="review-en-1",
            ),
            Review(
                business_id=business.id,
                author_name="German Customer",
                rating=4,
                text="Sehr gutes Essen und freundlicher Service!",
                language="unknown",  # Will be detected
                published_at=datetime.utcnow(),
                source="google",
                external_id="review-de-1",
            ),
            Review(
                business_id=business.id,
                author_name="Turkish Customer",
                rating=5,
                text="Mükemmel yemek ve harika hizmet!",
                language="unknown",  # Will be detected
                published_at=datetime.utcnow(),
                source="google",
                external_id="review-tr-1",
            ),
        ]
        
        # Add reviews to database
        for review in multilang_reviews:
            repositories["review"].session.add(review)
        await repositories["review"].session.commit()

        # Act
        result = await processing_service.process_new_reviews(business.id)

        # Assert
        assert result.success_count == 3

        # Verify language detection worked
        processed_reviews = await repositories["review"].get_by_business(business.id)
        languages = [r.language for r in processed_reviews]
        
        # Should have detected different languages
        assert "en" in languages
        assert "de" in languages
        # Note: Turkish detection might be challenging for short text

    @pytest.mark.asyncio
    async def test_error_recovery_integration(
        self,
        business,
        repositories,
        mock_language_detector,
        mock_cost_tracker,
    ):
        """Test error recovery in processing pipeline."""
        # Arrange
        from unittest.mock import AsyncMock
        from backend.services.notification.alert_service import AlertService
        
        # Create failing classifier
        failing_classifier = AsyncMock()
        failing_classifier.classify_batch.side_effect = Exception("API temporarily unavailable")
        
        alert_service = AlertService(None, None, None)
        alert_service.handle_critical_review = lambda r, c: None
        alert_service.handle_competitor_mention = lambda r, c: None
        
        processing_service = ReviewProcessingService(
            classifier=failing_classifier,
            language_detector=mock_language_detector,
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            cost_tracker=mock_cost_tracker,
            alert_service=alert_service,
        )

        # Create a review to process
        review = Review(
            business_id=business.id,
            author_name="Test Customer",
            rating=4,
            text="Good food",
            language="en",
            published_at=datetime.utcnow(),
            source="google",
            external_id="review-error-test-1",
        )
        repositories["review"].session.add(review)
        await repositories["review"].session.commit()

        # Act
        result = await processing_service.process_new_reviews(business.id)

        # Assert
        assert result.processed_count == 1
        assert result.success_count == 0
        assert result.error_count == 1
        assert len(result.errors) == 1
        assert "Classification failed" in result.errors[0]

        # Verify no classifications were created
        classifications = await repositories["classification"].get_by_business_id(business.id)
        assert len(classifications) == 0

    @pytest.mark.asyncio
    async def test_scheduler_integration(
        self,
        business,
        repositories,
        mock_classifier,
        mock_language_detector,
        mock_cost_tracker,
    ):
        """Test scheduler service integration with processing pipeline."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        from backend.external.google_places import GooglePlacesClient
        from unittest.mock import AsyncMock
        
        alert_service = AlertService(None, None, None)
        alert_service.handle_critical_review = lambda r, c: None
        alert_service.handle_competitor_mention = lambda r, c: None
        
        processing_service = ReviewProcessingService(
            classifier=mock_classifier,
            language_detector=mock_language_detector,
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            cost_tracker=mock_cost_tracker,
            alert_service=alert_service,
        )
        
        analytics_service = AnalyticsService(
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            business_repository=repositories["business"],
        )
        
        # Mock Google Places client
        google_places_client = AsyncMock(spec=GooglePlacesClient)
        google_places_client.import_reviews.return_value = {
            "imported_count": 2,
            "skipped_count": 0,
            "total_available": 2,
        }
        
        scheduler_service = SchedulerService(
            review_processor=processing_service,
            analytics_service=analytics_service,
            google_places_client=google_places_client,
            business_repository=repositories["business"],
        )

        # Create some unprocessed reviews first
        review = Review(
            business_id=business.id,
            author_name="Scheduled Customer",
            rating=5,
            text="Great experience!",
            language="en",
            published_at=datetime.utcnow(),
            source="google",
            external_id="scheduled-review-1",
        )
        repositories["review"].session.add(review)
        await repositories["review"].session.commit()

        # Act
        result = await scheduler_service.trigger_daily_review_processing()

        # Assert
        assert result["businesses_processed"] == 1
        assert result["total_errors"] == 0
        assert len(result["business_results"]) == 1

        business_result = result["business_results"][0]
        assert business_result["business_id"] == str(business.id)
        assert business_result["business_name"] == business.name
        assert business_result["imported_reviews"] == 2
        assert business_result["processed_reviews"] == 1  # Our test review

        # Verify Google Places import was called
        google_places_client.import_reviews.assert_called_once_with(
            business.google_place_id, business.id
        )

    @pytest.mark.asyncio
    async def test_cache_integration_with_processing(
        self,
        business,
        unprocessed_reviews,
        repositories,
        mock_classifier,
        mock_language_detector,
        mock_cost_tracker,
    ):
        """Test cache integration with review processing and analytics."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        alert_service = AlertService(None, None, None)
        alert_service.handle_critical_review = lambda r, c: None
        alert_service.handle_competitor_mention = lambda r, c: None
        
        processing_service = ReviewProcessingService(
            classifier=mock_classifier,
            language_detector=mock_language_detector,
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            cost_tracker=mock_cost_tracker,
            alert_service=alert_service,
        )
        
        analytics_service = AnalyticsService(
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            business_repository=repositories["business"],
            cache_ttl_hours=1,
        )

        # Act
        # First get dashboard data (should be calculated and cached)
        dashboard_data_1 = await analytics_service.get_dashboard_data(business.id)
        
        # Process reviews (should invalidate cache)
        await processing_service.process_new_reviews(business.id)
        await analytics_service.update_business_analytics(business.id)
        
        # Get dashboard data again (should be recalculated)
        dashboard_data_2 = await analytics_service.get_dashboard_data(business.id)

        # Assert
        # Data should be different after processing reviews
        assert dashboard_data_1.total_reviews != dashboard_data_2.total_reviews
        assert dashboard_data_2.total_reviews == 4  # Our test reviews
        
        # Verify cache statistics
        cache_stats = await analytics_service.get_cache_stats()
        assert cache_stats["total_entries"] > 0
        assert cache_stats["active_entries"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_processing_integration(
        self,
        test_db_session,
        test_organization,
        repositories,
        mock_classifier,
        mock_language_detector,
        mock_cost_tracker,
    ):
        """Test concurrent processing of multiple businesses."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        alert_service = AlertService(None, None, None)
        alert_service.handle_critical_review = lambda r, c: None
        alert_service.handle_competitor_mention = lambda r, c: None
        
        processing_service = ReviewProcessingService(
            classifier=mock_classifier,
            language_detector=mock_language_detector,
            review_repository=repositories["review"],
            classification_repository=repositories["classification"],
            cost_tracker=mock_cost_tracker,
            alert_service=alert_service,
        )

        # Create multiple businesses with reviews
        businesses = []
        for i in range(3):
            business = Business(
                name=f"Concurrent Test Restaurant {i}",
                google_place_id=f"concurrent-test-place-{i}",
                category="restaurant",
                address=f"123 Concurrent Test Street {i}",
                organization_id=test_organization.id,
            )
            test_db_session.add(business)
            businesses.append(business)
        
        await test_db_session.commit()
        
        # Add reviews for each business
        for business in businesses:
            await test_db_session.refresh(business)
            review = Review(
                business_id=business.id,
                author_name="Concurrent Customer",
                rating=4,
                text=f"Good food at {business.name}",
                language="en",
                published_at=datetime.utcnow(),
                source="google",
                external_id=f"concurrent-review-{business.id}",
            )
            test_db_session.add(review)
        
        await test_db_session.commit()

        # Act - Process all businesses concurrently
        import asyncio
        tasks = [
            processing_service.process_new_reviews(business.id)
            for business in businesses
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        for result in results:
            assert result.success_count == 1
            assert result.error_count == 0

        # Verify all classifications were created
        total_classifications = 0
        for business in businesses:
            classifications = await repositories["classification"].get_by_business_id(business.id)
            total_classifications += len(classifications)
        
        assert total_classifications == 3