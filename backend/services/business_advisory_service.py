"""
Business advisory service for managing conversations and reports.

This service orchestrates the business advisory functionality including
chat conversations, context management, and weekly report generation.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from backend.ai.base import BusinessAdvisorProtocol, BusinessContext, AdvisorResponse, WeeklyReport
from backend.db.repositories.conversation import ConversationRepository
from backend.db.repositories.business import BusinessRepository
from backend.db.models import Conversation, ConversationMessage
from backend.db.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    WeeklyReportRequest,
    WeeklyReportResponse,
)

logger = logging.getLogger(__name__)


class BusinessAdvisoryService:
    """Service for managing business advisory conversations and reports."""

    def __init__(
        self,
        advisor: BusinessAdvisorProtocol,
        conversation_repo: ConversationRepository,
        business_repo: BusinessRepository,
    ):
        """Initialize business advisory service.

        Args:
            advisor: Business advisor AI service
            conversation_repo: Conversation repository
            business_repo: Business repository
        """
        self._advisor = advisor
        self._conversation_repo = conversation_repo
        self._business_repo = business_repo

    async def send_chat_message(
        self, 
        request: ChatRequest, 
        user_id: UUID
    ) -> ChatResponse:
        """Send a chat message and get AI response.

        Args:
            request: Chat request with message and business context
            user_id: User sending the message

        Returns:
            Chat response from AI advisor

        Raises:
            ValueError: If business not found or user lacks access
            Exception: If AI service fails
        """
        try:
            # Get business context
            business = await self._business_repo.get_by_id(request.business_id)
            if not business:
                raise ValueError(f"Business {request.business_id} not found")

            # Create business context for AI
            business_context = await self._create_business_context(business)

            # Get or create active conversation
            conversation = await self._get_or_create_conversation(
                request.business_id, user_id, request.language
            )

            # Add user message to conversation
            await self._conversation_repo.add_message(
                conversation_id=conversation.id,
                role="user",
                content=request.message
            )

            # Get conversation history for context
            conversation_history = await self._conversation_repo.get_recent_messages_for_context(
                conversation.id, limit=10
            )

            # Generate AI response
            advisor_response = await self._advisor.generate_response(
                message=request.message,
                context=business_context,
                language=request.language,
                conversation_history=conversation_history[:-1]  # Exclude the current message
            )

            # Add AI response to conversation
            await self._conversation_repo.add_message(
                conversation_id=conversation.id,
                role="assistant",
                content=advisor_response.message,
                ai_model=advisor_response.ai_model,
                processing_time_ms=advisor_response.processing_time_ms,
                cost_usd=float(advisor_response.cost_usd)
            )

            logger.info(f"Chat response generated for business {request.business_id}")

            return ChatResponse(
                message=advisor_response.message,
                language=advisor_response.language,
                confidence_score=advisor_response.confidence_score,
                processing_time_ms=advisor_response.processing_time_ms,
                ai_model=advisor_response.ai_model,
                cost_usd=advisor_response.cost_usd,
            )

        except Exception as e:
            logger.error(f"Chat message processing failed: {e}")
            raise

    async def generate_weekly_report(
        self, 
        request: WeeklyReportRequest
    ) -> WeeklyReportResponse:
        """Generate a weekly business report.

        Args:
            request: Weekly report request

        Returns:
            Generated weekly report

        Raises:
            ValueError: If business not found
            Exception: If report generation fails
        """
        try:
            # Get business context
            business = await self._business_repo.get_by_id(request.business_id)
            if not business:
                raise ValueError(f"Business {request.business_id} not found")

            # Create business context for AI
            business_context = await self._create_business_context(business)

            # Generate report
            report = await self._advisor.generate_report(
                business_data=business_context,
                language=request.language,
                report_period_days=request.report_period_days
            )

            logger.info(f"Weekly report generated for business {request.business_id}")

            return WeeklyReportResponse(
                business_id=report.business_id,
                report_period_start=report.report_period_start,
                report_period_end=report.report_period_end,
                summary=report.summary,
                action_items=report.action_items,
                sentiment_analysis=report.sentiment_analysis,
                top_themes=report.top_themes,
                competitor_mentions=report.competitor_mentions,
                language=report.language,
                ai_model=report.ai_model,
            )

        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")
            raise

    async def get_conversation_history(
        self, 
        business_id: UUID, 
        user_id: UUID, 
        limit: int = 10
    ) -> List[ConversationResponse]:
        """Get conversation history for a user and business.

        Args:
            business_id: Business identifier
            user_id: User identifier
            limit: Maximum number of conversations to return

        Returns:
            List of conversations with messages
        """
        try:
            conversations = await self._conversation_repo.get_conversation_history(
                business_id=business_id,
                user_id=user_id,
                limit=limit
            )

            response_conversations = []
            for conv in conversations:
                messages = []
                for msg in conv.messages:
                    messages.append({
                        "id": msg.id,
                        "conversation_id": msg.conversation_id,
                        "role": msg.role,
                        "content": msg.content,
                        "ai_model": msg.ai_model,
                        "processing_time_ms": msg.processing_time_ms,
                        "cost_usd": msg.cost_usd,
                        "created_at": msg.created_at,
                    })

                response_conversations.append(ConversationResponse(
                    id=conv.id,
                    business_id=conv.business_id,
                    user_id=conv.user_id,
                    language=conv.language,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    messages=messages,
                ))

            return response_conversations

        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            raise

    async def get_conversation_stats(self, business_id: UUID) -> Dict[str, Any]:
        """Get conversation statistics for a business.

        Args:
            business_id: Business identifier

        Returns:
            Dictionary with conversation statistics
        """
        try:
            return await self._conversation_repo.get_conversation_stats(business_id)
        except Exception as e:
            logger.error(f"Failed to get conversation stats: {e}")
            raise

    async def cleanup_old_conversations(self, days_to_keep: int = 30) -> int:
        """Clean up old conversations beyond retention period.

        Args:
            days_to_keep: Number of days to keep conversations

        Returns:
            Number of conversations deleted
        """
        try:
            return await self._conversation_repo.cleanup_old_conversations(days_to_keep)
        except Exception as e:
            logger.error(f"Failed to cleanup old conversations: {e}")
            raise

    async def _get_or_create_conversation(
        self, 
        business_id: UUID, 
        user_id: UUID, 
        language: str
    ) -> Conversation:
        """Get active conversation or create a new one.

        Args:
            business_id: Business identifier
            user_id: User identifier
            language: Conversation language

        Returns:
            Active or newly created conversation
        """
        # Try to get active conversation
        conversation = await self._conversation_repo.get_active_conversation(
            business_id=business_id,
            user_id=user_id
        )

        if conversation:
            # Update language if different
            if conversation.language != language:
                conversation.language = language
                await self._conversation_repo.update(conversation)
            return conversation

        # Create new conversation
        return await self._conversation_repo.create_conversation(
            business_id=business_id,
            user_id=user_id,
            language=language
        )

    async def _create_business_context(self, business) -> BusinessContext:
        """Create business context for AI advisor.

        Args:
            business: Business model instance

        Returns:
            BusinessContext for AI advisor
        """
        # Get recent analytics data
        # This would typically come from the analytics service
        # For now, we'll use the basic business data
        
        # TODO: Integrate with analytics service to get:
        # - recent_sentiment_trend
        # - top_topics from recent reviews
        # - competitor_mentions count

        return BusinessContext(
            business_id=str(business.id),
            business_name=business.name,
            avg_rating=float(business.avg_rating) if business.avg_rating else 0.0,
            total_reviews=business.total_reviews or 0,
            recent_sentiment_trend="stable",  # TODO: Calculate from recent reviews
            top_topics=["service", "food_quality"],  # TODO: Get from recent classifications
            competitor_mentions=0,  # TODO: Count from recent reviews
        )