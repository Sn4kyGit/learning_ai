"""
Unit tests for Response Management Service.

Tests response template generation, tone analysis, response rate calculation,
and priority queue functionality.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.response_management_service import (
    ResponseManagementService,
    ResponseTemplate,
    ToneAnalysis,
    ResponseMetrics,
    PriorityQueueItem,
    ResponsePriority,
    ResponseTone,
)
from backend.ai.base import (
    BusinessAdvisorProtocol,
    BusinessContext,
    AdvisorResponse,
)
from backend.db.models import Review, Classification, Business


class TestResponseManagementService:
    """Test suite for ResponseManagementService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=AsyncSession)
        self.mock_advisor = Mock(spec=BusinessAdvisorProtocol)
        self.mock_repository = Mock()
        
        self.service = ResponseManagementService(
            db_session=self.mock_db,
            business_advisor=self.mock_advisor,
            repository=self.mock_repository
        )
        
        # Sample test data
        self.test_business_id = "test-business-123"
        self.test_review_id = "test-review-456"
        self.test_user_id = "test-user-789"
        
        self.sample_review = Review(
            id=self.test_review_id,
            business_id=self.test_business_id,
            author_name="John Doe",
            rating=2,
            text="The food was cold and service was slow.",
            language="en",
            published_at=datetime.utcnow() - timedelta(days=1),
            source="google",
            external_id="review-123"
        )
        
        self.sample_classification = Classification(
            id="classification-123",
            review_id=self.test_review_id,
            sentiment="negative",
            topics=["food_quality", "service"],
            urgency="high",
            competitor_mentioned=False,
            confidence_score=0.92,
            ai_model="test-model",
            processing_time_ms=100
        )
        
        self.sample_business = Business(
            id=self.test_business_id,
            name="Test Restaurant",
            google_place_id="place-123",
            category="restaurant",
            address="123 Test St",
            avg_rating=4.2,
            total_reviews=50
        )

    @pytest.mark.asyncio
    async def test_generate_response_template_success(self):
        """Test successful response template generation."""
        # Arrange
        language = "en"
        expected_template_text = "Thank you for your feedback. We apologize for the issues with your meal and service. We are taking immediate steps to improve."
        
        # Mock database queries
        mock_result = Mock()
        mock_result.first.return_value = (self.sample_review, self.sample_classification)
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock business query
        mock_business_result = Mock()
        mock_business_result.scalar_one_or_none.return_value = self.sample_business
        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_business_result])
        
        # Mock advisor response
        mock_advisor_response = AdvisorResponse(
            message=expected_template_text,
            language=language,
            confidence_score=Decimal("0.9"),
            processing_time_ms=200,
            ai_model="claude-haiku",
            cost_usd=Decimal("0.001")
        )
        self.mock_advisor.generate_response = AsyncMock(return_value=mock_advisor_response)
        
        # Act
        result = await self.service.generate_response_template(
            review_id=self.test_review_id,
            business_id=self.test_business_id,
            language=language
        )
        
        # Assert
        assert isinstance(result, ResponseTemplate)
        assert result.template_text == expected_template_text
        assert result.tone == ResponseTone.EMPATHETIC  # Should detect empathetic tone
        assert result.confidence_score == 0.9
        assert result.ai_model == "claude-haiku"
        assert result.processing_time_ms >= 0
        
        # Verify advisor was called with correct prompt
        self.mock_advisor.generate_response.assert_called_once()
        call_args = self.mock_advisor.generate_response.call_args
        assert "cold" in call_args[1]["message"]  # Review text should be in prompt
        assert "slow" in call_args[1]["message"]
        assert call_args[1]["language"] == language

    @pytest.mark.asyncio
    async def test_generate_response_template_with_tone_preference(self):
        """Test response template generation with specific tone preference."""
        # Arrange
        tone_preference = ResponseTone.PROFESSIONAL
        
        # Mock database queries
        mock_result = Mock()
        mock_result.first.return_value = (self.sample_review, self.sample_classification)
        mock_business_result = Mock()
        mock_business_result.scalar_one_or_none.return_value = self.sample_business
        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_business_result])
        
        # Mock advisor response
        mock_advisor_response = AdvisorResponse(
            message="Thank you for bringing this to our attention. We will address these issues promptly.",
            language="en",
            confidence_score=Decimal("0.85"),
            processing_time_ms=150,
            ai_model="claude-haiku",
            cost_usd=Decimal("0.001")
        )
        self.mock_advisor.generate_response = AsyncMock(return_value=mock_advisor_response)
        
        # Act
        result = await self.service.generate_response_template(
            review_id=self.test_review_id,
            business_id=self.test_business_id,
            tone_preference=tone_preference
        )
        
        # Assert
        assert isinstance(result, ResponseTemplate)
        assert result.tone == ResponseTone.PROFESSIONAL
        
        # Verify tone preference was included in prompt
        call_args = self.mock_advisor.generate_response.call_args
        assert "professional tone" in call_args[1]["message"].lower()

    @pytest.mark.asyncio
    async def test_generate_response_template_review_not_found(self):
        """Test response template generation when review is not found."""
        # Arrange
        mock_result = Mock()
        mock_result.first.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Review .* not found"):
            await self.service.generate_response_template(
                review_id="nonexistent-review",
                business_id=self.test_business_id
            )

    @pytest.mark.asyncio
    async def test_analyze_response_tone_empathetic(self):
        """Test tone analysis for empathetic response."""
        # Arrange
        response_text = "We sincerely apologize for your experience and understand your frustration."
        
        # Act
        result = await self.service.analyze_response_tone(response_text)
        
        # Assert
        assert isinstance(result, ToneAnalysis)
        assert result.primary_tone == ResponseTone.EMPATHETIC
        assert result.empathy_score > 0.6
        assert result.professionalism_score > 0.7
        assert result.tone_confidence > 0.0

    @pytest.mark.asyncio
    async def test_analyze_response_tone_professional(self):
        """Test tone analysis for professional response."""
        # Arrange
        response_text = "Thank you for your feedback. We appreciate your business and will address this matter."
        
        # Act
        result = await self.service.analyze_response_tone(response_text)
        
        # Assert
        assert isinstance(result, ToneAnalysis)
        assert result.primary_tone == ResponseTone.PROFESSIONAL
        assert result.professionalism_score > 0.7

    @pytest.mark.asyncio
    async def test_analyze_response_tone_defensive(self):
        """Test tone analysis for defensive response."""
        # Arrange
        response_text = "Actually, our food is always fresh. However, you may have visited during a busy time."
        
        # Act
        result = await self.service.analyze_response_tone(response_text)
        
        # Assert
        assert isinstance(result, ToneAnalysis)
        assert result.primary_tone == ResponseTone.DEFENSIVE
        assert len(result.issues) > 0
        assert any("defensive" in issue.lower() for issue in result.issues)

    @pytest.mark.asyncio
    async def test_analyze_response_tone_with_suggestions(self):
        """Test tone analysis provides helpful suggestions."""
        # Arrange
        response_text = "We will fix this issue immediately. Your complaint is noted."
        
        # Act
        result = await self.service.analyze_response_tone(response_text)
        
        # Assert
        assert isinstance(result, ToneAnalysis)
        assert len(result.suggestions) > 0
        assert any("thank" in suggestion.lower() for suggestion in result.suggestions)

    @pytest.mark.asyncio
    async def test_get_response_queue_prioritized_order(self):
        """Test response queue returns items in correct priority order."""
        # Arrange
        # Create multiple reviews with different urgency levels
        reviews_data = [
            # High urgency, negative sentiment - should be first
            (
                Review(
                    id="review-1",
                    business_id=self.test_business_id,
                    rating=1,
                    text="Terrible experience",
                    published_at=datetime.utcnow() - timedelta(days=2)
                ),
                Classification(
                    review_id="review-1",
                    sentiment="negative",
                    urgency="high",
                    topics=["service"]
                )
            ),
            # Medium urgency - should be second
            (
                Review(
                    id="review-2",
                    business_id=self.test_business_id,
                    rating=3,
                    text="Average experience",
                    published_at=datetime.utcnow() - timedelta(days=1)
                ),
                Classification(
                    review_id="review-2",
                    sentiment="neutral",
                    urgency="medium",
                    topics=["food_quality"]
                )
            ),
            # Low urgency - should be last
            (
                Review(
                    id="review-3",
                    business_id=self.test_business_id,
                    rating=5,
                    text="Great experience",
                    published_at=datetime.utcnow()
                ),
                Classification(
                    review_id="review-3",
                    sentiment="positive",
                    urgency="low",
                    topics=["service"]
                )
            )
        ]
        
        mock_result = Mock()
        mock_result.fetchall.return_value = reviews_data
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        result = await self.service.get_response_queue(self.test_business_id)
        
        # Assert
        assert len(result) == 3
        assert isinstance(result[0], PriorityQueueItem)
        
        # Verify priority order (highest urgency first)
        assert result[0].priority == ResponsePriority.URGENT
        assert result[1].priority == ResponsePriority.MEDIUM
        assert result[2].priority == ResponsePriority.LOW
        
        # Verify urgency scores are in descending order
        assert result[0].urgency_score >= result[1].urgency_score
        assert result[1].urgency_score >= result[2].urgency_score

    @pytest.mark.asyncio
    async def test_get_response_queue_with_priority_filter(self):
        """Test response queue with priority filter."""
        # Arrange
        reviews_data = [
            (
                Review(
                    id="review-1", 
                    business_id=self.test_business_id, 
                    rating=1,
                    published_at=datetime.utcnow() - timedelta(days=1)
                ),
                Classification(review_id="review-1", sentiment="negative", urgency="high", topics=["service"])
            ),
            (
                Review(
                    id="review-2", 
                    business_id=self.test_business_id, 
                    rating=4,
                    published_at=datetime.utcnow() - timedelta(days=2)
                ),
                Classification(review_id="review-2", sentiment="positive", urgency="low", topics=["food_quality"])
            )
        ]
        
        mock_result = Mock()
        mock_result.fetchall.return_value = reviews_data
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        result = await self.service.get_response_queue(
            self.test_business_id,
            priority_filter=ResponsePriority.URGENT
        )
        
        # Assert
        assert len(result) == 1  # Only urgent priority should be returned
        assert result[0].priority == ResponsePriority.URGENT

    @pytest.mark.asyncio
    async def test_track_response_metrics_calculation(self):
        """Test response metrics calculation."""
        # Arrange
        period_days = 30
        
        # Mock total reviews count
        mock_total_result = Mock()
        mock_total_result.scalar.return_value = 100
        
        # Mock other metric calculations
        self.mock_db.execute = AsyncMock(return_value=mock_total_result)
        
        # Mock helper methods
        self.service._count_responded_reviews = AsyncMock(return_value=75)
        self.service._calculate_avg_response_time = AsyncMock(return_value=4.5)
        self.service._get_responses_by_priority = AsyncMock(return_value={
            ResponsePriority.URGENT: 10,
            ResponsePriority.HIGH: 20,
            ResponsePriority.MEDIUM: 30,
            ResponsePriority.LOW: 15
        })
        self.service._get_responses_by_sentiment = AsyncMock(return_value={
            "positive": 40,
            "negative": 25,
            "neutral": 10
        })
        
        # Act
        result = await self.service.track_response_metrics(
            self.test_business_id,
            period_days=period_days
        )
        
        # Assert
        assert isinstance(result, ResponseMetrics)
        assert result.total_reviews == 100
        assert result.responded_reviews == 75
        assert result.response_rate == 75.0  # 75/100 * 100
        assert result.avg_response_time_hours == 4.5
        assert result.responses_by_priority[ResponsePriority.URGENT] == 10
        assert result.responses_by_sentiment["positive"] == 40

    @pytest.mark.asyncio
    async def test_track_response_metrics_zero_reviews(self):
        """Test response metrics when no reviews exist."""
        # Arrange
        mock_total_result = Mock()
        mock_total_result.scalar.return_value = 0
        self.mock_db.execute = AsyncMock(return_value=mock_total_result)
        
        # Mock helper methods
        self.service._count_responded_reviews = AsyncMock(return_value=0)
        self.service._calculate_avg_response_time = AsyncMock(return_value=0.0)
        self.service._get_responses_by_priority = AsyncMock(return_value={
            priority: 0 for priority in ResponsePriority
        })
        self.service._get_responses_by_sentiment = AsyncMock(return_value={
            "positive": 0, "negative": 0, "neutral": 0
        })
        
        # Act
        result = await self.service.track_response_metrics(self.test_business_id)
        
        # Assert
        assert result.total_reviews == 0
        assert result.responded_reviews == 0
        assert result.response_rate == 0.0  # Should handle division by zero
        assert result.avg_response_time_hours == 0.0

    @pytest.mark.asyncio
    async def test_save_response_success(self):
        """Test successful response saving."""
        # Arrange
        response_text = "Thank you for your feedback. We will address this issue."
        
        # Mock review exists check
        mock_review_result = Mock()
        mock_review_result.scalar_one_or_none.return_value = self.sample_review
        self.mock_db.execute = AsyncMock(return_value=mock_review_result)
        
        # Act
        result = await self.service.save_response(
            review_id=self.test_review_id,
            response_text=response_text,
            user_id=self.test_user_id,
            is_published=True
        )
        
        # Assert
        assert isinstance(result, str)
        assert result.startswith("response-")
        assert self.test_review_id in result

    @pytest.mark.asyncio
    async def test_save_response_review_not_found(self):
        """Test response saving when review doesn't exist."""
        # Arrange
        mock_review_result = Mock()
        mock_review_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_review_result)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Review .* not found"):
            await self.service.save_response(
                review_id="nonexistent-review",
                response_text="Test response",
                user_id=self.test_user_id
            )

    def test_calculate_response_priority_urgent(self):
        """Test priority calculation for urgent responses."""
        # Act
        priority = self.service._calculate_response_priority(
            urgency="high",
            sentiment="negative",
            rating=1
        )
        
        # Assert
        assert priority == ResponsePriority.URGENT

    def test_calculate_response_priority_high(self):
        """Test priority calculation for high priority responses."""
        # Act
        priority = self.service._calculate_response_priority(
            urgency="high",
            sentiment="positive",
            rating=4
        )
        
        # Assert
        assert priority == ResponsePriority.HIGH

    def test_calculate_response_priority_medium(self):
        """Test priority calculation for medium priority responses."""
        # Act
        priority = self.service._calculate_response_priority(
            urgency="medium",
            sentiment="neutral",
            rating=3
        )
        
        # Assert
        assert priority == ResponsePriority.MEDIUM

    def test_calculate_response_priority_low(self):
        """Test priority calculation for low priority responses."""
        # Act
        priority = self.service._calculate_response_priority(
            urgency="low",
            sentiment="positive",
            rating=5
        )
        
        # Assert
        assert priority == ResponsePriority.LOW

    def test_calculate_urgency_score_factors(self):
        """Test urgency score calculation includes all factors."""
        # Act
        score = self.service._calculate_urgency_score(
            urgency="high",
            sentiment="negative",
            rating=1,
            days_since=5
        )
        
        # Assert
        assert score > 0
        # High urgency (40) + negative sentiment (30) + low rating (25) + time factor (10) = 105
        assert score >= 100

    def test_calculate_urgency_score_time_factor_capped(self):
        """Test urgency score time factor is capped at maximum."""
        # Act
        score = self.service._calculate_urgency_score(
            urgency="low",
            sentiment="positive",
            rating=5,
            days_since=100  # Very old review
        )
        
        # Assert
        # Time factor should be capped at 20 points
        # Low urgency (10) + positive (0) + high rating (0) + time cap (20) = 30
        assert score <= 50  # Allow some buffer

    def test_extract_response_template_clean_text(self):
        """Test response template extraction removes meta-commentary."""
        # Arrange
        advisor_message = "Here is your response:\n\nThank you for your feedback. We will improve our service.\n\nThis response addresses the customer's concerns."
        
        # Act
        result = self.service._extract_response_template(advisor_message)
        
        # Assert
        assert result == "Thank you for your feedback. We will improve our service. This response addresses the customer's concerns."
        assert "Here is your response" not in result

    def test_create_response_prompt_includes_review_details(self):
        """Test response prompt includes all relevant review details."""
        # Act
        prompt = self.service._create_response_prompt(
            self.sample_review,
            self.sample_classification,
            ResponseTone.PROFESSIONAL,
            "en"
        )
        
        # Assert
        assert self.sample_review.text in prompt
        assert str(self.sample_review.rating) in prompt
        assert self.sample_classification.sentiment in prompt
        assert "food_quality" in prompt
        assert "service" in prompt
        assert self.sample_classification.urgency in prompt
        assert "professional tone" in prompt.lower()
        assert "en" in prompt

    def test_create_response_prompt_no_tone_preference(self):
        """Test response prompt without tone preference."""
        # Act
        prompt = self.service._create_response_prompt(
            self.sample_review,
            self.sample_classification,
            None,
            "de"
        )
        
        # Assert
        assert "tone" not in prompt.lower() or "Use a" not in prompt
        assert "de" in prompt