"""
Unit tests for AI service base protocols and data classes.

Tests the abstract base classes, protocols, and data structures
used by AI services for type safety and interface compliance.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from typing import List

from backend.ai.base import (
    ClassificationResult,
    ReviewText,
    BusinessContext,
    AdvisorResponse,
    WeeklyReport,
    ReviewClassifierProtocol,
    BusinessAdvisorProtocol,
    CostTracker,
)


class TestClassificationResult:
    """Test suite for ClassificationResult data class."""

    def test_classification_result_creation(self):
        """Test creating ClassificationResult with all fields."""
        # Arrange & Act
        result = ClassificationResult(
            sentiment="positive",
            topics=["food_quality", "service"],
            urgency="medium",
            competitor_mentioned=True,
            confidence_score=0.95,
            processing_time_ms=250,
            ai_model="gpt-4o-mini"
        )
        
        # Assert
        assert result.sentiment == "positive"
        assert result.topics == ["food_quality", "service"]
        assert result.urgency == "medium"
        assert result.competitor_mentioned is True
        assert result.confidence_score == 0.95
        assert result.processing_time_ms == 250
        assert result.ai_model == "gpt-4o-mini"

    def test_classification_result_equality(self):
        """Test ClassificationResult equality comparison."""
        # Arrange
        result1 = ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.90,
            processing_time_ms=200,
            ai_model="gpt-4o-mini"
        )
        
        result2 = ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.90,
            processing_time_ms=200,
            ai_model="gpt-4o-mini"
        )
        
        # Act & Assert
        assert result1 == result2

    def test_classification_result_different_values(self):
        """Test ClassificationResult with different values."""
        # Arrange
        result1 = ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.90,
            processing_time_ms=200,
            ai_model="gpt-4o-mini"
        )
        
        result2 = ClassificationResult(
            sentiment="negative",
            topics=["service"],
            urgency="high",
            competitor_mentioned=True,
            confidence_score=0.85,
            processing_time_ms=300,
            ai_model="gpt-4o-mini"
        )
        
        # Act & Assert
        assert result1 != result2


class TestReviewText:
    """Test suite for ReviewText data class."""

    def test_review_text_creation(self):
        """Test creating ReviewText with all fields."""
        # Arrange & Act
        review = ReviewText(
            id="review-123",
            text="Great food and excellent service!",
            language="en",
            business_id="business-456"
        )
        
        # Assert
        assert review.id == "review-123"
        assert review.text == "Great food and excellent service!"
        assert review.language == "en"
        assert review.business_id == "business-456"


class TestBusinessContext:
    """Test suite for BusinessContext data class."""

    def test_business_context_creation(self):
        """Test creating BusinessContext with all fields."""
        # Arrange & Act
        context = BusinessContext(
            business_id="business-123",
            business_name="Test Restaurant",
            avg_rating=4.2,
            total_reviews=150,
            recent_sentiment_trend="improving",
            top_topics=["food_quality", "service", "ambiance"],
            competitor_mentions=3
        )
        
        # Assert
        assert context.business_id == "business-123"
        assert context.business_name == "Test Restaurant"
        assert context.avg_rating == 4.2
        assert context.total_reviews == 150
        assert context.recent_sentiment_trend == "improving"
        assert context.top_topics == ["food_quality", "service", "ambiance"]
        assert context.competitor_mentions == 3


class TestAdvisorResponse:
    """Test suite for AdvisorResponse data class."""

    def test_advisor_response_creation(self):
        """Test creating AdvisorResponse with all fields."""
        # Arrange & Act
        response = AdvisorResponse(
            message="Based on your reviews, I recommend focusing on service speed.",
            language="en",
            confidence_score=0.92,
            processing_time_ms=500,
            ai_model="claude-3-haiku",
            cost_usd=Decimal("0.002")
        )
        
        # Assert
        assert response.message == "Based on your reviews, I recommend focusing on service speed."
        assert response.language == "en"
        assert response.confidence_score == 0.92
        assert response.processing_time_ms == 500
        assert response.ai_model == "claude-3-haiku"
        assert response.cost_usd == Decimal("0.002")


class TestWeeklyReport:
    """Test suite for WeeklyReport data class."""

    def test_weekly_report_creation(self):
        """Test creating WeeklyReport with all fields."""
        # Arrange
        start_date = datetime(2024, 1, 1, 0, 0, 0)
        end_date = datetime(2024, 1, 7, 23, 59, 59)
        
        # Act
        report = WeeklyReport(
            business_id="business-123",
            report_period_start=start_date,
            report_period_end=end_date,
            summary="Your restaurant performed well this week.",
            action_items=["Improve service speed", "Address cleanliness concerns"],
            sentiment_analysis="Overall positive trend with 75% positive reviews",
            top_themes=["food_quality", "service"],
            competitor_mentions=2,
            language="en",
            ai_model="claude-3-haiku"
        )
        
        # Assert
        assert report.business_id == "business-123"
        assert report.report_period_start == start_date
        assert report.report_period_end == end_date
        assert report.summary == "Your restaurant performed well this week."
        assert len(report.action_items) == 2
        assert "Improve service speed" in report.action_items
        assert report.sentiment_analysis == "Overall positive trend with 75% positive reviews"
        assert report.top_themes == ["food_quality", "service"]
        assert report.competitor_mentions == 2
        assert report.language == "en"
        assert report.ai_model == "claude-3-haiku"


class MockReviewClassifier:
    """Mock implementation of ReviewClassifierProtocol for testing."""

    async def classify_review(self, text: str, language: str = "en") -> ClassificationResult:
        """Mock classify_review implementation."""
        return ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.90,
            processing_time_ms=200,
            ai_model="mock-classifier"
        )

    async def classify_batch(self, reviews: List[ReviewText]) -> List[ClassificationResult]:
        """Mock classify_batch implementation."""
        results = []
        for review in reviews:
            result = await self.classify_review(review.text, review.language)
            results.append(result)
        return results


class MockBusinessAdvisor:
    """Mock implementation of BusinessAdvisorProtocol for testing."""

    async def generate_response(
        self, message: str, context: BusinessContext, language: str = "en"
    ) -> AdvisorResponse:
        """Mock generate_response implementation."""
        return AdvisorResponse(
            message=f"Mock response to: {message}",
            language=language,
            confidence_score=0.85,
            processing_time_ms=300,
            ai_model="mock-advisor",
            cost_usd=Decimal("0.001")
        )

    async def generate_report(
        self, business_data: BusinessContext, language: str = "en"
    ) -> WeeklyReport:
        """Mock generate_report implementation."""
        return WeeklyReport(
            business_id=business_data.business_id,
            report_period_start=datetime.now(),
            report_period_end=datetime.now(),
            summary="Mock weekly report",
            action_items=["Mock action item"],
            sentiment_analysis="Mock sentiment analysis",
            top_themes=business_data.top_topics,
            competitor_mentions=business_data.competitor_mentions,
            language=language,
            ai_model="mock-advisor"
        )


class MockCostTracker(CostTracker):
    """Mock implementation of CostTracker for testing."""

    def __init__(self):
        self.logged_usage = []
        self.monthly_costs = {}
        self.cost_limits = {}

    async def log_usage(
        self,
        business_id: str,
        ai_service: str,
        operation: str,
        tokens_used: int,
        cost_usd: Decimal,
        processing_time_ms: int,
    ) -> None:
        """Mock log_usage implementation."""
        self.logged_usage.append({
            "business_id": business_id,
            "ai_service": ai_service,
            "operation": operation,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "processing_time_ms": processing_time_ms,
        })

    async def get_monthly_cost(self, business_id: str) -> Decimal:
        """Mock get_monthly_cost implementation."""
        return self.monthly_costs.get(business_id, Decimal("0.00"))

    async def check_cost_limit(self, business_id: str) -> bool:
        """Mock check_cost_limit implementation."""
        current_cost = await self.get_monthly_cost(business_id)
        limit = self.cost_limits.get(business_id, Decimal("100.00"))
        return current_cost <= limit


class TestProtocolImplementations:
    """Test suite for protocol implementations."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_review_classifier_protocol_compliance(self):
        """Test that mock classifier implements the protocol correctly."""
        # Arrange
        classifier = MockReviewClassifier()
        review_text = "Great food and service!"
        
        # Act
        result = await classifier.classify_review(review_text)
        
        # Assert
        assert isinstance(result, ClassificationResult)
        assert result.sentiment == "positive"
        assert result.ai_model == "mock-classifier"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_review_classifier_batch_processing(self):
        """Test batch processing in classifier protocol."""
        # Arrange
        classifier = MockReviewClassifier()
        reviews = [
            ReviewText("1", "Great food!", "en", "business-1"),
            ReviewText("2", "Excellent service!", "en", "business-1"),
        ]
        
        # Act
        results = await classifier.classify_batch(reviews)
        
        # Assert
        assert len(results) == 2
        assert all(isinstance(r, ClassificationResult) for r in results)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_business_advisor_protocol_compliance(self):
        """Test that mock advisor implements the protocol correctly."""
        # Arrange
        advisor = MockBusinessAdvisor()
        context = BusinessContext(
            business_id="test-business",
            business_name="Test Restaurant",
            avg_rating=4.0,
            total_reviews=100,
            recent_sentiment_trend="stable",
            top_topics=["food_quality"],
            competitor_mentions=0
        )
        
        # Act
        response = await advisor.generate_response("How is my business doing?", context)
        
        # Assert
        assert isinstance(response, AdvisorResponse)
        assert "Mock response to:" in response.message
        assert response.language == "en"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_business_advisor_report_generation(self):
        """Test report generation in advisor protocol."""
        # Arrange
        advisor = MockBusinessAdvisor()
        context = BusinessContext(
            business_id="test-business",
            business_name="Test Restaurant",
            avg_rating=4.0,
            total_reviews=100,
            recent_sentiment_trend="stable",
            top_topics=["food_quality", "service"],
            competitor_mentions=1
        )
        
        # Act
        report = await advisor.generate_report(context)
        
        # Assert
        assert isinstance(report, WeeklyReport)
        assert report.business_id == "test-business"
        assert report.top_themes == ["food_quality", "service"]
        assert report.competitor_mentions == 1

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_cost_tracker_protocol_compliance(self):
        """Test that mock cost tracker implements the protocol correctly."""
        # Arrange
        tracker = MockCostTracker()
        business_id = "test-business"
        
        # Act
        await tracker.log_usage(
            business_id=business_id,
            ai_service="test-service",
            operation="test-op",
            tokens_used=100,
            cost_usd=Decimal("0.001"),
            processing_time_ms=200
        )
        
        monthly_cost = await tracker.get_monthly_cost(business_id)
        within_limit = await tracker.check_cost_limit(business_id)
        
        # Assert
        assert len(tracker.logged_usage) == 1
        assert tracker.logged_usage[0]["business_id"] == business_id
        assert monthly_cost == Decimal("0.00")  # Default
        assert within_limit is True