"""
Unit tests for GPT-5 Nano review classifier.

Tests the GPT5NanoClassifier implementation including API calls,
batch processing, error handling, and cost tracking.
"""

import json
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from typing import List

from backend.ai.gpt5_classifier import GPT5NanoClassifier
from backend.ai.base import ClassificationResult, ReviewText, CostTracker
from backend.tests.unit.test_ai_base_protocols import MockCostTracker

import openai


class TestGPT5NanoClassifier:
    """Test suite for GPT5NanoClassifier."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"
        self.cost_tracker = MockCostTracker()
        self.classifier = GPT5NanoClassifier(
            api_key=self.api_key,
            cost_tracker=self.cost_tracker,
            model_name="gpt-4o-mini",
            max_retries=2,
            retry_delay=0.1,  # Fast retries for testing
            request_timeout=10
        )

    def test_init_creates_classifier_with_config(self):
        """Test classifier initialization with configuration."""
        # Act
        classifier = GPT5NanoClassifier(
            api_key="test-key",
            cost_tracker=self.cost_tracker,
            model_name="custom-model",
            max_retries=5,
            retry_delay=2.0,
            request_timeout=60
        )
        
        # Assert
        assert classifier._api_key == "test-key"
        assert classifier._cost_tracker == self.cost_tracker
        assert classifier._model_name == "custom-model"
        assert classifier._max_retries == 5
        assert classifier._retry_delay == 2.0
        assert classifier._request_timeout == 60
        assert classifier._client is not None

    @pytest.mark.asyncio
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    async def test_classify_review_success(self, mock_openai_class):
        """Test successful single review classification."""
        # Arrange
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "sentiment": "positive",
            "topics": ["food_quality", "service"],
            "urgency": "low",
            "competitor_mentioned": False,
            "confidence_score": 0.95
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create new classifier with mocked client
        classifier = GPT5NanoClassifier(
            api_key=self.api_key,
            cost_tracker=self.cost_tracker
        )
        classifier._client = mock_client
        
        # Act
        result = await classifier.classify_review(
            text="Great food and excellent service!",
            language="en",
            business_id="test-business"
        )
        
        # Assert
        assert isinstance(result, ClassificationResult)
        assert result.sentiment == "positive"
        assert result.topics == ["food_quality", "service"]
        assert result.urgency == "low"
        assert result.competitor_mentioned is False
        assert result.confidence_score == 0.95
        assert result.ai_model == "gpt-4o-mini"
        assert result.processing_time_ms >= 0  # Allow 0 for mocked calls
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o-mini"
        assert call_args[1]["temperature"] == 0.1
        assert call_args[1]["max_tokens"] == 1000
        assert call_args[1]["response_format"] == {"type": "json_object"}
        
        # Verify cost tracking
        assert len(self.cost_tracker.logged_usage) == 1
        usage_log = self.cost_tracker.logged_usage[0]
        assert usage_log["business_id"] == "test-business"
        assert usage_log["ai_service"] == "gpt4o_mini"
        assert usage_log["operation"] == "classify_single"
        assert usage_log["tokens_used"] == 150

    @pytest.mark.asyncio
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    async def test_classify_review_with_invalid_json_response(self, mock_openai_class):
        """Test handling of invalid JSON response."""
        # Arrange
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        
        mock_client.chat.completions.create.return_value = mock_response
        
        classifier = GPT5NanoClassifier(
            api_key=self.api_key,
            cost_tracker=self.cost_tracker
        )
        classifier._client = mock_client
        
        # Act
        result = await classifier.classify_review(
            text="Test review",
            language="en",
            business_id="test-business"
        )
        
        # Assert - Should return default values
        assert result.sentiment == "neutral"
        assert result.topics == []
        assert result.urgency == "low"
        assert result.competitor_mentioned is False
        assert result.confidence_score == 0.5

    @pytest.mark.asyncio
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    async def test_classify_review_rate_limit_retry(self, mock_openai_class):
        """Test retry logic for rate limit errors."""
        # Arrange
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # First call raises rate limit error, second succeeds
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "sentiment": "positive",
            "topics": ["food_quality"],
            "urgency": "low",
            "competitor_mentioned": False,
            "confidence_score": 0.9
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        
        # Create a mock request object for the exception
        mock_request = Mock()
        mock_response_obj = Mock()
        mock_response_obj.request = mock_request
        
        mock_client.chat.completions.create.side_effect = [
            openai.RateLimitError("Rate limit exceeded", response=mock_response_obj, body=None),
            mock_response
        ]
        
        classifier = GPT5NanoClassifier(
            api_key=self.api_key,
            cost_tracker=self.cost_tracker,
            max_retries=2,
            retry_delay=0.01  # Very fast for testing
        )
        classifier._client = mock_client
        
        # Act
        result = await classifier.classify_review("Test review", "en", "test-business")
        
        # Assert
        assert result.sentiment == "positive"
        assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    async def test_classify_review_max_retries_exceeded(self, mock_openai_class):
        """Test failure after max retries exceeded."""
        # Arrange
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Create a mock request object for the exception
        mock_request = Mock()
        mock_response_obj = Mock()
        mock_response_obj.request = mock_request
        
        mock_client.chat.completions.create.side_effect = openai.RateLimitError(
            "Rate limit exceeded", response=mock_response_obj, body=None
        )
        
        classifier = GPT5NanoClassifier(
            api_key=self.api_key,
            cost_tracker=self.cost_tracker,
            max_retries=2,
            retry_delay=0.01
        )
        classifier._client = mock_client
        
        # Act & Assert
        with pytest.raises(openai.RateLimitError):
            await classifier.classify_review("Test review", "en", "test-business")
        
        assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    async def test_classify_batch_success(self, mock_openai_class):
        """Test successful batch review classification."""
        # Arrange
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock batch API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([
            {
                "sentiment": "positive",
                "topics": ["food_quality"],
                "urgency": "low",
                "competitor_mentioned": False,
                "confidence_score": 0.9
            },
            {
                "sentiment": "negative",
                "topics": ["service"],
                "urgency": "high",
                "competitor_mentioned": False,
                "confidence_score": 0.85
            }
        ])
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 300
        
        mock_client.chat.completions.create.return_value = mock_response
        
        classifier = GPT5NanoClassifier(
            api_key=self.api_key,
            cost_tracker=self.cost_tracker
        )
        classifier._client = mock_client
        
        reviews = [
            ReviewText("1", "Great food!", "en", "business-1"),
            ReviewText("2", "Terrible service!", "en", "business-2")
        ]
        
        # Act
        results = await classifier.classify_batch(reviews)
        
        # Assert
        assert len(results) == 2
        
        assert results[0].sentiment == "positive"
        assert results[0].topics == ["food_quality"]
        assert results[0].urgency == "low"
        
        assert results[1].sentiment == "negative"
        assert results[1].topics == ["service"]
        assert results[1].urgency == "high"
        
        # Verify cost tracking for both businesses
        assert len(self.cost_tracker.logged_usage) == 2
        assert self.cost_tracker.logged_usage[0]["business_id"] == "business-1"
        assert self.cost_tracker.logged_usage[1]["business_id"] == "business-2"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_classify_batch_empty_list(self):
        """Test batch classification with empty review list."""
        # Act
        results = await self.classifier.classify_batch([])
        
        # Assert
        assert results == []

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_classify_batch_exceeds_limit(self):
        """Test batch classification with too many reviews."""
        # Arrange
        reviews = [ReviewText(str(i), f"Review {i}", "en", "business") for i in range(501)]
        
        # Act & Assert
        with pytest.raises(ValueError, match="Batch size cannot exceed 500 reviews"):
            await self.classifier.classify_batch(reviews)

    @pytest.mark.asyncio
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    async def test_classify_batch_with_invalid_response(self, mock_openai_class):
        """Test batch classification with invalid API response."""
        # Arrange
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Not a JSON array"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        
        mock_client.chat.completions.create.return_value = mock_response
        
        classifier = GPT5NanoClassifier(
            api_key=self.api_key,
            cost_tracker=self.cost_tracker
        )
        classifier._client = mock_client
        
        reviews = [
            ReviewText("1", "Test review 1", "en", "business-1"),
            ReviewText("2", "Test review 2", "en", "business-2")
        ]
        
        # Act
        results = await classifier.classify_batch(reviews)
        
        # Assert - Should return default classifications
        assert len(results) == 2
        for result in results:
            assert result.sentiment == "neutral"
            assert result.topics == []
            assert result.urgency == "low"
            assert result.confidence_score == 0.5

    def test_create_classification_prompt(self):
        """Test single review prompt creation."""
        # Act
        messages = self.classifier._create_classification_prompt("Great food!", "en")
        
        # Assert
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "JSON response" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "Great food!" in messages[1]["content"]
        assert "language: en" in messages[1]["content"]

    def test_create_batch_classification_prompt(self):
        """Test batch review prompt creation."""
        # Arrange
        reviews = [
            ReviewText("1", "Great food!", "en", "business-1"),
            ReviewText("2", "Bad service!", "de", "business-2")
        ]
        
        # Act
        messages = self.classifier._create_batch_classification_prompt(reviews)
        
        # Assert
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "JSON array" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "1. (language: en) Great food!" in messages[1]["content"]
        assert "2. (language: de) Bad service!" in messages[1]["content"]

    def test_parse_classification_response_valid(self):
        """Test parsing valid classification response."""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "sentiment": "positive",
            "topics": ["food_quality", "service"],
            "urgency": "medium",
            "competitor_mentioned": True,
            "confidence_score": 0.92
        })
        
        # Act
        result = self.classifier._parse_classification_response(mock_response)
        
        # Assert
        assert result["sentiment"] == "positive"
        assert result["topics"] == ["food_quality", "service"]
        assert result["urgency"] == "medium"
        assert result["competitor_mentioned"] is True
        assert result["confidence_score"] == 0.92

    def test_parse_classification_response_invalid_values(self):
        """Test parsing response with invalid values."""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "sentiment": "invalid_sentiment",
            "topics": "not_a_list",
            "urgency": "invalid_urgency",
            "competitor_mentioned": "not_boolean",
            "confidence_score": 2.5  # Out of range
        })
        
        # Act
        result = self.classifier._parse_classification_response(mock_response)
        
        # Assert - Should be corrected to valid values
        assert result["sentiment"] == "neutral"
        assert result["topics"] == []
        assert result["urgency"] == "low"
        assert result["confidence_score"] == 0.5

    def test_parse_classification_response_missing_fields(self):
        """Test parsing response with missing fields."""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "sentiment": "positive"
            # Missing other required fields
        })
        
        # Act
        result = self.classifier._parse_classification_response(mock_response)
        
        # Assert - Should use defaults for missing fields
        assert result["sentiment"] == "positive"
        assert result["topics"] == []
        assert result["urgency"] == "low"
        assert result["competitor_mentioned"] is False
        assert result["confidence_score"] == 0.5

    def test_parse_batch_classification_response_valid(self):
        """Test parsing valid batch classification response."""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([
            {
                "sentiment": "positive",
                "topics": ["food_quality"],
                "urgency": "low",
                "competitor_mentioned": False,
                "confidence_score": 0.9
            },
            {
                "sentiment": "negative",
                "topics": ["service"],
                "urgency": "high",
                "competitor_mentioned": False,
                "confidence_score": 0.85
            }
        ])
        
        # Act
        results = self.classifier._parse_batch_classification_response(mock_response, 2)
        
        # Assert
        assert len(results) == 2
        assert results[0]["sentiment"] == "positive"
        assert results[1]["sentiment"] == "negative"

    def test_parse_batch_classification_response_insufficient_results(self):
        """Test parsing batch response with fewer results than expected."""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([
            {
                "sentiment": "positive",
                "topics": ["food_quality"],
                "urgency": "low",
                "competitor_mentioned": False,
                "confidence_score": 0.9
            }
        ])
        
        # Act - Expect 3 results but only get 1
        results = self.classifier._parse_batch_classification_response(mock_response, 3)
        
        # Assert - Should pad with defaults
        assert len(results) == 3
        assert results[0]["sentiment"] == "positive"
        assert results[1]["sentiment"] == "neutral"  # Default
        assert results[2]["sentiment"] == "neutral"  # Default

    def test_validate_classification_data(self):
        """Test classification data validation."""
        # Arrange
        invalid_data = {
            "sentiment": "invalid",
            "topics": "not_a_list",
            "urgency": "invalid",
            "competitor_mentioned": "not_boolean",
            "confidence_score": -0.5
        }
        
        # Act
        result = self.classifier._validate_classification_data(invalid_data)
        
        # Assert
        assert result["sentiment"] == "neutral"
        assert result["topics"] == []
        assert result["urgency"] == "low"
        assert result["confidence_score"] == 0.5

    def test_calculate_cost(self):
        """Test cost calculation based on token usage."""
        # Arrange
        mock_usage = Mock()
        mock_usage.prompt_tokens = 1000  # 1K input tokens
        mock_usage.completion_tokens = 500  # 0.5K output tokens
        
        # Act
        cost = self.classifier._calculate_cost(mock_usage)
        
        # Assert
        expected_input_cost = Decimal("1.0") * self.classifier.INPUT_TOKEN_COST
        expected_output_cost = Decimal("0.5") * self.classifier.OUTPUT_TOKEN_COST
        expected_total = expected_input_cost + expected_output_cost
        
        assert cost == expected_total
        assert cost > 0


class TestGPT5NanoClassifierIntegration:
    """Integration tests for GPT5NanoClassifier."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cost_tracker = MockCostTracker()

    @pytest.mark.asyncio
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    async def test_performance_batch_processing_under_60_seconds(self, mock_openai_class):
        """Test that batch processing of 500 reviews completes within 60 seconds."""
        # Arrange
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Create mock response for 500 reviews
        classifications = []
        for i in range(500):
            classifications.append({
                "sentiment": "positive" if i % 2 == 0 else "negative",
                "topics": ["food_quality"],
                "urgency": "low",
                "competitor_mentioned": False,
                "confidence_score": 0.9
            })
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(classifications)
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10000
        mock_response.usage.completion_tokens = 5000
        mock_response.usage.total_tokens = 15000
        
        # Simulate realistic API delay
        async def mock_create(*args, **kwargs):
            await asyncio.sleep(0.5)  # 500ms delay
            return mock_response
        
        mock_client.chat.completions.create = mock_create
        
        classifier = GPT5NanoClassifier(
            api_key="test-key",
            cost_tracker=self.cost_tracker
        )
        classifier._client = mock_client
        
        # Create 500 test reviews
        reviews = [
            ReviewText(str(i), f"Review {i}", "en", f"business-{i % 10}")
            for i in range(500)
        ]
        
        # Act
        import time
        start_time = time.time()
        results = await classifier.classify_batch(reviews)
        end_time = time.time()
        
        # Assert
        processing_time = end_time - start_time
        assert processing_time < 60  # Must complete within 60 seconds
        assert len(results) == 500
        assert all(isinstance(r, ClassificationResult) for r in results)

    @pytest.mark.asyncio
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    async def test_cost_tracking_accuracy(self, mock_openai_class):
        """Test accuracy of cost tracking calculations."""
        # Arrange
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "sentiment": "positive",
            "topics": ["food_quality"],
            "urgency": "low",
            "competitor_mentioned": False,
            "confidence_score": 0.9
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 1000
        mock_response.usage.completion_tokens = 500
        mock_response.usage.total_tokens = 1500
        
        mock_client.chat.completions.create.return_value = mock_response
        
        classifier = GPT5NanoClassifier(
            api_key="test-key",
            cost_tracker=self.cost_tracker
        )
        classifier._client = mock_client
        
        # Act
        await classifier.classify_review("Test review", "en", "test-business")
        
        # Assert
        assert len(self.cost_tracker.logged_usage) == 1
        usage_log = self.cost_tracker.logged_usage[0]
        
        # Verify cost calculation
        expected_input_cost = Decimal("1.0") * classifier.INPUT_TOKEN_COST
        expected_output_cost = Decimal("0.5") * classifier.OUTPUT_TOKEN_COST
        expected_total_cost = expected_input_cost + expected_output_cost
        
        assert usage_log["cost_usd"] == expected_total_cost
        assert usage_log["tokens_used"] == 1500


# Import asyncio for the performance test
import asyncio