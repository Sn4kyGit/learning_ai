"""
Mock API response fixtures for external services.

This module provides comprehensive mock responses for Google Places API,
OpenAI API, Anthropic API, and other external services used in testing.
"""

import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime, timedelta

# Removed circular import - MockDataFactory methods will be defined locally

class MockDataFactory:
    """Factory for creating mock API response data."""
    
    @staticmethod
    def create_openai_classification_response(
        sentiment: str = "positive",
        topics: List[str] = None,
        urgency: str = "low",
        confidence: float = 0.95,
        competitor_mentioned: bool = False
    ) -> str:
        """Create mock OpenAI classification response."""
        if topics is None:
            topics = ["food_quality", "service"]
        
        return json.dumps({
            "sentiment": sentiment,
            "topics": topics,
            "urgency": urgency,
            "competitor_mentioned": competitor_mentioned,
            "confidence_score": confidence
        })
    
    @staticmethod
    def create_google_places_review(
        rating: int = 4,
        text: str = "Great restaurant experience!",
        author: str = "Test User",
        days_ago: int = 5
    ) -> Dict[str, Any]:
        """Create mock Google Places review."""
        return {
            "author_name": author,
            "rating": rating,
            "text": text,
            "time": int((datetime.now() - timedelta(days=days_ago)).timestamp()),
            "language": "en",
            "author_url": f"https://www.google.com/maps/contrib/{hash(author)}",
            "profile_photo_url": "https://lh3.googleusercontent.com/a-/photo.jpg",
            "relative_time_description": f"{days_ago} days ago"
        }
    
    @staticmethod
    def create_google_places_response(
        reviews: List[Dict[str, Any]] = None,
        place_id: str = "test-place-123",
        name: str = "Test Restaurant",
        rating: float = 4.2
    ) -> Dict[str, Any]:
        """Create mock Google Places API response."""
        if reviews is None:
            reviews = [MockDataFactory.create_google_places_review()]
        
        return {
            "result": {
                "place_id": place_id,
                "name": name,
                "rating": rating,
                "user_ratings_total": len(reviews),
                "reviews": reviews
            },
            "status": "OK"
        }
    
    @staticmethod
    def create_anthropic_advisor_response(
        message: str = "Based on your reviews, I recommend focusing on service improvements."
    ) -> str:
        """Create mock Anthropic advisor response."""
        return message


