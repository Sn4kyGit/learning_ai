"""
Chat API endpoints for Strategic Advisory Agent.

This module provides REST API endpoints for conversational business
advisory interactions using Claude Haiku.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.db.database import get_db_session
from backend.db.repositories.conversation import ConversationRepository
from backend.db.repositories.business import BusinessRepository
from backend.services.business_advisory_service import BusinessAdvisoryService
from backend.services.auth_dependencies import get_current_user
from backend.ai.factory import get_business_advisor
from backend.ai.cost_tracker import DatabaseCostTracker
from backend.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# Request/Response models
class ChatMessage(BaseModel):
    """Chat message model."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    language: Optional[str] = Field("en", description="Preferred response language")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    conversation_id: str
    message_id: str
    language: str
    cost_info: dict
    context_used: bool
    processing_time_ms: int


class ConversationSummary(BaseModel):
    """Conversation summary model."""
    conversation_id: str
    business_id: str
    message_count: int
    created_at: str
    last_message_at: str
    language: str


async def get_advisory_service(db: AsyncSession = Depends(get_db_session)) -> BusinessAdvisoryService:
    """Dependency to get business advisory service."""
    advisor = await get_business_advisor()
    conversation_repo = ConversationRepository(db)
    business_repo = BusinessRepository(db)
    cost_tracker = DatabaseCostTracker(db)
    
    return BusinessAdvisoryService(
        advisor=advisor,
        conversation_repository=conversation_repo,
        business_repository=business_repo,
        cost_tracker=cost_tracker,
    )


