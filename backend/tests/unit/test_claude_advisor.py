"""
Unit tests for Claude Haiku business advisor.

Tests the ClaudeHaikuAdvisor implementation including API calls,
response generation, report generation, and error handling.
"""

import json
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

from backend.ai.claude_advisor import ClaudeHaikuAdvisor
from backend.ai.base import (
    BusinessAdvisorProtocol,
    BusinessContext,
    AdvisorResponse,
    WeeklyReport,
    CostTracker,
)
from backend.tests.unit.test_ai_base_protocols import MockCostTracker

import anthropic


class TestClaudeHaikuAdvisor:
    """Test suite for ClaudeHaikuAdvisor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-anthropic-key"
        self.cost_tracker = MockCostTracker()
        self.advisor = ClaudeHaikuAdvisor(
            api_key=self.api_key,
            cost_tracker=self.cost_tracker,
            model_name="claude-3-haiku-20240307",
            max_retries=2,
            retry_delay=0.1,  # Fast retries for testing
            request_timeout=10,
            max_tokens=1000,
        )

        # Sample business context
        self.business_context = BusinessContext(
            business_id="test-business-123",
            business_name="Test Restaurant",
            avg_rating=4.2,
            total_reviews=150,
            recent_sentiment_trend="positive",
            top_topics=["food_quality", "service"],
            competitor_mentions=2,
        )

    def test_init_creates_advisor_with_config(self):
        """Test advisor initialization with configuration."""
        # Act
        advisor = ClaudeHaikuAdvisor(
            api_key="test-key",
            cost_tracker=self.cost_tracker,
            model_name="custom-model",
            max_retries=5,
            retry_delay=2.0,
            request_timeout=60,
            max_tokens=2000,
        )

        # Assert
        assert advisor._api_key == "test-key"
        assert advisor._model_name == "custom-model"
        assert advisor._max_retries == 5
        assert advisor._retry_delay == 2.0
        assert advisor._request_timeout == 60
        assert advisor._max_tokens == 2000

    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """Test successful response generation."""
        # Arrange
        message = "How is my restaurant performing?"
        language = "en"
        
        mock_response = Mock()
        mock_response.content = [Mock(text="Your restaurant is performing well with a 4.2 rating.")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await self.advisor.generate_response(
                message=message,
                context=self.business_context,
                language=language
            )

            # Assert
            assert isinstance(result, AdvisorResponse)
            assert result.message == "Your restaurant is performing well with a 4.2 rating."
            assert result.language == language
            assert result.ai_model == "claude-3-haiku-20240307"
            assert result.confidence_score == Decimal("0.9")
            assert result.processing_time_ms >= 0  # Allow 0 for fast tests
            assert result.cost_usd > 0

            # Verify API call
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]["model"] == "claude-3-haiku-20240307"
            assert call_args[1]["max_tokens"] == 1000
            assert call_args[1]["temperature"] == 0.1

    @pytest.mark.asyncio
    async def test_generate_response_with_conversation_history(self):
        """Test response generation with conversation history."""
        # Arrange
        message = "What about my service quality?"
        conversation_history = [
            {"role": "user", "content": "How is my restaurant doing?"},
            {"role": "assistant", "content": "Your restaurant is performing well."}
        ]

        mock_response = Mock()
        mock_response.content = [Mock(text="Your service quality is excellent based on recent reviews.")]
        mock_response.usage = Mock(input_tokens=150, output_tokens=75)

        with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await self.advisor.generate_response(
                message=message,
                context=self.business_context,
                language="en",
                conversation_history=conversation_history
            )

            # Assert
            assert isinstance(result, AdvisorResponse)
            assert "service quality" in result.message.lower()

            # Verify conversation history was included
            call_args = mock_create.call_args
            messages = call_args[1]["messages"]
            assert len(messages) == 3  # history + current message
            assert messages[0]["content"] == "How is my restaurant doing?"
            assert messages[1]["content"] == "Your restaurant is performing well."
            assert messages[2]["content"] == "What about my service quality?"

    @pytest.mark.asyncio
    async def test_generate_response_multi_language(self):
        """Test response generation in different languages."""
        # Arrange
        test_cases = [
            ("en", "English"),
            ("de", "German"),
            ("tr", "Turkish"),
            ("ar", "Arabic")
        ]

        for language, language_name in test_cases:
            mock_response = Mock()
            mock_response.content = [Mock(text=f"Response in {language_name}")]
            mock_response.usage = Mock(input_tokens=100, output_tokens=50)

            with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_response

                # Act
                result = await self.advisor.generate_response(
                    message="How is my restaurant?",
                    context=self.business_context,
                    language=language
                )

                # Assert
                assert result.language == language
                assert f"Response in {language_name}" in result.message

                # Verify system prompt includes language instruction
                call_args = mock_create.call_args
                system_prompt = call_args[1]["system"]
                if language == "de":
                    assert "German" in system_prompt
                elif language == "tr":
                    assert "Turkish" in system_prompt
                elif language == "ar":
                    assert "Arabic" in system_prompt

    @pytest.mark.asyncio
    async def test_generate_report_success(self):
        """Test successful weekly report generation."""
        # Arrange
        language = "en"
        report_period_days = 7
        
        mock_report_json = {
            "summary": "Your restaurant had a great week with improved ratings.",
            "action_items": [
                "Continue focusing on food quality",
                "Maintain excellent service standards",
                "Monitor competitor activity"
            ],
            "sentiment_analysis": "Customer sentiment improved by 15% this week.",
            "top_themes": ["food_quality", "service", "ambiance"]
        }

        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(mock_report_json))]
        mock_response.usage = Mock(input_tokens=200, output_tokens=150)

        with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await self.advisor.generate_report(
                business_data=self.business_context,
                language=language,
                report_period_days=report_period_days
            )

            # Assert
            assert isinstance(result, WeeklyReport)
            assert result.business_id == self.business_context.business_id
            assert result.summary == mock_report_json["summary"]
            assert result.action_items == mock_report_json["action_items"]
            assert result.sentiment_analysis == mock_report_json["sentiment_analysis"]
            assert result.top_themes == mock_report_json["top_themes"]
            assert result.competitor_mentions == self.business_context.competitor_mentions
            assert result.language == language
            assert result.ai_model == "claude-3-haiku-20240307"

            # Verify report period
            assert isinstance(result.report_period_start, datetime)
            assert isinstance(result.report_period_end, datetime)
            period_diff = result.report_period_end - result.report_period_start
            assert period_diff.days == report_period_days

    @pytest.mark.asyncio
    async def test_generate_report_malformed_json_fallback(self):
        """Test report generation with malformed JSON response."""
        # Arrange
        mock_response = Mock()
        mock_response.content = [Mock(text="This is not valid JSON content")]
        mock_response.usage = Mock(input_tokens=200, output_tokens=150)

        with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await self.advisor.generate_report(
                business_data=self.business_context,
                language="en"
            )

            # Assert - should use fallback values
            assert isinstance(result, WeeklyReport)
            assert "Unable to generate detailed summary" in result.summary
            assert len(result.action_items) >= 3
            assert "Service quality" in result.top_themes

    @pytest.mark.asyncio
    async def test_cost_tracking_logged(self):
        """Test that cost tracking is properly logged."""
        # Arrange
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            await self.advisor.generate_response(
                message="Test message",
                context=self.business_context,
                language="en"
            )

            # Assert
            assert len(self.cost_tracker.logged_usage) == 1
            log = self.cost_tracker.logged_usage[0]
            assert log["business_id"] == self.business_context.business_id
            assert log["ai_service"] == "claude_haiku"
            assert log["operation"] == "chat"
            assert log["tokens_used"] == 150  # input + output
            assert log["cost_usd"] > 0

    @pytest.mark.asyncio
    async def test_api_retry_on_rate_limit(self):
        """Test retry logic on rate limit errors."""
        # Arrange
        mock_response = Mock()
        mock_response.content = [Mock(text="Success after retry")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        # Create proper Anthropic error
        mock_error_response = Mock()
        mock_error_response.status_code = 429
        rate_limit_error = anthropic.RateLimitError(
            "Rate limit exceeded",
            response=mock_error_response,
            body={"error": {"message": "Rate limit exceeded"}}
        )

        with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            # First call raises rate limit, second succeeds
            mock_create.side_effect = [
                rate_limit_error,
                mock_response
            ]

            # Act
            result = await self.advisor.generate_response(
                message="Test message",
                context=self.business_context,
                language="en"
            )

            # Assert
            assert result.message == "Success after retry"
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_api_retry_exhausted_raises_exception(self):
        """Test that exhausted retries raise the last exception."""
        # Arrange
        mock_error_response = Mock()
        mock_error_response.status_code = 429
        rate_limit_error = anthropic.RateLimitError(
            "Rate limit exceeded",
            response=mock_error_response,
            body={"error": {"message": "Rate limit exceeded"}}
        )

        with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = rate_limit_error

            # Act & Assert
            with pytest.raises(anthropic.RateLimitError):
                await self.advisor.generate_response(
                    message="Test message",
                    context=self.business_context,
                    language="en"
                )

            # Should have tried max_retries times
            assert mock_create.call_count == 2  # max_retries = 2

    @pytest.mark.asyncio
    async def test_api_timeout_retry(self):
        """Test retry logic on API timeout errors."""
        # Arrange
        mock_response = Mock()
        mock_response.content = [Mock(text="Success after timeout retry")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = [
                anthropic.APITimeoutError("Request timeout"),
                mock_response
            ]

            # Act
            result = await self.advisor.generate_response(
                message="Test message",
                context=self.business_context,
                language="en"
            )

            # Assert
            assert result.message == "Success after timeout retry"
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises_immediately(self):
        """Test that non-retryable errors are raised immediately."""
        # Arrange
        mock_error_response = Mock()
        mock_error_response.status_code = 401
        auth_error = anthropic.AuthenticationError(
            "Invalid API key",
            response=mock_error_response,
            body={"error": {"message": "Invalid API key"}}
        )

        with patch.object(self.advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = auth_error

            # Act & Assert
            with pytest.raises(anthropic.AuthenticationError):
                await self.advisor.generate_response(
                    message="Test message",
                    context=self.business_context,
                    language="en"
                )

            # Should not retry on authentication errors
            assert mock_create.call_count == 1

    def test_calculate_cost(self):
        """Test cost calculation based on token usage."""
        # Arrange
        mock_usage = Mock()
        mock_usage.input_tokens = 1000
        mock_usage.output_tokens = 500

        # Act
        cost = self.advisor._calculate_cost(mock_usage)

        # Assert
        expected_input_cost = Decimal("1.0") * self.advisor.INPUT_TOKEN_COST  # 1000/1000 * rate
        expected_output_cost = Decimal("0.5") * self.advisor.OUTPUT_TOKEN_COST  # 500/1000 * rate
        expected_total = expected_input_cost + expected_output_cost
        assert cost == expected_total

    def test_create_advisory_system_prompt_includes_context(self):
        """Test that system prompt includes business context."""
        # Act
        prompt = self.advisor._create_advisory_system_prompt(self.business_context, "en")

        # Assert
        assert self.business_context.business_name in prompt
        assert str(self.business_context.avg_rating) in prompt
        assert str(self.business_context.total_reviews) in prompt
        assert self.business_context.recent_sentiment_trend in prompt
        assert "food_quality" in prompt
        assert "service" in prompt
        assert "Respond in English" in prompt

    def test_create_advisory_system_prompt_language_instructions(self):
        """Test system prompt language instructions for different languages."""
        # Arrange
        test_cases = [
            ("en", "Respond in English"),
            ("de", "Respond in German"),
            ("tr", "Respond in Turkish"),
            ("ar", "Respond in Arabic")
        ]

        for language, expected_instruction in test_cases:
            # Act
            prompt = self.advisor._create_advisory_system_prompt(self.business_context, language)

            # Assert
            assert expected_instruction in prompt

    def test_build_conversation_messages_with_history(self):
        """Test building conversation messages with history."""
        # Arrange
        current_message = "What should I improve?"
        history = [
            {"role": "user", "content": "How is my restaurant?"},
            {"role": "assistant", "content": "Your restaurant is doing well."},
            {"role": "user", "content": "What about service?"},
            {"role": "assistant", "content": "Service quality is excellent."}
        ]

        # Act
        messages = self.advisor._build_conversation_messages(current_message, history)

        # Assert
        assert len(messages) == 5  # 4 history + 1 current
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == current_message
        assert messages[0]["content"] == "How is my restaurant?"

    def test_build_conversation_messages_limits_history(self):
        """Test that conversation history is limited to prevent token overflow."""
        # Arrange
        current_message = "Current question"
        # Create 15 messages (more than the 10 limit)
        history = []
        for i in range(15):
            history.extend([
                {"role": "user", "content": f"User message {i}"},
                {"role": "assistant", "content": f"Assistant response {i}"}
            ])

        # Act
        messages = self.advisor._build_conversation_messages(current_message, history)

        # Assert
        # Should have last 10 messages from history + current message = 11 total
        assert len(messages) == 11
        assert messages[-1]["content"] == current_message
        # Should start with the most recent history (last 10 messages)
        # The history has 30 messages total (15 pairs), so last 10 should start from message 10
        assert "User message 10" in messages[0]["content"]

    def test_build_conversation_messages_no_history(self):
        """Test building messages with no conversation history."""
        # Arrange
        current_message = "First message"

        # Act
        messages = self.advisor._build_conversation_messages(current_message, None)

        # Assert
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == current_message

    def test_parse_report_response_valid_json(self):
        """Test parsing valid JSON report response."""
        # Arrange
        report_data = {
            "summary": "Great week for your restaurant",
            "action_items": ["Improve service", "Monitor quality"],
            "sentiment_analysis": "Positive trend observed",
            "top_themes": ["service", "quality"]
        }
        response_content = json.dumps(report_data)

        # Act
        result = self.advisor._parse_report_response(response_content)

        # Assert
        assert result == report_data

    def test_parse_report_response_json_with_extra_text(self):
        """Test parsing JSON embedded in additional text."""
        # Arrange
        report_data = {
            "summary": "Weekly summary",
            "action_items": ["Action 1", "Action 2"],
            "sentiment_analysis": "Analysis text",
            "top_themes": ["theme1", "theme2"]
        }
        response_content = f"Here is your report:\n{json.dumps(report_data)}\nEnd of report."

        # Act
        result = self.advisor._parse_report_response(response_content)

        # Assert
        assert result == report_data

    def test_parse_report_response_invalid_json_uses_fallback(self):
        """Test that invalid JSON uses fallback values."""
        # Arrange
        response_content = "This is not JSON at all"

        # Act
        result = self.advisor._parse_report_response(response_content)

        # Assert
        assert "Unable to generate detailed summary" in result["summary"]
        assert len(result["action_items"]) >= 3
        assert "Service quality" in result["top_themes"]
        assert isinstance(result["action_items"], list)
        assert isinstance(result["top_themes"], list)