class MockAPIResponses:
    """Collection of mock API responses for testing."""
    
    # Google Places API Mock Responses
    GOOGLE_PLACES_SUCCESS = {
        "result": {
            "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "name": "Test Restaurant",
            "rating": 4.2,
            "user_ratings_total": 150,
            "formatted_address": "123 Test Street, Test City, TC 12345",
            "formatted_phone_number": "(555) 123-4567",
            "website": "https://www.testrestaurant.com",
            "business_status": "OPERATIONAL",
            "price_level": 2,
            "types": ["restaurant", "food", "establishment"],
            "reviews": [
                {
                    "author_name": "John D.",
                    "rating": 5,
                    "text": "Excellent food and service! Highly recommend the pasta dishes.",
                    "time": int((datetime.now() - timedelta(days=2)).timestamp()),
                    "language": "en",
                    "author_url": "https://www.google.com/maps/contrib/123456789",
                    "profile_photo_url": "https://lh3.googleusercontent.com/a-/photo1.jpg",
                    "relative_time_description": "2 days ago"
                },
                {
                    "author_name": "Sarah M.",
                    "rating": 4,
                    "text": "Great atmosphere and friendly staff. Food was delicious.",
                    "time": int((datetime.now() - timedelta(days=5)).timestamp()),
                    "language": "en",
                    "author_url": "https://www.google.com/maps/contrib/987654321",
                    "profile_photo_url": "https://lh3.googleusercontent.com/a-/photo2.jpg",
                    "relative_time_description": "5 days ago"
                }
            ]
        },
        "status": "OK"
    }
    
    GOOGLE_PLACES_NOT_FOUND = {
        "status": "NOT_FOUND",
        "error_message": "The referenced location was not found in the Places database."
    }
    
    GOOGLE_PLACES_ZERO_RESULTS = {
        "result": {
            "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "name": "Test Restaurant",
            "rating": 4.2,
            "user_ratings_total": 0,
            "reviews": []
        },
        "status": "OK"
    }
    
    GOOGLE_PLACES_RATE_LIMIT = {
        "status": "OVER_QUERY_LIMIT",
        "error_message": "You have exceeded your daily request quota for this API."
    }
    
    # OpenAI API Mock Responses
    OPENAI_CLASSIFICATION_SUCCESS = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-5-nano",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps({
                        "sentiment": "positive",
                        "topics": ["food_quality", "service"],
                        "urgency": "low",
                        "competitor_mentioned": False,
                        "confidence_score": 0.95
                    })
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 45,
            "completion_tokens": 25,
            "total_tokens": 70
        }
    }
    
    OPENAI_RATE_LIMIT_ERROR = {
        "error": {
            "message": "Rate limit reached for requests",
            "type": "rate_limit_exceeded",
            "param": None,
            "code": "rate_limit_exceeded"
        }
    }
    
    OPENAI_INVALID_API_KEY = {
        "error": {
            "message": "Incorrect API key provided",
            "type": "invalid_request_error",
            "param": None,
            "code": "invalid_api_key"
        }
    }
    
    # Anthropic API Mock Responses
    ANTHROPIC_CHAT_SUCCESS = {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Based on your recent reviews, I recommend focusing on service speed during peak hours. Your food quality ratings are excellent, but several customers mentioned longer wait times."
            }
        ],
        "model": "claude-3-haiku-20240307",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 120,
            "output_tokens": 45
        }
    }
    
    ANTHROPIC_REPORT_SUCCESS = {
        "id": "msg_456",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": """Weekly Performance Report

Summary: Your restaurant had a strong week with 85% positive sentiment and improved ratings compared to last week.

Key Action Items:
• Continue excellent food quality standards
• Focus on reducing wait times during peak hours
• Respond to negative reviews within 24 hours
• Highlight positive customer feedback in marketing

Sentiment Analysis: Overall positive trend with customers particularly praising food quality and ambiance. Some concerns about service speed during busy periods.

Recommendations: Maintain current food quality standards while implementing strategies to improve service efficiency during peak dining hours."""
            }
        ],
        "model": "claude-3-haiku-20240307",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 250,
            "output_tokens": 120
        }
    }
    
    ANTHROPIC_RATE_LIMIT_ERROR = {
        "type": "error",
        "error": {
            "type": "rate_limit_error",
            "message": "Number of requests per minute exceeded"
        }
    }


@pytest.fixture
def mock_google_places_client():
    """Mock Google Places API client."""
    client = AsyncMock()
    
    # Configure successful response by default
    client.get_place_details.return_value = MockAPIResponses.GOOGLE_PLACES_SUCCESS
    client.get_place_reviews.return_value = MockAPIResponses.GOOGLE_PLACES_SUCCESS["result"]["reviews"]
    
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI API client."""
    client = AsyncMock()
    
    # Configure successful classification response
    client.chat.completions.create.return_value = Mock(
        choices=[Mock(
            message=Mock(
                content=json.dumps({
                    "sentiment": "positive",
                    "topics": ["food_quality", "service"],
                    "urgency": "low",
                    "competitor_mentioned": False,
                    "confidence_score": 0.95
                })
            )
        )],
        usage=Mock(
            prompt_tokens=45,
            completion_tokens=25,
            total_tokens=70
        )
    )
    
    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client."""
    client = AsyncMock()
    
    # Configure successful chat response
    client.messages.create.return_value = Mock(
        content=[Mock(
            text="Based on your reviews, I recommend focusing on service quality improvements."
        )],
        usage=Mock(
            input_tokens=120,
            output_tokens=45
        )
    )
    
    return client


@pytest.fixture
def mock_api_responses_success():
    """Collection of successful mock API responses."""
    return {
        "google_places": MockAPIResponses.GOOGLE_PLACES_SUCCESS,
        "openai_classification": MockAPIResponses.OPENAI_CLASSIFICATION_SUCCESS,
        "anthropic_chat": MockAPIResponses.ANTHROPIC_CHAT_SUCCESS,
        "anthropic_report": MockAPIResponses.ANTHROPIC_REPORT_SUCCESS
    }


@pytest.fixture
def mock_api_responses_errors():
    """Collection of error mock API responses."""
    return {
        "google_places_not_found": MockAPIResponses.GOOGLE_PLACES_NOT_FOUND,
        "google_places_rate_limit": MockAPIResponses.GOOGLE_PLACES_RATE_LIMIT,
        "openai_rate_limit": MockAPIResponses.OPENAI_RATE_LIMIT_ERROR,
        "openai_invalid_key": MockAPIResponses.OPENAI_INVALID_API_KEY,
        "anthropic_rate_limit": MockAPIResponses.ANTHROPIC_RATE_LIMIT_ERROR
    }


@pytest.fixture
def mock_batch_responses():
    """Mock responses for batch operations."""
    return {
        "classifications": [
            MockDataFactory.create_openai_classification_response(
                sentiment="positive",
                topics=["food_quality"],
                confidence=0.95
            ),
            MockDataFactory.create_openai_classification_response(
                sentiment="negative",
                topics=["service", "wait_time"],
                urgency="high",
                confidence=0.88
            ),
            MockDataFactory.create_openai_classification_response(
                sentiment="neutral",
                topics=["ambiance"],
                confidence=0.82
            )
        ],
        "google_reviews": [
            MockDataFactory.create_google_places_review(
                rating=5,
                text="Excellent food and service!"
            ),
            MockDataFactory.create_google_places_review(
                rating=2,
                text="Food was cold and service was slow."
            ),
            MockDataFactory.create_google_places_review(
                rating=4,
                text="Good atmosphere and decent food."
            )
        ]
    }


class MockResponseHelpers:
    """Helper methods for working with mock responses."""
    
    @staticmethod
    def create_google_places_mock_with_reviews(review_count: int = 5) -> Dict[str, Any]:
        """Create Google Places response with specified number of reviews."""
        reviews = [
            MockDataFactory.create_google_places_review()
            for _ in range(review_count)
        ]
        
        return MockDataFactory.create_google_places_response(
            reviews=reviews,
            place_id="test-place-123"
        )
    
    @staticmethod
    def create_openai_batch_responses(count: int = 10) -> List[str]:
        """Create batch of OpenAI classification responses."""
        return [
            MockDataFactory.create_openai_classification_response()
            for _ in range(count)
        ]
    
    @staticmethod
    def create_anthropic_conversation_responses(message_count: int = 5) -> List[str]:
        """Create series of Anthropic conversation responses."""
        return [
            MockDataFactory.create_anthropic_advisor_response()
            for _ in range(message_count)
        ]
    
    @staticmethod
    def simulate_api_delay(delay_seconds: float = 0.1):
        """Simulate API response delay for performance testing."""
        import asyncio
        return asyncio.sleep(delay_seconds)
    
    @staticmethod
    def create_error_response_sequence(success_count: int = 3, error_count: int = 2):
        """Create sequence of responses with some errors for resilience testing."""
        responses = []
        
        # Add successful responses
        for _ in range(success_count):
            responses.append(MockAPIResponses.OPENAI_CLASSIFICATION_SUCCESS)
        
        # Add error responses
        for _ in range(error_count):
            responses.append(MockAPIResponses.OPENAI_RATE_LIMIT_ERROR)
        
        return responses


@pytest.fixture
def mock_external_service_failures():
    """Mock external service failure scenarios."""
    return {
        "google_places_timeout": {
            "error": "TimeoutError",
            "message": "Request timed out after 30 seconds"
        },
        "openai_service_unavailable": {
            "error": "ServiceUnavailableError",
            "message": "OpenAI service is temporarily unavailable"
        },
        "anthropic_connection_error": {
            "error": "ConnectionError",
            "message": "Failed to connect to Anthropic API"
        },
        "network_error": {
            "error": "NetworkError",
            "message": "Network connection failed"
        }
    }


@pytest.fixture
def mock_performance_responses():
    """Mock responses optimized for performance testing."""
    return {
        "fast_classification": {
            "response_time_ms": 50,
            "response": MockAPIResponses.OPENAI_CLASSIFICATION_SUCCESS
        },
        "slow_classification": {
            "response_time_ms": 2000,
            "response": MockAPIResponses.OPENAI_CLASSIFICATION_SUCCESS
        },
        "batch_500_reviews": MockResponseHelpers.create_openai_batch_responses(500),
        "large_google_response": MockResponseHelpers.create_google_places_mock_with_reviews(100)
    }