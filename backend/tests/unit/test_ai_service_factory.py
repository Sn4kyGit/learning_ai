"""
Unit tests for AI service factory.

Tests the AIServiceFactory for dependency injection,
service creation, and configuration validation.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.factory import AIServiceFactory, create_ai_service_factory
from backend.ai.language_detector import LanguageDetector
from backend.ai.cost_tracker import DatabaseCostTracker
from backend.ai.gpt5_classifier import GPT5NanoClassifier
from backend.ai.claude_advisor import ClaudeHaikuAdvisor


class TestAIServiceFactory:
    """Test suite for AIServiceFactory."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=AsyncSession)
        self.factory = AIServiceFactory(db_session=self.mock_db)

    @patch('backend.ai.factory.get_settings')
    def test_init_creates_factory_with_session(self, mock_get_settings):
        """Test factory initialization with database session."""
        # Arrange
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        # Act
        factory = AIServiceFactory(self.mock_db)
        
        # Assert
        assert factory._db_session == self.mock_db
        assert factory._settings == mock_settings
        assert factory._cost_tracker is None
        assert factory._language_detector is None

    def test_create_language_detector_returns_singleton(self):
        """Test that language detector is created as singleton."""
        # Act
        detector1 = self.factory.create_language_detector()
        detector2 = self.factory.create_language_detector()
        
        # Assert
        assert isinstance(detector1, LanguageDetector)
        assert detector1 is detector2  # Same instance

    def test_create_cost_tracker_returns_database_tracker(self):
        """Test cost tracker creation with database session."""
        # Act
        tracker1 = self.factory.create_cost_tracker()
        tracker2 = self.factory.create_cost_tracker()
        
        # Assert
        assert isinstance(tracker1, DatabaseCostTracker)
        assert tracker1 is tracker2  # Same instance
        assert tracker1._db == self.mock_db

    def test_create_cost_tracker_without_db_session_raises_error(self):
        """Test that cost tracker creation requires database session."""
        # Arrange
        factory = AIServiceFactory(db_session=None)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Database session required"):
            factory.create_cost_tracker()

    @patch('backend.ai.factory.get_settings')
    def test_create_review_classifier_with_valid_api_key(self, mock_get_settings):
        """Test review classifier creation with valid OpenAI API key."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(self.mock_db)
        
        # Act
        classifier = factory.create_review_classifier()
        
        # Assert
        assert isinstance(classifier, GPT5NanoClassifier)
        assert classifier._api_key == "test-openai-key"

    @patch('backend.ai.factory.get_settings')
    def test_create_review_classifier_without_api_key_raises_error(self, mock_get_settings):
        """Test that classifier creation requires OpenAI API key."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = ""
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(self.mock_db)
        
        # Act & Assert
        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            factory.create_review_classifier()

    @patch('backend.ai.factory.get_settings')
    def test_create_business_advisor_with_valid_api_key(self, mock_get_settings):
        """Test business advisor creation with valid Anthropic API key."""
        # Arrange
        mock_settings = Mock()
        mock_settings.anthropic_api_key = "test-anthropic-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(self.mock_db)
        
        # Act
        advisor = factory.create_business_advisor()
        
        # Assert
        assert isinstance(advisor, ClaudeHaikuAdvisor)
        assert advisor._api_key == "test-anthropic-key"

    @patch('backend.ai.factory.get_settings')
    def test_create_business_advisor_without_api_key_raises_error(self, mock_get_settings):
        """Test that advisor creation requires Anthropic API key."""
        # Arrange
        mock_settings = Mock()
        mock_settings.anthropic_api_key = ""
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(self.mock_db)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Anthropic API key not configured"):
            factory.create_business_advisor()

    @patch('backend.ai.factory.get_settings')
    def test_create_ai_services_returns_all_services(self, mock_get_settings):
        """Test creating all AI services as a bundle."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.anthropic_api_key = "test-anthropic-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(self.mock_db)
        
        # Act
        services = factory.create_ai_services()
        
        # Assert
        assert "language_detector" in services
        assert "cost_tracker" in services
        assert "review_classifier" in services
        assert "business_advisor" in services
        
        assert isinstance(services["language_detector"], LanguageDetector)
        assert isinstance(services["cost_tracker"], DatabaseCostTracker)
        assert isinstance(services["review_classifier"], GPT5NanoClassifier)
        assert isinstance(services["business_advisor"], ClaudeHaikuAdvisor)

    @patch('backend.ai.factory.get_settings')
    def test_create_ai_services_raises_error_for_missing_keys(self, mock_get_settings):
        """Test that creating all services fails with missing API keys."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = ""  # Missing
        mock_settings.anthropic_api_key = "test-anthropic-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(self.mock_db)
        
        # Act & Assert
        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            factory.create_ai_services()

    @patch('backend.ai.factory.get_settings')
    def test_validate_configuration_returns_validation_results(self, mock_get_settings):
        """Test configuration validation."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.anthropic_api_key = "test-anthropic-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(self.mock_db)
        
        with patch.object(LanguageDetector, 'is_available', True):
            # Act
            results = factory.validate_configuration()
            
            # Assert
            assert results["language_detector"] is True
            assert results["openai_api_key"] is True
            assert results["anthropic_api_key"] is True
            assert results["database_session"] is True
            assert results["cost_limit_configured"] is True
            assert results["langdetect_available"] is True

    @patch('backend.ai.factory.get_settings')
    def test_validate_configuration_detects_missing_requirements(self, mock_get_settings):
        """Test validation with missing configuration."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = ""  # Missing
        mock_settings.anthropic_api_key = "test-anthropic-key"
        mock_settings.default_monthly_cost_limit = 0  # Invalid
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(db_session=None)  # Missing DB
        
        with patch.object(LanguageDetector, 'is_available', False):
            # Act
            results = factory.validate_configuration()
            
            # Assert
            assert results["openai_api_key"] is False
            assert results["anthropic_api_key"] is True
            assert results["database_session"] is False
            assert results["cost_limit_configured"] is False
            assert results["langdetect_available"] is False

    @patch('backend.ai.factory.get_settings')
    def test_cost_tracker_uses_configured_default_limit(self, mock_get_settings):
        """Test that cost tracker uses configured default limit."""
        # Arrange
        mock_settings = Mock()
        mock_settings.default_monthly_cost_limit = 250.0
        mock_get_settings.return_value = mock_settings
        
        factory = AIServiceFactory(self.mock_db)
        
        # Act
        tracker = factory.create_cost_tracker()
        
        # Assert
        assert tracker._default_cost_limit == Decimal("250.0")

    def test_create_ai_service_factory_function(self):
        """Test the factory creation function."""
        # Act
        factory = create_ai_service_factory(self.mock_db)
        
        # Assert
        assert isinstance(factory, AIServiceFactory)
        assert factory._db_session == self.mock_db

    def test_create_ai_service_factory_without_db_session(self):
        """Test factory creation without database session."""
        # Act
        factory = create_ai_service_factory()
        
        # Assert
        assert isinstance(factory, AIServiceFactory)
        assert factory._db_session is None


