"""
Mock helper utilities for creating properly configured service mocks.
"""

from unittest.mock import AsyncMock, Mock
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta

from backend.ai.base import (
    ClassificationResult,
    AdvisorResponse,
    WeeklyReport,
    ReviewClassifierProtocol,
    BusinessAdvisorProtocol,
    CostTracker,
)
from backend.ai.gpt5_classifier import GPT5NanoClassifier
from backend.ai.claude_advisor import ClaudeHaikuAdvisor
from backend.ai.cost_tracker import DatabaseCostTracker


class MockServiceFactory:
    """Factory for creating properly configured service mocks."""
    
    @staticmethod
    def create_gpt5_classifier_mock() -> AsyncMock:
        """Create properly configured GPT-5 classifier mock."""
        mock = AsyncMock(spec=GPT5NanoClassifier)
        
        async def mock_classify_review(text: str, language: str = "en"):
            # Simulate different responses based on text content
            if "excellent" in text.lower() or "great" in text.lower():
                sentiment = "positive"
                urgency = "low"
                confidence = 0.95
            elif "terrible" in text.lower() or "awful" in text.lower():
                sentiment = "negative"
                urgency = "high"
                confidence = 0.92
            else:
                sentiment = "neutral"
                urgency = "medium"
                confidence = 0.85
            
            return ClassificationResult(
                sentiment=sentiment,
                topics=["food_quality", "service"],
                urgency=urgency,
                confidence_score=confidence,
                competitor_mentioned="competitor" in text.lower(),
                processing_time_ms=100,
                ai_model="mock-gpt5-nano",
            )
        
        async def mock_classify_batch(reviews: List[Any]):
            results = []
            for review in reviews:
                text = getattr(review, 'text', str(review))
                result = await mock_classify_review(text)
                results.append(result)
            return results
        
        mock.classify_review.side_effect = mock_classify_review
        mock.classify_batch.side_effect = mock_classify_batch
        
        return mock
    
    @staticmethod
    def create_claude_advisor_mock() -> AsyncMock:
        """Create properly configured Claude advisor mock."""
        mock = AsyncMock(spec=ClaudeHaikuAdvisor)
        
        async def mock_generate_response(message: str, context=None, language: str = "en"):
            # Simulate different responses based on message content
            if "performance" in message.lower():
                response_text = "Based on your recent reviews, your restaurant is performing well with an average rating of 4.2 stars."
            elif "improve" in message.lower():
                response_text = "I recommend focusing on service speed and food temperature consistency based on recent feedback."
            else:
                response_text = "I'm here to help you understand your customer feedback and improve your business."
            
            return AdvisorResponse(
                message=response_text,
                language=language,
                confidence_score=0.92,
                processing_time_ms=200,
                ai_model="mock-claude-haiku",
                cost_usd=Decimal("0.001"),
            )
        
        async def mock_generate_report(business_data=None, language: str = "en"):
            business_id = getattr(business_data, 'business_id', 'test-business-id') if business_data else 'test-business-id'
            
            return WeeklyReport(
                business_id=business_id,
                report_period_start=datetime.now() - timedelta(days=7),
                report_period_end=datetime.now(),
                summary="Your restaurant received 15 reviews this week with an average rating of 4.3 stars.",
                action_items=[
                    "Continue excellent food quality",
                    "Improve service speed during peak hours",
                    "Address cleanliness concerns in restroom area"
                ],
                sentiment_analysis="Overall positive sentiment with 73% positive reviews, 20% neutral, and 7% negative.",
                top_themes=["food_quality", "service", "ambiance"],
                competitor_mentions=2,
                language=language,
                ai_model="mock-claude-haiku",
            )
        
        mock.generate_response.side_effect = mock_generate_response
        mock.generate_report.side_effect = mock_generate_report
        
        return mock
    
    @staticmethod
    def create_cost_tracker_mock() -> AsyncMock:
        """Create properly configured cost tracker mock."""
        mock = AsyncMock(spec=DatabaseCostTracker)
        
        async def mock_log_usage(business_id: str, ai_service: str, operation: str, 
                                tokens_used: int, cost_usd: Decimal, processing_time_ms: int = None):
            return None
        
        async def mock_get_monthly_cost(business_id: str):
            return Decimal("25.50")
        
        async def mock_check_cost_limit(business_id: str):
            return True
        
        async def mock_get_cost_summary(business_id: str):
            return {
                "total_cost": Decimal("25.50"),
                "classification_cost": Decimal("15.30"),
                "chat_cost": Decimal("8.20"),
                "report_cost": Decimal("2.00"),
                "usage_percentage": 25.5,
                "cost_limit": Decimal("100.00"),
                "remaining_budget": Decimal("74.50")
            }
        
        async def mock_validate_operation(business_id: str, operation: str):
            return True  # Allow all operations in tests
        
        mock.log_usage.side_effect = mock_log_usage
        mock.get_monthly_cost.side_effect = mock_get_monthly_cost
        mock.check_cost_limit.side_effect = mock_check_cost_limit
        mock.get_cost_summary.side_effect = mock_get_cost_summary
        mock.validate_operation.side_effect = mock_validate_operation
        
        return mock
    
    @staticmethod
    def create_service_mocks() -> Dict[str, AsyncMock]:
        """Create all service mocks in one call."""
        return {
            "gpt5_classifier": MockServiceFactory.create_gpt5_classifier_mock(),
            "claude_advisor": MockServiceFactory.create_claude_advisor_mock(),
            "cost_tracker": MockServiceFactory.create_cost_tracker_mock(),
        }


class MockResponseFactory:
    """Factory for creating mock API responses."""
    
    @staticmethod
    def create_openai_response(content: str) -> Dict[str, Any]:
        """Create mock OpenAI API response."""
        return {
            "choices": [
                {
                    "message": {
                        "content": content
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
    
    @staticmethod
    def create_anthropic_response(content: str) -> Dict[str, Any]:
        """Create mock Anthropic API response."""
        return {
            "content": [
                {
                    "text": content
                }
            ],
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50
            }
        }
    
    @staticmethod
    def create_google_places_response(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create mock Google Places API response."""
        return {
            "result": {
                "reviews": reviews
            }
        }