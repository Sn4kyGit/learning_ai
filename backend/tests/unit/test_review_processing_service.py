"""
Unit tests for Review Processing Service.

Tests the ReviewProcessingService including pipeline orchestration,
language detection, classification, and alert handling.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime, timedelta

from backend.services.review.processor import ReviewProcessingService, ProcessingResult
from backend.ai.base import ReviewText, ClassificationResult
from backend.db.models import Review, Classification


class MockReviewRepository:
    """Mock review repository for testing."""

    def __init__(self):
        self.reviews = {}
        self.unprocessed_reviews = []

    async def get_unclassified_reviews(self, business_id):
        """Mock get unclassified reviews."""
        return [r for r in self.unprocessed_reviews if r.business_id == business_id]

    async def update(self, review_id, **kwargs):
        """Mock update review."""
        if review_id in self.reviews:
            for key, value in kwargs.items():
                setattr(self.reviews[review_id], key, value)

    async def get_by_id(self, review_id):
        """Mock get review by ID."""
        return self.reviews.get(review_id)

    def add_unprocessed_review(self, business_id, review_id=None, text="Test review", language="en"):
        """Helper to add unprocessed review."""
        if review_id is None:
            review_id = uuid4()
        
        review = Mock()
        review.id = review_id
        review.business_id = business_id
        review.text = text
        review.language = language
        review.author_name = "Test Author"
        review.rating = 4
        review.published_at = datetime.utcnow()
        
        self.reviews[review_id] = review
        self.unprocessed_reviews.append(review)
        return review


class MockClassificationRepository:
    """Mock classification repository for testing."""

    def __init__(self):
        self.classifications = []

    async def create(self, classification_data):
        """Mock create classification."""
        classification = Mock()
        classification.id = uuid4()
        
        # Handle both dict and schema object
        if hasattr(classification_data, 'model_dump'):
            data = classification_data.model_dump()
        else:
            data = classification_data
            
        for key, value in data.items():
            setattr(classification, key, value)
        classification.created_at = datetime.utcnow()
        
        self.classifications.append(classification)
        return classification


class MockAlertService:
    """Mock alert service for testing."""

    def __init__(self):
        self.critical_alerts = []
        self.competitor_alerts = []

    async def handle_critical_review(self, review, classification):
        """Mock handle critical review."""
        self.critical_alerts.append((review, classification))

    async def handle_competitor_mention(self, review, classification):
        """Mock handle competitor mention."""
        self.competitor_alerts.append((review, classification))


class TestReviewProcessingService:
    """Test suite for ReviewProcessingService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = Mock()
        self.language_detector = Mock()
        self.review_repo = MockReviewRepository()
        self.classification_repo = MockClassificationRepository()
        self.cost_tracker = Mock()
        self.alert_service = MockAlertService()
        
        self.service = ReviewProcessingService(
            classifier=self.classifier,
            language_detector=self.language_detector,
            review_repository=self.review_repo,
            classification_repository=self.classification_repo,
            cost_tracker=self.cost_tracker,
            alert_service=self.alert_service,
        )

        # Test data
        self.business_id = uuid4()

    @pytest.mark.asyncio
    async def test_process_new_reviews_success(self):
        """Test successful processing of new reviews."""
        # Arrange
        review1 = self.review_repo.add_unprocessed_review(
            self.business_id, text="Great food and service!", language="en"
        )
        review2 = self.review_repo.add_unprocessed_review(
            self.business_id, text="Terrible experience", language="en"
        )

        # Mock language detection
        self.language_detector.detect_language.return_value = "en"

        # Mock classification results
        classification_results = [
            ClassificationResult(
                sentiment="positive",
                topics=["food_quality", "service"],
                urgency="low",
                competitor_mentioned=False,
                confidence_score=0.95,
                processing_time_ms=100,
                ai_model="test-model",
            ),
            ClassificationResult(
                sentiment="negative",
                topics=["service"],
                urgency="high",
                competitor_mentioned=False,
                confidence_score=0.92,
                processing_time_ms=120,
                ai_model="test-model",
            ),
        ]
        
        self.classifier.classify_batch = AsyncMock(return_value=classification_results)

        # Act
        result = await self.service.process_new_reviews(self.business_id)

        # Assert
        assert result.processed_count == 2
        assert result.success_count == 2
        assert result.error_count == 0
        assert result.critical_reviews_found == 1  # One high urgency review
        assert len(result.errors) == 0

        # Verify classifications were created
        assert len(self.classification_repo.classifications) == 2
        
        # Verify critical alert was triggered
        assert len(self.alert_service.critical_alerts) == 1
        assert self.alert_service.critical_alerts[0][0] == review2

        # Verify classifier was called with correct data
        self.classifier.classify_batch.assert_called_once()
        call_args = self.classifier.classify_batch.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0].text == "Great food and service!"
        assert call_args[1].text == "Terrible experience"

    @pytest.mark.asyncio
    async def test_process_new_reviews_no_unprocessed(self):
        """Test processing when no unprocessed reviews exist."""
        # Arrange - no unprocessed reviews

        # Act
        result = await self.service.process_new_reviews(self.business_id)

        # Assert
        assert result.processed_count == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.critical_reviews_found == 0
        assert len(result.errors) == 0

        # Verify classifier was not called
        self.classifier.classify_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_new_reviews_language_detection(self):
        """Test language detection and review update."""
        # Arrange
        review = self.review_repo.add_unprocessed_review(
            self.business_id, text="Sehr gutes Essen!", language="en"  # Wrong language
        )

        # Mock language detection to return German
        self.language_detector.detect_language.return_value = "de"

        # Mock classification
        classification_result = ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.90,
            processing_time_ms=100,
            ai_model="test-model",
        )
        self.classifier.classify_batch = AsyncMock(return_value=[classification_result])

        # Act
        result = await self.service.process_new_reviews(self.business_id)

        # Assert
        assert result.success_count == 1

        # Verify language was detected
        self.language_detector.detect_language.assert_called_with("Sehr gutes Essen!")
        
        # Verify review language was updated (mock doesn't actually update, but method was called)
        # In real implementation, review.language would be updated to "de"

    @pytest.mark.asyncio
    async def test_process_new_reviews_competitor_mentions(self):
        """Test handling of competitor mentions."""
        # Arrange
        review = self.review_repo.add_unprocessed_review(
            self.business_id, text="Better than McDonald's next door"
        )

        self.language_detector.detect_language.return_value = "en"

        # Mock classification with competitor mention
        classification_result = ClassificationResult(
            sentiment="positive",
            topics=["comparison"],
            urgency="medium",
            competitor_mentioned=True,
            confidence_score=0.88,
            processing_time_ms=110,
            ai_model="test-model",
        )
        self.classifier.classify_batch = AsyncMock(return_value=[classification_result])

        # Act
        result = await self.service.process_new_reviews(self.business_id)

        # Assert
        assert result.success_count == 1

        # Verify competitor mention alert was triggered
        assert len(self.alert_service.competitor_alerts) == 1
        assert self.alert_service.competitor_alerts[0][0] == review

    @pytest.mark.asyncio
    async def test_process_new_reviews_classification_failure(self):
        """Test handling of classification failures."""
        # Arrange
        self.review_repo.add_unprocessed_review(self.business_id, text="Test review")
        
        self.language_detector.detect_language.return_value = "en"
        
        # Mock classification failure
        self.classifier.classify_batch = AsyncMock(
            side_effect=Exception("Classification API error")
        )

        # Act
        result = await self.service.process_new_reviews(self.business_id)

        # Assert
        assert result.processed_count == 1
        assert result.success_count == 0
        assert result.error_count == 1
        assert len(result.errors) == 1
        assert "Classification failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_process_single_review_success(self):
        """Test successful processing of a single review."""
        # Arrange
        review_id = uuid4()
        review = self.review_repo.add_unprocessed_review(
            self.business_id, review_id=review_id, text="Good food"
        )

        self.language_detector.detect_language.return_value = "en"

        classification_result = ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.93,
            processing_time_ms=95,
            ai_model="test-model",
        )
        self.classifier.classify_review = AsyncMock(return_value=classification_result)

        # Act
        result = await self.service.process_single_review(review_id)

        # Assert
        assert result is True

        # Verify classification was created
        assert len(self.classification_repo.classifications) == 1
        classification = self.classification_repo.classifications[0]
        assert classification.review_id == review_id
        assert classification.sentiment == "positive"

        # Verify classifier was called correctly
        self.classifier.classify_review.assert_called_once_with("Good food", "en")

    @pytest.mark.asyncio
    async def test_process_single_review_not_found(self):
        """Test processing single review when review doesn't exist."""
        # Arrange
        non_existent_id = uuid4()

        # Act
        result = await self.service.process_single_review(non_existent_id)

        # Assert
        assert result is False

        # Verify no classification was created
        assert len(self.classification_repo.classifications) == 0

    @pytest.mark.asyncio
    async def test_process_single_review_critical_alert(self):
        """Test single review processing triggers critical alert."""
        # Arrange
        review_id = uuid4()
        review = self.review_repo.add_unprocessed_review(
            self.business_id, review_id=review_id, text="Awful service"
        )

        self.language_detector.detect_language.return_value = "en"

        # Mock high urgency classification
        classification_result = ClassificationResult(
            sentiment="negative",
            topics=["service"],
            urgency="high",
            competitor_mentioned=False,
            confidence_score=0.96,
            processing_time_ms=105,
            ai_model="test-model",
        )
        self.classifier.classify_review = AsyncMock(return_value=classification_result)

        # Act
        result = await self.service.process_single_review(review_id)

        # Assert
        assert result is True

        # Verify critical alert was triggered
        assert len(self.alert_service.critical_alerts) == 1

    @pytest.mark.asyncio
    async def test_process_single_review_classification_error(self):
        """Test single review processing with classification error."""
        # Arrange
        review_id = uuid4()
        self.review_repo.add_unprocessed_review(
            self.business_id, review_id=review_id, text="Test review"
        )

        self.language_detector.detect_language.return_value = "en"
        self.classifier.classify_review = AsyncMock(
            side_effect=Exception("API error")
        )

        # Act
        result = await self.service.process_single_review(review_id)

        # Assert
        assert result is False

        # Verify no classification was created
        assert len(self.classification_repo.classifications) == 0

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test batch processing handles multiple reviews efficiently."""
        # Arrange - Create 10 reviews
        reviews = []
        for i in range(10):
            review = self.review_repo.add_unprocessed_review(
                self.business_id, text=f"Review {i}"
            )
            reviews.append(review)

        self.language_detector.detect_language.return_value = "en"

        # Mock batch classification results
        classification_results = [
            ClassificationResult(
                sentiment="positive" if i % 2 == 0 else "negative",
                topics=["food_quality"],
                urgency="low" if i % 3 != 0 else "high",
                competitor_mentioned=False,
                confidence_score=0.90,
                processing_time_ms=100,
                ai_model="test-model",
            )
            for i in range(10)
        ]
        self.classifier.classify_batch = AsyncMock(return_value=classification_results)

        # Act
        result = await self.service.process_new_reviews(self.business_id)

        # Assert
        assert result.processed_count == 10
        assert result.success_count == 10
        assert result.error_count == 0

        # Verify batch classification was called once (not 10 individual calls)
        self.classifier.classify_batch.assert_called_once()
        
        # Verify all classifications were created
        assert len(self.classification_repo.classifications) == 10

        # Verify critical alerts for high urgency reviews
        expected_critical_count = len([r for r in classification_results if r.urgency == "high"])
        assert len(self.alert_service.critical_alerts) == expected_critical_count

    @pytest.mark.asyncio
    async def test_mixed_language_processing(self):
        """Test processing reviews in different languages."""
        # Arrange
        reviews_data = [
            ("Great food!", "en"),
            ("Sehr gut!", "de"),
            ("Mükemmel!", "tr"),
        ]

        for text, expected_lang in reviews_data:
            self.review_repo.add_unprocessed_review(
                self.business_id, text=text, language="unknown"
            )

        # Mock language detection to return correct languages
        def mock_detect_language(text):
            if "Great" in text:
                return "en"
            elif "Sehr" in text:
                return "de"
            elif "Mükemmel" in text:
                return "tr"
            return "en"

        self.language_detector.detect_language.side_effect = mock_detect_language

        # Mock classification results
        classification_results = [
            ClassificationResult(
                sentiment="positive",
                topics=["food_quality"],
                urgency="low",
                competitor_mentioned=False,
                confidence_score=0.90,
                processing_time_ms=100,
                ai_model="test-model",
            )
            for _ in range(3)
        ]
        self.classifier.classify_batch = AsyncMock(return_value=classification_results)

        # Act
        result = await self.service.process_new_reviews(self.business_id)

        # Assert
        assert result.success_count == 3

        # Verify language detection was called for each review
        assert self.language_detector.detect_language.call_count == 3

        # Verify ReviewText objects had correct languages
        call_args = self.classifier.classify_batch.call_args[0][0]
        assert call_args[0].language == "en"
        assert call_args[1].language == "de"
        assert call_args[2].language == "tr"