@router.post(
    "/{business_id}",
    response_model=ChatResponse,
    responses={
        404: {"model": dict, "description": "Business not found"},
        400: {"model": dict, "description": "Bad Request"},
        429: {"model": dict, "description": "Rate limit exceeded"},
    },
)
async def send_chat_message(
    business_id: UUID,
    message: ChatMessage,
    conversation_id: Optional[UUID] = Query(None, description="Existing conversation ID"),
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> ChatResponse:
    """Send a message to the business advisory agent.
    
    Args:
        business_id: Business ID for context
        message: Chat message
        conversation_id: Optional existing conversation ID
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        ChatResponse: AI advisor response
        
    Raises:
        HTTPException: If chat fails
    """
    try:
        # TODO: Add business access validation
        
        response = await advisory_service.process_chat_message(
            business_id=business_id,
            user_id=current_user.id,
            message=message.message,
            language=message.language or "en",
            conversation_id=conversation_id,
        )
        
        return ChatResponse(
            response=response.response,
            conversation_id=str(response.conversation_id),
            message_id=str(response.message_id),
            language=response.language,
            cost_info=response.cost_info,
            context_used=response.context_used,
            processing_time_ms=response.processing_time_ms,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat message failed for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat message processing failed"
        )


@router.get(
    "/{business_id}/conversations",
    response_model=List[ConversationSummary],
    responses={
        404: {"model": dict, "description": "Business not found"},
    },
)
async def get_conversations(
    business_id: UUID,
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of conversations to return"),
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> List[ConversationSummary]:
    """Get conversation history for a business.
    
    Args:
        business_id: Business ID
        skip: Number of conversations to skip
        limit: Maximum number of conversations to return
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        List[ConversationSummary]: List of conversation summaries
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # TODO: Add business access validation
        
        conversations = await advisory_service.get_conversation_history(
            business_id=business_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )
        
        return [
            ConversationSummary(
                conversation_id=str(conv.conversation_id),
                business_id=str(conv.business_id),
                message_count=conv.message_count,
                created_at=conv.created_at.isoformat(),
                last_message_at=conv.last_message_at.isoformat(),
                language=conv.language,
            )
            for conv in conversations
        ]
        
    except Exception as e:
        logger.error(f"Failed to get conversations for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get(
    "/{business_id}/conversations/{conversation_id}",
    responses={
        404: {"model": dict, "description": "Conversation not found"},
    },
)
async def get_conversation_messages(
    business_id: UUID,
    conversation_id: UUID,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of messages to return"),
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
):
    """Get messages from a specific conversation.
    
    Args:
        business_id: Business ID
        conversation_id: Conversation ID
        skip: Number of messages to skip
        limit: Maximum number of messages to return
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        dict: Conversation messages
        
    Raises:
        HTTPException: If conversation not found
    """
    try:
        # TODO: Add business access validation and conversation ownership check
        
        messages = await advisory_service.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )
        
        return {
            "conversation_id": str(conversation_id),
            "business_id": str(business_id),
            "messages": [
                {
                    "message_id": str(msg.message_id),
                    "role": msg.role,  # user or assistant
                    "content": msg.content,
                    "language": msg.language,
                    "created_at": msg.created_at.isoformat(),
                    "cost_info": msg.cost_info,
                }
                for msg in messages
            ],
            "total_returned": len(messages),
        }
        
    except Exception as e:
        logger.error(f"Failed to get conversation messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation messages"
        )


@router.delete(
    "/{business_id}/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": dict, "description": "Conversation not found"},
    },
)
async def delete_conversation(
    business_id: UUID,
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
) -> None:
    """Delete a conversation and all its messages.
    
    Args:
        business_id: Business ID
        conversation_id: Conversation ID
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Raises:
        HTTPException: If conversation not found or deletion fails
    """
    try:
        # TODO: Add business access validation and conversation ownership check
        
        deleted = await advisory_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conversation deletion failed"
        )


@router.post(
    "/{business_id}/conversations/{conversation_id}/clear",
    responses={
        404: {"model": dict, "description": "Conversation not found"},
    },
)
async def clear_conversation_context(
    business_id: UUID,
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
):
    """Clear conversation context while keeping message history.
    
    This resets the AI's memory of the conversation context while
    preserving the message history for user reference.
    
    Args:
        business_id: Business ID
        conversation_id: Conversation ID
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        dict: Confirmation message
        
    Raises:
        HTTPException: If conversation not found
    """
    try:
        # TODO: Add business access validation and conversation ownership check
        
        cleared = await advisory_service.clear_conversation_context(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        
        if not cleared:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return {
            "message": "Conversation context cleared successfully",
            "conversation_id": str(conversation_id),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear conversation context {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear conversation context"
        )


@router.get(
    "/{business_id}/context-summary",
    responses={
        404: {"model": dict, "description": "Business not found"},
    },
)
async def get_business_context_summary(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
):
    """Get a summary of business context available to the AI advisor.
    
    This endpoint shows what data the AI has access to for providing
    contextual advice about the business.
    
    Args:
        business_id: Business ID
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        dict: Business context summary
        
    Raises:
        HTTPException: If business not found
    """
    try:
        # TODO: Add business access validation
        
        context_summary = await advisory_service.get_business_context_summary(business_id)
        
        return {
            "business_id": str(business_id),
            "context_summary": context_summary,
        }
        
    except Exception as e:
        logger.error(f"Failed to get business context summary for {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business context summary"
        )


@router.get(
    "/usage-stats/{business_id}",
    responses={
        404: {"model": dict, "description": "Business not found"},
    },
)
async def get_chat_usage_stats(
    business_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    advisory_service: BusinessAdvisoryService = Depends(get_advisory_service),
):
    """Get chat usage statistics for a business.
    
    Args:
        business_id: Business ID
        days: Number of days to analyze
        current_user: Current authenticated user
        advisory_service: Business advisory service
        
    Returns:
        dict: Chat usage statistics
        
    Raises:
        HTTPException: If business not found
    """
    try:
        # TODO: Add business access validation
        
        stats = await advisory_service.get_chat_usage_stats(business_id, days)
        
        return {
            "business_id": str(business_id),
            "period_days": days,
            "total_conversations": stats.get("total_conversations", 0),
            "total_messages": stats.get("total_messages", 0),
            "avg_messages_per_conversation": stats.get("avg_messages_per_conversation", 0),
            "total_cost": stats.get("total_cost", 0),
            "avg_cost_per_message": stats.get("avg_cost_per_message", 0),
            "languages_used": stats.get("languages_used", []),
            "most_active_days": stats.get("most_active_days", []),
        }
        
    except Exception as e:
        logger.error(f"Failed to get chat usage stats for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat usage statistics"
        )