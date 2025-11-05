"""
AI service factory for dependency injection.

This module provides a factory pattern for creating AI services
with proper dependency injection and configuration management.
"""

import logging
from typing import Optional
from decimal import Decimal

from backend.config import get_settings
from backend.ai.base import ReviewClassifierProtocol, BusinessAdvisorProtocol, CostTracker
from backend.ai.language_detector import LanguageDetector
from backend.ai.cost_tracker import DatabaseCostTracker
from backend.ai.gpt5_classifier import GPT5NanoClassifier

logger = logging.getLogger(__name__)


class AIServiceFactory:
    """Factory for creating AI services with dependency injection."""

    def __init__(self, db_session=None):
        """Initialize AI service factory.

        Args:
            db_session: Database session for cost tracking
        """
        self._settings = get_settings()
        self._db_session = db_session
        self._cost_tracker: Optional[CostTracker] = None
        self._language_detector: Optional[LanguageDetector] = None

    def create_language_detector(self) -> LanguageDetector:
        """Create language detector service.

        Returns:
            Configured LanguageDetector instance
        """
        if self._language_detector is None:
            self._language_detector = LanguageDetector()
            logger.info("Language detector service created")
        
        return self._language_detector

    def create_cost_tracker(self) -> CostTracker:
        """Create cost tracking service.

        Returns:
            Configured CostTracker instance
        """
        if self._cost_tracker is None:
            if self._db_session is None:
                raise ValueError("Database session required for cost tracking")
            
            default_limit = Decimal(str(self._settings.default_monthly_cost_limit))
            self._cost_tracker = DatabaseCostTracker(
                db_session=self._db_session,
                default_cost_limit=default_limit
            )
            logger.info("Cost tracker service created")
        
        return self._cost_tracker

    def create_review_classifier(self) -> ReviewClassifierProtocol:
        """Create review classification service.

        Returns:
            Configured ReviewClassifierProtocol implementation

        Raises:
            ValueError: If OpenAI API key is not configured
        """
        if not self._settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        cost_tracker = self.create_cost_tracker()
        
        classifier = GPT5NanoClassifier(
            api_key=self._settings.openai_api_key,
            cost_tracker=cost_tracker
        )
        
        logger.info("GPT-5 Nano classifier service created")
        return classifier

    def create_business_advisor(self) -> BusinessAdvisorProtocol:
        """Create business advisory service.

        Returns:
            Configured BusinessAdvisorProtocol implementation

        Raises:
            ValueError: If Anthropic API key is not configured
        """
        if not self._settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")

        cost_tracker = self.create_cost_tracker()
        
        # Import here to avoid circular imports
        from backend.ai.claude_advisor import ClaudeHaikuAdvisor
        
        advisor = ClaudeHaikuAdvisor(
            api_key=self._settings.anthropic_api_key,
            cost_tracker=cost_tracker
        )
        
        logger.info("Claude Haiku advisor service created")
        return advisor

    def create_ai_services(self) -> dict:
        """Create all AI services as a bundle.

        Returns:
            Dictionary containing all AI services

        Raises:
            ValueError: If required API keys are not configured
        """
        services = {
            "language_detector": self.create_language_detector(),
            "cost_tracker": self.create_cost_tracker(),
            "review_classifier": self.create_review_classifier(),
            "business_advisor": self.create_business_advisor(),
        }
        
        logger.info("All AI services created successfully")
        return services

    def validate_configuration(self) -> dict:
        """Validate AI service configuration.

        Returns:
            Dictionary with validation results for each service
        """
        validation_results = {
            "language_detector": True,  # Always available
            "openai_api_key": bool(self._settings.openai_api_key),
            "anthropic_api_key": bool(self._settings.anthropic_api_key),
            "database_session": self._db_session is not None,
            "cost_limit_configured": self._settings.default_monthly_cost_limit > 0,
        }

        # Check if langdetect is available
        language_detector = LanguageDetector()
        validation_results["langdetect_available"] = language_detector.is_available

        logger.info(f"AI service configuration validation: {validation_results}")
        return validation_results


def create_ai_service_factory(db_session=None) -> AIServiceFactory:
    """Create AI service factory with database session.

    Args:
        db_session: Database session for cost tracking

    Returns:
        Configured AIServiceFactory instance
    """
    return AIServiceFactory(db_session=db_session)


# Convenience functions for dependency injection
async def get_review_classifier() -> ReviewClassifierProtocol:
    """Get review classifier service for dependency injection.
    
    Returns:
        Configured ReviewClassifierProtocol implementation
    """
    # This will be used in route dependencies
    # For now, create a factory without DB session (will be injected separately)
    factory = AIServiceFactory()
    return factory.create_review_classifier()


async def get_business_advisor() -> BusinessAdvisorProtocol:
    """Get business advisor service for dependency injection.
    
    Returns:
        Configured BusinessAdvisorProtocol implementation
    """
    # This will be used in route dependencies
    # For now, create a factory without DB session (will be injected separately)
    factory = AIServiceFactory()
    return factory.create_business_advisor()


def get_language_detector() -> LanguageDetector:
    """Get language detector service for dependency injection.
    
    Returns:
        Configured LanguageDetector instance
    """
    factory = AIServiceFactory()
    return factory.create_language_detector()