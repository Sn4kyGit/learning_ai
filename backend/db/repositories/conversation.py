"""
Repository for conversation and message management.

This module provides data access methods for conversation history
and message tracking for the business advisory chat system.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Conversation, ConversationMessage
from backend.db.repositories.base import BaseRepository
from backend.db.schemas import ConversationCreate, ConversationResponse

logger = logging.getLogger(__name__)


class ConversationRepository(BaseRepository[Conversation, ConversationCreate, ConversationResponse]):
    """Repository for conversation management."""

    def __init__(self, db_session: AsyncSession):
        """Initialize conversation repository.

        Args:
            db_session: Database session
        """
        super().__init__(Conversation, db_session)

    async def create_conversation(
        self, 
        business_id: UUID, 
        user_id: UUID, 
        language: str = "en"
    ) -> Conversation:
        """Create a new conversation.

        Args:
            business_id: Business identifier
            user_id: User identifier
            language: Conversation language

        Returns:
            Created conversation
        """
        conversation = Conversation(
            business_id=business_id,
            user_id=user_id,
            language=language
        )
        
        self._session.add(conversation)
        await self._session.commit()
        await self._session.refresh(conversation)
        
        logger.info(f"Created conversation {conversation.id} for business {business_id}")
        return conversation

    async def get_conversation_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation by ID with messages.

        Args:
            conversation_id: Conversation identifier

        Returns:
            Conversation with messages or None if not found
        """
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_conversation(
        self, 
        business_id: UUID, 
        user_id: UUID
    ) -> Optional[Conversation]:
        """Get the most recent active conversation for a business and user.

        Args:
            business_id: Business identifier
            user_id: User identifier

        Returns:
            Most recent conversation or None if not found
        """
        # Consider a conversation active if it was updated within the last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                and_(
                    Conversation.business_id == business_id,
                    Conversation.user_id == user_id,
                    Conversation.updated_at >= cutoff_time
                )
            )
            .order_by(desc(Conversation.updated_at))
            .limit(1)
        )
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_conversation_history(
        self, 
        business_id: UUID, 
        user_id: UUID, 
        limit: int = 10
    ) -> List[Conversation]:
        """Get conversation history for a business and user.

        Args:
            business_id: Business identifier
            user_id: User identifier
            limit: Maximum number of conversations to return

        Returns:
            List of conversations ordered by most recent
        """
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                and_(
                    Conversation.business_id == business_id,
                    Conversation.user_id == user_id
                )
            )
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def add_message(
        self, 
        conversation_id: UUID, 
        role: str, 
        content: str,
        ai_model: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        cost_usd: Optional[float] = None
    ) -> ConversationMessage:
        """Add a message to a conversation.

        Args:
            conversation_id: Conversation identifier
            role: Message role (user or assistant)
            content: Message content
            ai_model: AI model used (for assistant messages)
            processing_time_ms: Processing time (for assistant messages)
            cost_usd: Cost in USD (for assistant messages)

        Returns:
            Created message
        """
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            ai_model=ai_model,
            processing_time_ms=processing_time_ms,
            cost_usd=cost_usd
        )
        
        self._session.add(message)
        
        # Update conversation timestamp
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()
        
        await self._session.commit()
        await self._session.refresh(message)
        
        logger.info(f"Added {role} message to conversation {conversation_id}")
        return message

    async def get_conversation_messages(
        self, 
        conversation_id: UUID, 
        limit: int = 50
    ) -> List[ConversationMessage]:
        """Get messages for a conversation.

        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return

        Returns:
            List of messages ordered by creation time
        """
        query = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at)
            .limit(limit)
        )
        
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_recent_messages_for_context(
        self, 
        conversation_id: UUID, 
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Get recent messages formatted for AI context.

        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return

        Returns:
            List of messages formatted for AI API calls
        """
        query = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(desc(ConversationMessage.created_at))
            .limit(limit)
        )
        
        result = await self._session.execute(query)
        messages = list(result.scalars().all())
        
        # Reverse to get chronological order and format for AI
        formatted_messages = []
        for message in reversed(messages):
            formatted_messages.append({
                "role": message.role,
                "content": message.content
            })
        
        return formatted_messages

    async def cleanup_old_conversations(self, days_to_keep: int = 30) -> int:
        """Clean up old conversations beyond retention period.

        Args:
            days_to_keep: Number of days to keep conversations

        Returns:
            Number of conversations deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Get conversations to delete
        query = select(Conversation).where(Conversation.updated_at < cutoff_date)
        result = await self._session.execute(query)
        conversations_to_delete = list(result.scalars().all())
        
        # Delete conversations (messages will be cascade deleted)
        for conversation in conversations_to_delete:
            await self._session.delete(conversation)
        
        await self._session.commit()
        
        deleted_count = len(conversations_to_delete)
        logger.info(f"Cleaned up {deleted_count} old conversations")
        return deleted_count

    async def get_conversation_stats(self, business_id: UUID) -> Dict[str, Any]:
        """Get conversation statistics for a business.

        Args:
            business_id: Business identifier

        Returns:
            Dictionary with conversation statistics
        """
        # Count total conversations
        total_query = (
            select(Conversation)
            .where(Conversation.business_id == business_id)
        )
        total_result = await self._session.execute(total_query)
        total_conversations = len(list(total_result.scalars().all()))
        
        # Count active conversations (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        active_query = (
            select(Conversation)
            .where(
                and_(
                    Conversation.business_id == business_id,
                    Conversation.updated_at >= cutoff_time
                )
            )
        )
        active_result = await self._session.execute(active_query)
        active_conversations = len(list(active_result.scalars().all()))
        
        # Count total messages
        message_query = (
            select(ConversationMessage)
            .join(Conversation)
            .where(Conversation.business_id == business_id)
        )
        message_result = await self._session.execute(message_query)
        total_messages = len(list(message_result.scalars().all()))
        
        return {
            "total_conversations": total_conversations,
            "active_conversations": active_conversations,
            "total_messages": total_messages,
            "avg_messages_per_conversation": total_messages / total_conversations if total_conversations > 0 else 0
        }