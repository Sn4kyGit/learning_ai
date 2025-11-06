"""
Unit tests for Business Advisory Service.

Tests the BusinessAdvisoryService including conversation management,
chat functionality, and report generation.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime, timedelta

from backend.services.business_advisory_service import BusinessAdvisoryService
from backend.ai.base import BusinessContext, AdvisorResponse, WeeklyReport
from backend.db.schemas import ChatRequest, WeeklyReportRequest
from backend.db.models import Business, Conversation, ConversationMessage


class MockBusinessAdvisor:
    """Mock business advisor for testing."""

    async def generate_response(self, message, context, language="en", conversation_history=None):
        """Mock response generation."""
        return AdvisorResponse(
            message=f"AI response to: {message}",
            language=language,
            confidence_score=Decimal("0.9"),
            processing_time_ms=500,
            ai_model="claude-3-haiku-20240307",
            cost_usd=Decimal("0.001"),
        )

    async def generate_report(self, business_data, language="en", report_period_days=7):
        """Mock report generation."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=report_period_days)
        
        return WeeklyReport(
            business_id=business_data.business_id,
            report_period_start=start_date,
            report_period_end=end_date,
            summary="Weekly performance summary",
            action_items=["Improve service", "Monitor quality", "Engage customers"],
            sentiment_analysis="Positive sentiment trend",
            top_themes=["service", "food_quality"],
            competitor_mentions=2,
            language=language,
            ai_model="claude-3-haiku-20240307",
        )


class MockConversationRepository:
    """Mock conversation repository for testing."""

    def __init__(self):
        self.conversations = {}
        self.messages = {}

    async def get_active_conversation(self, business_id, user_id):
        """Mock get active conversation."""
        key = f"{business_id}_{user_id}"
        return self.conversations.get(key)

    async def create_conversation(self, business_id, user_id, language="en"):
        """Mock create conversation."""
        conversation_id = uuid4()
        conversation = Mock()
        conversation.id = conversation_id
        conversation.business_id = business_id
        conversation.user_id = user_id
        conversation.language = language
        conversation.created_at = datetime.now()
        conversation.updated_at = datetime.now()
        conversation.messages = []
        
        key = f"{business_id}_{user_id}"
        self.conversations[key] = conversation
        return conversation

    async def add_message(self, conversation_id, role, content, ai_model=None, processing_time_ms=None, cost_usd=None):
        """Mock add message."""
        message = Mock()
        message.id = uuid4()
        message.conversation_id = conversation_id
        message.role = role
        message.content = content
        message.ai_model = ai_model
        message.processing_time_ms = processing_time_ms
        message.cost_usd = cost_usd
        message.created_at = datetime.now()
        
        if conversation_id not in self.messages:
            self.messages[conversation_id] = []
        self.messages[conversation_id].append(message)
        
        return message

    async def get_recent_messages_for_context(self, conversation_id, limit=10):
        """Mock get recent messages for context."""
        messages = self.messages.get(conversation_id, [])
        return [{"role": msg.role, "content": msg.content} for msg in messages[-limit:]]

    async def get_conversation_history(self, business_id, user_id, limit=10):
        """Mock get conversation history."""
        key = f"{business_id}_{user_id}"
        conversation = self.conversations.get(key)
        if conversation:
            conversation.messages = self.messages.get(conversation.id, [])
            return [conversation]
        return []

    async def get_conversation_stats(self, business_id):
        """Mock get conversation stats."""
        return {
            "total_conversations": 5,
            "active_conversations": 2,
            "total_messages": 25,
            "avg_messages_per_conversation": 5.0
        }

    async def cleanup_old_conversations(self, days_to_keep=30):
        """Mock cleanup old conversations."""
        return 3  # Number of conversations cleaned up

    async def update(self, conversation):
        """Mock update conversation."""
        # Update the conversation in our mock storage
        key = f"{conversation.business_id}_{conversation.user_id}"
        if key in self.conversations:
            self.conversations[key] = conversation
        return conversation


class MockBusinessRepository:
    """Mock business repository for testing."""

    def __init__(self):
        self.businesses = {}

    async def get_by_id(self, business_id):
        """Mock get business by ID."""
        if business_id in self.businesses:
            return self.businesses[business_id]
        
        # Return None if business not found (don't auto-create)
        return None

    def add_business(self, business_id, name="Test Restaurant", avg_rating=4.2, total_reviews=150):
        """Helper method to add a business for testing."""
        business = Mock()
        business.id = business_id
        business.name = name
        business.avg_rating = Decimal(str(avg_rating))
        business.total_reviews = total_reviews
        self.businesses[business_id] = business
        return business


