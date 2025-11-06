"""
Custom assertion helpers for business logic validation.
"""

import time
from typing import Any, Dict, List, Optional
from decimal import Decimal

from backend.ai.base import ClassificationResult, AdvisorResponse, WeeklyReport


class TestAssertions:
    """Custom assertion helpers for business logic validation."""
    
    @staticmethod
    def assert_classification_result(
        result: ClassificationResult,
        expected_sentiment: Optional[str] = None,
        expected_topics: Optional[List[str]] = None,
        min_confidence: float = 0.8,
        expected_urgency: Optional[str] = None
    ) -> None:
        """Assert classification result meets expectations."""
        assert isinstance(result, ClassificationResult), f"Expected ClassificationResult, got {type(result)}"
        assert result.confidence_score >= min_confidence, f"Confidence {result.confidence_score} below minimum {min_confidence}"
        
        if expected_sentiment:
            assert result.sentiment == expected_sentiment, f"Expected sentiment {expected_sentiment}, got {result.sentiment}"
        
        if expected_topics:
            missing_topics = [topic for topic in expected_topics if topic not in result.topics]
            assert not missing_topics, f"Missing expected topics: {missing_topics}"
        
        if expected_urgency:
            assert result.urgency == expected_urgency, f"Expected urgency {expected_urgency}, got {result.urgency}"
        
        # Validate required fields
        assert result.sentiment in ["positive", "negative", "neutral"], f"Invalid sentiment: {result.sentiment}"
        assert result.urgency in ["low", "medium", "high"], f"Invalid urgency: {result.urgency}"
        assert isinstance(result.topics, list), f"Topics must be a list, got {type(result.topics)}"
        assert isinstance(result.competitor_mentioned, bool), f"competitor_mentioned must be bool, got {type(result.competitor_mentioned)}"
    
    @staticmethod
    def assert_advisor_response(
        response: AdvisorResponse,
        expected_language: str = "en",
        min_confidence: float = 0.8,
        max_cost: Optional[Decimal] = None
    ) -> None:
        """Assert advisor response meets expectations."""
        assert isinstance(response, AdvisorResponse), f"Expected AdvisorResponse, got {type(response)}"
        assert response.language == expected_language, f"Expected language {expected_language}, got {response.language}"
        assert response.confidence_score >= min_confidence, f"Confidence {response.confidence_score} below minimum {min_confidence}"
        assert len(response.message) > 0, "Response message cannot be empty"
        
        if max_cost:
            assert response.cost_usd <= max_cost, f"Cost {response.cost_usd} exceeds maximum {max_cost}"
    
    @staticmethod
    def assert_weekly_report(
        report: WeeklyReport,
        expected_language: str = "en",
        min_action_items: int = 1
    ) -> None:
        """Assert weekly report meets expectations."""
        assert isinstance(report, WeeklyReport), f"Expected WeeklyReport, got {type(report)}"
        assert report.language == expected_language, f"Expected language {expected_language}, got {report.language}"
        assert len(report.action_items) >= min_action_items, f"Expected at least {min_action_items} action items, got {len(report.action_items)}"
        assert len(report.summary) > 0, "Report summary cannot be empty"
        assert isinstance(report.top_themes, list), f"top_themes must be a list, got {type(report.top_themes)}"
        assert report.competitor_mentions >= 0, f"competitor_mentions must be non-negative, got {report.competitor_mentions}"
    
    @staticmethod
    def assert_response_time(start_time: float, max_seconds: float) -> None:
        """Assert operation completed within time limit."""
        elapsed = time.time() - start_time
        assert elapsed <= max_seconds, f"Operation took {elapsed:.2f}s, expected <{max_seconds}s"
    
    @staticmethod
    def assert_api_response(
        response: Any,
        expected_status: int = 200,
        required_fields: Optional[List[str]] = None,
        forbidden_fields: Optional[List[str]] = None
    ) -> None:
        """Assert API response format and content."""
        assert hasattr(response, 'status_code'), "Response must have status_code attribute"
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
        
        if response.status_code == 200 and required_fields:
            try:
                data = response.json()
            except Exception as e:
                raise AssertionError(f"Failed to parse JSON response: {e}")
            
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            if forbidden_fields:
                for field in forbidden_fields:
                    assert field not in data, f"Forbidden field present: {field}"
    
    @staticmethod
    def assert_database_record(
        record: Any,
        expected_fields: Dict[str, Any],
        exclude_fields: Optional[List[str]] = None
    ) -> None:
        """Assert database record has expected field values."""
        exclude_fields = exclude_fields or ['id', 'created_at', 'updated_at']
        
        for field, expected_value in expected_fields.items():
            if field not in exclude_fields:
                actual_value = getattr(record, field, None)
                assert actual_value == expected_value, f"Field {field}: expected {expected_value}, got {actual_value}"
    
    @staticmethod
    def assert_cost_within_limit(
        actual_cost: Decimal,
        max_cost: Decimal,
        operation_name: str = "operation"
    ) -> None:
        """Assert cost is within acceptable limits."""
        assert isinstance(actual_cost, Decimal), f"Cost must be Decimal, got {type(actual_cost)}"
        assert actual_cost >= 0, f"Cost cannot be negative: {actual_cost}"
        assert actual_cost <= max_cost, f"{operation_name} cost {actual_cost} exceeds limit {max_cost}"
    
    @staticmethod
    def assert_pagination_response(
        response_data: Dict[str, Any],
        expected_total: Optional[int] = None,
        expected_page_size: Optional[int] = None
    ) -> None:
        """Assert pagination response structure."""
        required_fields = ['items', 'total', 'page', 'page_size', 'pages']
        for field in required_fields:
            assert field in response_data, f"Missing pagination field: {field}"
        
        assert isinstance(response_data['items'], list), "items must be a list"
        assert isinstance(response_data['total'], int), "total must be an integer"
        assert isinstance(response_data['page'], int), "page must be an integer"
        assert isinstance(response_data['page_size'], int), "page_size must be an integer"
        assert isinstance(response_data['pages'], int), "pages must be an integer"
        
        if expected_total is not None:
            assert response_data['total'] == expected_total, f"Expected total {expected_total}, got {response_data['total']}"
        
        if expected_page_size is not None:
            assert response_data['page_size'] == expected_page_size, f"Expected page_size {expected_page_size}, got {response_data['page_size']}"
    
    @staticmethod
    def assert_error_response(
        response: Any,
        expected_status: int,
        expected_error_code: Optional[str] = None,
        expected_message_contains: Optional[str] = None
    ) -> None:
        """Assert error response format and content."""
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
        
        try:
            error_data = response.json()
        except Exception as e:
            raise AssertionError(f"Failed to parse error response JSON: {e}")
        
        assert 'error' in error_data or 'detail' in error_data, "Error response must contain error or detail field"
        
        if expected_error_code:
            error_code = error_data.get('error_code') or error_data.get('code')
            assert error_code == expected_error_code, f"Expected error code {expected_error_code}, got {error_code}"
        
        if expected_message_contains:
            message = error_data.get('message') or error_data.get('detail') or str(error_data)
            assert expected_message_contains.lower() in message.lower(), f"Expected message to contain '{expected_message_contains}', got: {message}"