class TestAIServiceFactoryIntegration:
    """Integration tests for AI service factory."""

    @patch('backend.ai.factory.get_settings')
    def test_services_share_cost_tracker_instance(self, mock_get_settings):
        """Test that services share the same cost tracker instance."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.anthropic_api_key = "test-anthropic-key"
        mock_settings.default_monthly_cost_limit = 100.0
        mock_get_settings.return_value = mock_settings
        
        mock_db = Mock(spec=AsyncSession)
        factory = AIServiceFactory(mock_db)
        
        # Act
        classifier = factory.create_review_classifier()
        advisor = factory.create_business_advisor()
        cost_tracker = factory.create_cost_tracker()
        
        # Assert
        assert classifier._cost_tracker is cost_tracker
        assert advisor._cost_tracker is cost_tracker

    @patch('backend.ai.factory.get_settings')
    def test_factory_handles_service_creation_errors_gracefully(self, mock_get_settings):
        """Test that factory handles service creation errors."""
        # Arrange
        mock_settings = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.anthropic_api_key = "test-key"
        mock_get_settings.return_value = mock_settings
        
        # Mock database session that raises error
        mock_db = Mock(spec=AsyncSession)
        factory = AIServiceFactory(mock_db)
        
        # Act & Assert - Should not raise during factory creation
        assert factory is not None
        
        # Services should still be creatable
        detector = factory.create_language_detector()
        assert isinstance(detector, LanguageDetector)