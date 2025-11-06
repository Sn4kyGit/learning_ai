"""
Integration tests for GPT-5 Nano classifier with factory and cost tracking.

Tests the complete integration of the classifier with the AI service factory
and cost tracking system.
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.factory import AIServiceFactory
from backend.ai.gpt5_classifier import GPT5NanoClassifier
from backend.ai.base import ReviewText, ClassificationResult
from backend.tests.helpers.mock_helpers import MockServiceFactory


class TestGPT5ClassifierIntegration:
    """Integration tests for GPT5NanoClassifier with factory."""

    @pytest_asyncio.fixture
    async def mock_db_session(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest_asyncio.fixture
    async def cost_tracker(self):
        """Create mock cost tracker."""
        return MockServiceFactory.create_cost_tracker_mock()

    @patch('backend.ai.factory.get_settings')
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_classifier_created_by_factory_works_correctly(self, mock_openai_class, mock_get_settings, mock_db_session):
        """Test that classifier created by factory works correctly."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        # Mock OpenAI client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"sentiment": "positive", "topics": ["food_quality"], "urgency": "low", "competitor_mentioned": false, "confidence_score": 0.9}'
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create factory and classifier
        factory = AIServiceFactory(mock_db_session)
        classifier = factory.create_review_classifier()
        
        # Override the client with our mock
        classifier._client = mock_client
        
        # Act
        result = await classifier.classify_review(
            text="Great food and service!",
            language="en",
            business_id="test-business"
        )
        
        # Assert
        assert isinstance(result, ClassificationResult)
        assert result.sentiment == "positive"
        assert result.topics == ["food_quality"]
        assert result.urgency == "low"
        assert result.ai_model == "gpt-4o-mini"
        
        # Verify API call was made
        mock_client.chat.completions.create.assert_called_once()

    @patch('backend.ai.factory.get_settings')
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_batch_classification_with_cost_tracking(self, mock_openai_class, mock_get_settings, cost_tracker):
        """Test batch classification with proper cost tracking."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        # Mock OpenAI client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''[
            {"sentiment": "positive", "topics": ["food_quality"], "urgency": "low", "competitor_mentioned": false, "confidence_score": 0.9},
            {"sentiment": "negative", "topics": ["service"], "urgency": "high", "competitor_mentioned": false, "confidence_score": 0.85}
        ]'''
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 300
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create classifier with mock cost tracker
        classifier = GPT5NanoClassifier(
            api_key="test-key",
            cost_tracker=cost_tracker
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
        assert results[1].sentiment == "negative"
        
        # Verify cost tracking was called
        assert cost_tracker.log_usage.call_count == 2

    @patch('backend.ai.factory.get_settings')
    def test_factory_validation_includes_classifier_requirements(self, mock_get_settings, mock_db_session):
        """Test that factory validation checks classifier requirements."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = ""  # Missing API key
        mock_settings.anthropic_api_key = "test-anthropic-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(mock_db_session)
        
        # Act
        validation_results = factory.validate_configuration()
        
        # Assert
        assert validation_results["openai_api_key"] is False
        assert validation_results["anthropic_api_key"] is True
        assert validation_results["database_session"] is True

    @patch('backend.ai.factory.get_settings')
    def test_factory_raises_error_for_missing_openai_key(self, mock_get_settings, mock_db_session):
        """Test that factory raises error when OpenAI API key is missing."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = ""
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(mock_db_session)
        
        # Act & Assert
        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            factory.create_review_classifier()

    @patch('backend.ai.factory.get_settings')
    @patch('backend.ai.gpt5_classifier.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_classifier_handles_api_errors_gracefully(self, mock_openai_class, mock_get_settings, mock_db_session):
        """Test that classifier handles API errors gracefully."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        # Mock OpenAI client that raises an error
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        import openai
        
        mock_client.chat.completions.create.side_effect = Exception("Connection failed")
        
        factory = AIServiceFactory(mock_db_session)
        classifier = factory.create_review_classifier()
        classifier._client = mock_client
        
        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            await classifier.classify_review("Test review", "en", "test-business")