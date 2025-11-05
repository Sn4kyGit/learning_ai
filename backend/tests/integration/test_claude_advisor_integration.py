"""
Integration tests for Claude Haiku business advisor.

Tests the ClaudeHaikuAdvisor with real API interactions (mocked)
and database integration for cost tracking.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from backend.ai.claude_advisor import ClaudeHaikuAdvisor
from backend.ai.base import BusinessContext
from backend.ai.cost_tracker import DatabaseCostTracker
from backend.db.models import AIUsageLog, MonthlyCostSummary

import anthropic


class TestClaudeAdvisorIntegration:
    """Integration test suite for Claude Haiku advisor."""

    @pytest.fixture
    async def cost_tracker(self, test_db_session):
        """Create cost tracker with database session."""
        return DatabaseCostTracker(
            db_session=test_db_session,
            default_cost_limit=Decimal("100.0")
        )

    @pytest.fixture
    def business_context(self):
        """Create business context for testing."""
        return BusinessContext(
            business_id="test-business-123",
            business_name="Integration Test Restaurant",
            avg_rating=4.3,
            total_reviews=200,
            recent_sentiment_trend="improving",
            top_topics=["food_quality", "service", "ambiance"],
            competitor_mentions=1,
        )

    @pytest.fixture
    def advisor(self, cost_tracker):
        """Create Claude advisor with cost tracker."""
        return ClaudeHaikuAdvisor(
            api_key="test-anthropic-key",
            cost_tracker=cost_tracker,
            model_name="claude-3-haiku-20240307",
            max_retries=2,
            retry_delay=0.1,
            request_timeout=10,
            max_tokens=1000,
        )

    @pytest.mark.asyncio
    async def test_generate_response_with_cost_tracking(
        self, advisor, business_context, test_db_session
    ):
        """Test response generation with database cost tracking."""
        # Arrange
        mock_response = Mock()
        mock_response.content = [Mock(text="Your restaurant is performing excellently with strong customer satisfaction.")]
        mock_response.usage = Mock(input_tokens=150, output_tokens=75)

        with patch.object(advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await advisor.generate_response(
                message="How is my restaurant performing overall?",
                context=business_context,
                language="en"
            )

            # Assert
            assert result.message == "Your restaurant is performing excellently with strong customer satisfaction."
            assert result.cost_usd > 0

            # Verify cost tracking in database
            usage_logs = test_db_session.query(AIUsageLog).filter_by(
                business_id=business_context.business_id
            ).all()
            
            assert len(usage_logs) == 1
            log = usage_logs[0]
            assert log.ai_service == "claude_haiku"
            assert log.operation == "chat"
            assert log.tokens_used == 225  # 150 + 75
            assert log.cost_usd == result.cost_usd

    @pytest.mark.asyncio
    async def test_generate_report_with_cost_tracking(
        self, advisor, business_context, test_db_session
    ):
        """Test report generation with database cost tracking."""
        # Arrange
        mock_report_json = {
            "summary": "Your restaurant showed strong performance this week with improved customer satisfaction.",
            "action_items": [
                "Continue focusing on food quality improvements",
                "Maintain excellent service standards during peak hours",
                "Consider expanding popular menu items"
            ],
            "sentiment_analysis": "Customer sentiment improved by 12% this week, with particular praise for food quality.",
            "top_themes": ["food_quality", "service", "value"]
        }

        mock_response = Mock()
        mock_response.content = [Mock(text=f"Here's your report: {mock_report_json}")]
        mock_response.usage = Mock(input_tokens=300, output_tokens=200)

        with patch.object(advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await advisor.generate_report(
                business_data=business_context,
                language="en",
                report_period_days=7
            )

            # Assert
            assert result.business_id == business_context.business_id
            assert "strong performance" in result.summary
            assert len(result.action_items) == 3
            assert "food quality" in result.sentiment_analysis

            # Verify cost tracking in database
            usage_logs = test_db_session.query(AIUsageLog).filter_by(
                business_id=business_context.business_id,
                operation="report"
            ).all()
            
            assert len(usage_logs) == 1
            log = usage_logs[0]
            assert log.ai_service == "claude_haiku"
            assert log.tokens_used == 500  # 300 + 200

    @pytest.mark.asyncio
    async def test_multi_language_response_generation(
        self, advisor, business_context, test_db_session
    ):
        """Test response generation in multiple languages."""
        # Arrange
        test_cases = [
            ("en", "Your restaurant is performing well"),
            ("de", "Ihr Restaurant läuft sehr gut"),
            ("tr", "Restoranınız çok iyi performans gösteriyor"),
            ("ar", "مطعمك يعمل بشكل جيد جداً")
        ]

        for language, expected_response in test_cases:
            mock_response = Mock()
            mock_response.content = [Mock(text=expected_response)]
            mock_response.usage = Mock(input_tokens=100, output_tokens=50)

            with patch.object(advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_response

                # Act
                result = await advisor.generate_response(
                    message="How is my restaurant doing?",
                    context=business_context,
                    language=language
                )

                # Assert
                assert result.language == language
                assert result.message == expected_response

                # Verify system prompt includes correct language instruction
                call_args = mock_create.call_args
                system_prompt = call_args[1]["system"]
                
                if language == "de":
                    assert "German" in system_prompt
                elif language == "tr":
                    assert "Turkish" in system_prompt
                elif language == "ar":
                    assert "Arabic" in system_prompt
                else:
                    assert "English" in system_prompt

    @pytest.mark.asyncio
    async def test_conversation_context_integration(
        self, advisor, business_context
    ):
        """Test conversation context management in responses."""
        # Arrange
        conversation_history = [
            {"role": "user", "content": "What's my average rating?"},
            {"role": "assistant", "content": "Your average rating is 4.3 stars."},
            {"role": "user", "content": "How many reviews do I have?"},
            {"role": "assistant", "content": "You have 200 total reviews."}
        ]

        mock_response = Mock()
        mock_response.content = [Mock(text="Based on our previous discussion about your 4.3-star rating and 200 reviews, I recommend focusing on service improvements.")]
        mock_response.usage = Mock(input_tokens=200, output_tokens=100)

        with patch.object(advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await advisor.generate_response(
                message="What should I focus on improving?",
                context=business_context,
                language="en",
                conversation_history=conversation_history
            )

            # Assert
            assert "4.3-star rating" in result.message
            assert "200 reviews" in result.message

            # Verify conversation history was included in API call
            call_args = mock_create.call_args
            messages = call_args[1]["messages"]
            assert len(messages) == 5  # 4 history + 1 current
            assert messages[0]["content"] == "What's my average rating?"
            assert messages[-1]["content"] == "What should I focus on improving?"

    @pytest.mark.asyncio
    async def test_api_error_handling_with_retries(
        self, advisor, business_context
    ):
        """Test API error handling and retry logic."""
        # Arrange
        mock_success_response = Mock()
        mock_success_response.content = [Mock(text="Success after retry")]
        mock_success_response.usage = Mock(input_tokens=100, output_tokens=50)

        with patch.object(advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            # First call fails with rate limit, second succeeds
            mock_create.side_effect = [
                anthropic.RateLimitError("Rate limit exceeded"),
                mock_success_response
            ]

            # Act
            result = await advisor.generate_response(
                message="Test message",
                context=business_context,
                language="en"
            )

            # Assert
            assert result.message == "Success after retry"
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_cost_limit_integration(
        self, advisor, business_context, test_db_session
    ):
        """Test integration with cost limit checking."""
        # Arrange
        # Set a low cost limit
        advisor._cost_tracker._default_cost_limit = Decimal("0.001")

        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=1000)  # High token usage

        with patch.object(advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await advisor.generate_response(
                message="Test message",
                context=business_context,
                language="en"
            )

            # Assert
            assert result.cost_usd > Decimal("0.001")  # Should exceed limit

            # Check if cost limit was exceeded
            within_limit = await advisor._cost_tracker.check_cost_limit(business_context.business_id)
            assert not within_limit  # Should be over limit

    @pytest.mark.asyncio
    async def test_monthly_cost_summary_update(
        self, advisor, business_context, test_db_session
    ):
        """Test that monthly cost summaries are updated."""
        # Arrange
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        with patch.object(advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            await advisor.generate_response(
                message="Test message",
                context=business_context,
                language="en"
            )

            # Force cost summary update
            await advisor._cost_tracker._update_monthly_summary(business_context.business_id)

            # Assert
            summaries = test_db_session.query(MonthlyCostSummary).filter_by(
                business_id=business_context.business_id
            ).all()
            
            assert len(summaries) == 1
            summary = summaries[0]
            assert summary.chat_cost > 0
            assert summary.total_cost > 0

    @pytest.mark.asyncio
    async def test_business_context_integration(
        self, advisor, business_context
    ):
        """Test that business context is properly integrated into responses."""
        # Arrange
        mock_response = Mock()
        mock_response.content = [Mock(text=f"Based on your {business_context.avg_rating} rating and {business_context.total_reviews} reviews, I recommend...")]
        mock_response.usage = Mock(input_tokens=150, output_tokens=100)

        with patch.object(advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await advisor.generate_response(
                message="What do you recommend?",
                context=business_context,
                language="en"
            )

            # Assert
            assert str(business_context.avg_rating) in result.message
            assert str(business_context.total_reviews) in result.message

            # Verify business context was included in system prompt
            call_args = mock_create.call_args
            system_prompt = call_args[1]["system"]
            assert business_context.business_name in system_prompt
            assert str(business_context.avg_rating) in system_prompt
            assert business_context.recent_sentiment_trend in system_prompt
            assert "food_quality" in system_prompt

    @pytest.mark.asyncio
    async def test_report_generation_with_business_data(
        self, advisor, business_context
    ):
        """Test report generation includes business-specific data."""
        # Arrange
        mock_response = Mock()
        mock_response.content = [Mock(text='{"summary": "Great performance", "action_items": ["Keep it up"], "sentiment_analysis": "Positive", "top_themes": ["quality"]}')]
        mock_response.usage = Mock(input_tokens=200, output_tokens=150)

        with patch.object(advisor._client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            # Act
            result = await advisor.generate_report(
                business_data=business_context,
                language="en",
                report_period_days=14
            )

            # Assert
            assert result.business_id == business_context.business_id
            assert result.competitor_mentions == business_context.competitor_mentions

            # Verify business data was included in user prompt
            call_args = mock_create.call_args
            user_message = call_args[1]["messages"][0]["content"]
            assert business_context.business_name in user_message
            assert str(business_context.avg_rating) in user_message
            assert business_context.recent_sentiment_trend in user_message