class TestBusinessAdvisoryService:
    """Test suite for BusinessAdvisoryService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.advisor = MockBusinessAdvisor()
        self.conversation_repo = MockConversationRepository()
        self.business_repo = MockBusinessRepository()
        
        self.service = BusinessAdvisoryService(
            advisor=self.advisor,
            conversation_repo=self.conversation_repo,
            business_repo=self.business_repo,
        )

        # Test data
        self.business_id = uuid4()
        self.user_id = uuid4()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_send_chat_message_creates_new_conversation(self):
        """Test sending chat message creates new conversation."""
        # Arrange
        self.business_repo.add_business(self.business_id)  # Add business first
        request = ChatRequest(
            business_id=self.business_id,
            message="How is my restaurant performing?",
            language="en"
        )

        # Act
        response = await self.service.send_chat_message(request, self.user_id)

        # Assert
        assert response.message == f"AI response to: {request.message}"
        assert response.language == "en"
        assert response.ai_model == "claude-3-haiku-20240307"
        assert response.processing_time_ms == 500
        assert response.cost_usd == Decimal("0.001")

        # Verify conversation was created
        key = f"{self.business_id}_{self.user_id}"
        assert key in self.conversation_repo.conversations

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_send_chat_message_uses_existing_conversation(self):
        """Test sending chat message uses existing active conversation."""
        # Arrange
        self.business_repo.add_business(self.business_id)  # Add business first
        # Create existing conversation
        existing_conversation = await self.conversation_repo.create_conversation(
            self.business_id, self.user_id, "en"
        )
        
        request = ChatRequest(
            business_id=self.business_id,
            message="What about my service quality?",
            language="en"
        )

        # Act
        response = await self.service.send_chat_message(request, self.user_id)

        # Assert
        assert response.message == f"AI response to: {request.message}"
        
        # Verify messages were added to existing conversation
        messages = self.conversation_repo.messages.get(existing_conversation.id, [])
        assert len(messages) == 2  # user message + assistant response
        assert messages[0].role == "user"
        assert messages[0].content == request.message
        assert messages[1].role == "assistant"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_send_chat_message_multi_language(self):
        """Test sending chat message in different languages."""
        # Arrange
        test_cases = ["en", "de", "tr", "ar"]

        for language in test_cases:
            self.business_repo.add_business(self.business_id)  # Add business first
            request = ChatRequest(
                business_id=self.business_id,
                message="Test message",
                language=language
            )

            # Act
            response = await self.service.send_chat_message(request, self.user_id)

            # Assert
            assert response.language == language

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_send_chat_message_business_not_found(self):
        """Test sending chat message when business doesn't exist."""
        # Arrange
        non_existent_business_id = uuid4()
        self.business_repo.businesses.clear()  # Clear all businesses
        
        request = ChatRequest(
            business_id=non_existent_business_id,
            message="Test message",
            language="en"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Business .* not found"):
            await self.service.send_chat_message(request, self.user_id)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_generate_weekly_report_success(self):
        """Test successful weekly report generation."""
        # Arrange
        self.business_repo.add_business(self.business_id)  # Add business first
        request = WeeklyReportRequest(
            business_id=self.business_id,
            language="en",
            report_period_days=7
        )

        # Act
        response = await self.service.generate_weekly_report(request)

        # Assert
        assert response.business_id == self.business_id
        assert response.summary == "Weekly performance summary"
        assert len(response.action_items) == 3
        assert "Improve service" in response.action_items
        assert response.sentiment_analysis == "Positive sentiment trend"
        assert response.top_themes == ["service", "food_quality"]
        assert response.competitor_mentions == 2
        assert response.language == "en"
        assert response.ai_model == "claude-3-haiku-20240307"

        # Verify report period
        assert isinstance(response.report_period_start, datetime)
        assert isinstance(response.report_period_end, datetime)
        period_diff = response.report_period_end - response.report_period_start
        assert period_diff.days == 7

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_generate_weekly_report_multi_language(self):
        """Test weekly report generation in different languages."""
        # Arrange
        test_languages = ["en", "de", "tr", "ar"]

        for language in test_languages:
            self.business_repo.add_business(self.business_id)  # Add business first
            request = WeeklyReportRequest(
                business_id=self.business_id,
                language=language,
                report_period_days=7
            )

            # Act
            response = await self.service.generate_weekly_report(request)

            # Assert
            assert response.language == language

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_generate_weekly_report_custom_period(self):
        """Test weekly report generation with custom period."""
        # Arrange
        self.business_repo.add_business(self.business_id)  # Add business first
        request = WeeklyReportRequest(
            business_id=self.business_id,
            language="en",
            report_period_days=14
        )

        # Act
        response = await self.service.generate_weekly_report(request)

        # Assert
        period_diff = response.report_period_end - response.report_period_start
        assert period_diff.days == 14

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_generate_weekly_report_business_not_found(self):
        """Test weekly report generation when business doesn't exist."""
        # Arrange
        non_existent_business_id = uuid4()
        self.business_repo.businesses.clear()  # Clear all businesses
        
        request = WeeklyReportRequest(
            business_id=non_existent_business_id,
            language="en"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Business .* not found"):
            await self.service.generate_weekly_report(request)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_conversation_history(self):
        """Test getting conversation history."""
        # Arrange
        # Create conversation with messages
        conversation = await self.conversation_repo.create_conversation(
            self.business_id, self.user_id, "en"
        )
        await self.conversation_repo.add_message(
            conversation.id, "user", "Hello"
        )
        await self.conversation_repo.add_message(
            conversation.id, "assistant", "Hi there!"
        )

        # Act
        history = await self.service.get_conversation_history(
            self.business_id, self.user_id, limit=10
        )

        # Assert
        assert len(history) == 1
        conversation_response = history[0]
        assert conversation_response.id == conversation.id
        assert conversation_response.business_id == self.business_id
        assert conversation_response.user_id == self.user_id
        assert conversation_response.language == "en"
        assert len(conversation_response.messages) == 2

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_conversation_stats(self):
        """Test getting conversation statistics."""
        # Act
        stats = await self.service.get_conversation_stats(self.business_id)

        # Assert
        assert stats["total_conversations"] == 5
        assert stats["active_conversations"] == 2
        assert stats["total_messages"] == 25
        assert stats["avg_messages_per_conversation"] == 5.0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_cleanup_old_conversations(self):
        """Test cleaning up old conversations."""
        # Act
        deleted_count = await self.service.cleanup_old_conversations(days_to_keep=30)

        # Assert
        assert deleted_count == 3

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_business_context(self):
        """Test creating business context from business model."""
        # Arrange
        business = Mock()
        business.id = self.business_id
        business.name = "Test Restaurant"
        business.avg_rating = Decimal("4.5")
        business.total_reviews = 200

        # Act
        context = await self.service._create_business_context(business)

        # Assert
        assert context.business_id == str(self.business_id)
        assert context.business_name == "Test Restaurant"
        assert context.avg_rating == 4.5
        assert context.total_reviews == 200
        assert context.recent_sentiment_trend == "stable"  # Default value
        assert "service" in context.top_topics
        assert "food_quality" in context.top_topics
        assert context.competitor_mentions == 0  # Default value

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_business_context_handles_none_values(self):
        """Test creating business context handles None values gracefully."""
        # Arrange
        business = Mock()
        business.id = self.business_id
        business.name = "Test Restaurant"
        business.avg_rating = None
        business.total_reviews = None

        # Act
        context = await self.service._create_business_context(business)

        # Assert
        assert context.avg_rating == 0.0
        assert context.total_reviews == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_or_create_conversation_creates_new(self):
        """Test get or create conversation creates new when none exists."""
        # Act
        conversation = await self.service._get_or_create_conversation(
            self.business_id, self.user_id, "en"
        )

        # Assert
        assert conversation.business_id == self.business_id
        assert conversation.user_id == self.user_id
        assert conversation.language == "en"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_or_create_conversation_returns_existing(self):
        """Test get or create conversation returns existing active conversation."""
        # Arrange
        existing_conversation = await self.conversation_repo.create_conversation(
            self.business_id, self.user_id, "en"
        )

        # Act
        conversation = await self.service._get_or_create_conversation(
            self.business_id, self.user_id, "en"
        )

        # Assert
        assert conversation.id == existing_conversation.id

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_conversation_context_management(self):
        """Test that conversation context is properly managed across messages."""
        # Arrange
        self.business_repo.add_business(self.business_id)  # Add business first
        request1 = ChatRequest(
            business_id=self.business_id,
            message="How is my restaurant doing?",
            language="en"
        )
        request2 = ChatRequest(
            business_id=self.business_id,
            message="What about the service quality?",
            language="en"
        )

        # Act
        response1 = await self.service.send_chat_message(request1, self.user_id)
        response2 = await self.service.send_chat_message(request2, self.user_id)

        # Assert
        assert response1.message == f"AI response to: {request1.message}"
        assert response2.message == f"AI response to: {request2.message}"

        # Verify both messages are in the same conversation
        key = f"{self.business_id}_{self.user_id}"
        conversation = self.conversation_repo.conversations[key]
        messages = self.conversation_repo.messages.get(conversation.id, [])
        assert len(messages) == 4  # 2 user messages + 2 assistant responses