"""
GDPR compliance service for data protection and privacy management.

This module provides functionality for GDPR compliance including consent management,
data subject rights (access, deletion, portability), privacy notices, and data breach
notification as required by Requirement 12.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
import logging
import json
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, and_, or_
from fastapi import HTTPException, status

from backend.db.models import (
    User, Business, Review, Classification, Conversation, ConversationMessage,
    ReviewResponse, AIUsageLog, DailyAnalytics
)

logger = logging.getLogger(__name__)


class ConsentType(str, Enum):
    """Types of consent for GDPR compliance."""
    DATA_PROCESSING = "data_processing"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    AI_PROCESSING = "ai_processing"


class DataSubjectRightType(str, Enum):
    """Types of data subject rights under GDPR."""
    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    PORTABILITY = "portability"
    RESTRICTION = "restriction"
    OBJECTION = "objection"


class DataBreachSeverity(str, Enum):
    """Severity levels for data breaches."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GDPRComplianceService:
    """Service for managing GDPR compliance and data protection."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def record_consent(
        self,
        user_id: UUID,
        consent_type: ConsentType,
        granted: bool,
        purpose: str,
        legal_basis: str = "consent",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record user consent for data processing activities.
        
        Args:
            user_id: User providing consent
            consent_type: Type of consent being recorded
            granted: Whether consent was granted or withdrawn
            purpose: Purpose for which consent is being recorded
            legal_basis: Legal basis for processing (default: consent)
            ip_address: IP address of the user (for audit trail)
            user_agent: User agent string (for audit trail)
            
        Returns:
            Dict containing consent record details
            
        Raises:
            HTTPException: If user not found
        """
        # Verify user exists
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        consent_record = {
            "user_id": str(user_id),
            "consent_type": consent_type.value,
            "granted": granted,
            "purpose": purpose,
            "legal_basis": legal_basis,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        # In a real implementation, this would be stored in a dedicated consent table
        # For now, we'll log it and could extend the User model to include consent data
        logger.info(
            f"Consent recorded for user {user_id}: {consent_type.value} = {granted}"
        )

        return consent_record

    async def get_user_consents(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all consent records for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of consent records
        """
        # In a real implementation, this would query a consent table
        # For now, return a placeholder structure
        return [
            {
                "consent_type": ConsentType.DATA_PROCESSING.value,
                "granted": True,
                "purpose": "Business intelligence and review analysis",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "legal_basis": "consent"
            }
        ]

    async def process_data_subject_request(
        self,
        user_id: UUID,
        request_type: DataSubjectRightType,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a data subject rights request under GDPR.
        
        Args:
            user_id: User making the request
            request_type: Type of request (access, erasure, etc.)
            details: Additional details for the request
            
        Returns:
            Dict containing request processing results
            
        Raises:
            HTTPException: If user not found or request invalid
        """
        # Verify user exists
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        request_id = f"dsr_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        if request_type == DataSubjectRightType.ACCESS:
            return await self._process_access_request(user_id, request_id)
        elif request_type == DataSubjectRightType.ERASURE:
            return await self._process_erasure_request(user_id, request_id)
        elif request_type == DataSubjectRightType.PORTABILITY:
            return await self._process_portability_request(user_id, request_id)
        else:
            # For other request types, log and return acknowledgment
            logger.info(f"Data subject request {request_type.value} for user {user_id}")
            return {
                "request_id": request_id,
                "request_type": request_type.value,
                "status": "acknowledged",
                "message": f"Your {request_type.value} request has been received and will be processed within 30 days.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _process_access_request(
        self, user_id: UUID, request_id: str
    ) -> Dict[str, Any]:
        """Process a data access request (Right to Access).
        
        Args:
            user_id: User ID
            request_id: Unique request identifier
            
        Returns:
            Dict containing all user data
        """
        # Get user data
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one()

        # Get user's conversations
        conversations_result = await self.db.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversations = conversations_result.scalars().all()

        # Get conversation messages
        conversation_ids = [conv.id for conv in conversations]
        messages_result = await self.db.execute(
            select(ConversationMessage).where(
                ConversationMessage.conversation_id.in_(conversation_ids)
            )
        )
        messages = messages_result.scalars().all()

        # Get review responses created by user
        responses_result = await self.db.execute(
            select(ReviewResponse).where(ReviewResponse.user_id == user_id)
        )
        responses = responses_result.scalars().all()

        # Compile user data
        user_data = {
            "request_id": request_id,
            "request_type": "access",
            "user_profile": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "language_preference": user.language_preference,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
            "conversations": [
                {
                    "id": str(conv.id),
                    "business_id": str(conv.business_id),
                    "language": conv.language,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                }
                for conv in conversations
            ],
            "messages": [
                {
                    "id": str(msg.id),
                    "conversation_id": str(msg.conversation_id),
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
            "review_responses": [
                {
                    "id": str(resp.id),
                    "review_id": str(resp.review_id),
                    "response_text": resp.response_text,
                    "is_published": resp.is_published,
                    "created_at": resp.created_at.isoformat(),
                }
                for resp in responses
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Data access request processed for user {user_id}")
        return user_data

    async def _process_erasure_request(
        self, user_id: UUID, request_id: str
    ) -> Dict[str, Any]:
        """Process a data erasure request (Right to be Forgotten).
        
        Args:
            user_id: User ID
            request_id: Unique request identifier
            
        Returns:
            Dict containing erasure results
        """
        deleted_records = {
            "conversations": 0,
            "messages": 0,
            "review_responses": 0,
            "user_profile": 0,
        }

        try:
            # Delete conversation messages first (due to foreign key constraints)
            conversations_result = await self.db.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversations = conversations_result.scalars().all()
            conversation_ids = [conv.id for conv in conversations]

            if conversation_ids:
                messages_delete_result = await self.db.execute(
                    delete(ConversationMessage).where(
                        ConversationMessage.conversation_id.in_(conversation_ids)
                    )
                )
                deleted_records["messages"] = messages_delete_result.rowcount

            # Delete conversations
            conversations_delete_result = await self.db.execute(
                delete(Conversation).where(Conversation.user_id == user_id)
            )
            deleted_records["conversations"] = conversations_delete_result.rowcount

            # Delete review responses
            responses_delete_result = await self.db.execute(
                delete(ReviewResponse).where(ReviewResponse.user_id == user_id)
            )
            deleted_records["review_responses"] = responses_delete_result.rowcount

            # Anonymize or delete user profile
            # In practice, we might anonymize rather than delete to maintain referential integrity
            user_delete_result = await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    email=f"deleted_user_{user_id}@anonymized.local",
                    name="Deleted User",
                    password_hash="DELETED",
                )
            )
            deleted_records["user_profile"] = user_delete_result.rowcount

            await self.db.commit()

            logger.info(f"Data erasure completed for user {user_id}: {deleted_records}")

            return {
                "request_id": request_id,
                "request_type": "erasure",
                "status": "completed",
                "deleted_records": deleted_records,
                "message": "Your data has been successfully deleted from our systems.",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing erasure request for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing erasure request"
            )

    async def _process_portability_request(
        self, user_id: UUID, request_id: str
    ) -> Dict[str, Any]:
        """Process a data portability request (Right to Data Portability).
        
        Args:
            user_id: User ID
            request_id: Unique request identifier
            
        Returns:
            Dict containing portable data in structured format
        """
        # Get all user data in a portable format
        access_data = await self._process_access_request(user_id, request_id)
        
        # Convert to portable format (JSON structure suitable for export)
        portable_data = {
            "request_id": request_id,
            "request_type": "portability",
            "export_format": "json",
            "data": access_data,
            "metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "1.0",
                "total_records": (
                    len(access_data.get("conversations", [])) +
                    len(access_data.get("messages", [])) +
                    len(access_data.get("review_responses", []))
                ),
            },
        }

        logger.info(f"Data portability request processed for user {user_id}")
        return portable_data

    async def log_data_breach(
        self,
        severity: DataBreachSeverity,
        description: str,
        affected_data_types: List[str],
        affected_users_count: int,
        discovered_at: datetime,
        contained_at: Optional[datetime] = None,
        root_cause: Optional[str] = None,
        mitigation_steps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Log a data breach incident for GDPR compliance.
        
        Args:
            severity: Severity level of the breach
            description: Description of the breach
            affected_data_types: Types of data affected
            affected_users_count: Number of users affected
            discovered_at: When the breach was discovered
            contained_at: When the breach was contained (if applicable)
            root_cause: Root cause of the breach
            mitigation_steps: Steps taken to mitigate the breach
            
        Returns:
            Dict containing breach record details
        """
        breach_id = f"breach_{int(datetime.now(timezone.utc).timestamp())}"
        
        breach_record = {
            "breach_id": breach_id,
            "severity": severity.value,
            "description": description,
            "affected_data_types": affected_data_types,
            "affected_users_count": affected_users_count,
            "discovered_at": discovered_at.isoformat(),
            "contained_at": contained_at.isoformat() if contained_at else None,
            "root_cause": root_cause,
            "mitigation_steps": mitigation_steps or [],
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "notification_required": severity in [DataBreachSeverity.HIGH, DataBreachSeverity.CRITICAL],
            "authority_notification_deadline": (
                discovered_at + timedelta(hours=72)
            ).isoformat(),
        }

        # In a real implementation, this would be stored in a dedicated breach log table
        logger.critical(f"Data breach logged: {breach_id} - {severity.value}")
        
        # If high severity, trigger immediate notifications
        if severity in [DataBreachSeverity.HIGH, DataBreachSeverity.CRITICAL]:
            await self._trigger_breach_notifications(breach_record)

        return breach_record

    async def _trigger_breach_notifications(self, breach_record: Dict[str, Any]) -> None:
        """Trigger breach notifications to authorities and affected users.
        
        Args:
            breach_record: Breach record details
        """
        # In a real implementation, this would:
        # 1. Send notifications to data protection authorities
        # 2. Send notifications to affected users
        # 3. Update internal incident management systems
        
        logger.critical(
            f"GDPR breach notification triggered for {breach_record['breach_id']}"
        )

    async def get_privacy_notice(self, language: str = "en") -> Dict[str, Any]:
        """Get privacy notice content for GDPR compliance.
        
        Args:
            language: Language code for the privacy notice
            
        Returns:
            Dict containing privacy notice content
        """
        # In a real implementation, this would be stored in a database
        # and support multiple languages
        privacy_notice = {
            "language": language,
            "last_updated": "2024-01-01",
            "version": "1.0",
            "content": {
                "data_controller": {
                    "name": "Local Business Intelligence Bot",
                    "contact": "privacy@businessbot.com",
                    "address": "123 Privacy Street, Data City, DC 12345",
                },
                "data_processing_purposes": [
                    "Business intelligence and analytics",
                    "Review sentiment analysis",
                    "AI-powered business recommendations",
                    "User account management",
                    "Service improvement",
                ],
                "legal_basis": [
                    "Consent (Article 6(1)(a) GDPR)",
                    "Legitimate interests (Article 6(1)(f) GDPR)",
                    "Contract performance (Article 6(1)(b) GDPR)",
                ],
                "data_types_collected": [
                    "Account information (name, email)",
                    "Business information",
                    "Review data (publicly available)",
                    "Usage analytics",
                    "Communication records",
                ],
                "data_retention": {
                    "user_accounts": "Until account deletion requested",
                    "review_data": "As long as business account is active",
                    "analytics_data": "12 months",
                    "conversation_history": "30 days",
                },
                "user_rights": [
                    "Right to access your data",
                    "Right to rectification",
                    "Right to erasure (right to be forgotten)",
                    "Right to data portability",
                    "Right to restrict processing",
                    "Right to object to processing",
                ],
                "data_sharing": [
                    "We do not sell your personal data",
                    "Data may be shared with AI service providers (OpenAI, Anthropic) for processing",
                    "Data may be shared with authorities if legally required",
                ],
                "security_measures": [
                    "Encryption in transit and at rest",
                    "Access controls and authentication",
                    "Regular security audits",
                    "Data breach response procedures",
                ],
            },
        }

        return privacy_notice

    async def validate_data_minimization(self, business_id: UUID) -> Dict[str, Any]:
        """Validate that data collection follows GDPR data minimization principles.
        
        Args:
            business_id: Business ID to validate
            
        Returns:
            Dict containing validation results
        """
        validation_results = {
            "business_id": str(business_id),
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "compliant": True,
            "issues": [],
            "recommendations": [],
        }

        # Check review data retention
        old_reviews_result = await self.db.execute(
            select(Review).where(
                and_(
                    Review.business_id == business_id,
                    Review.created_at < datetime.now(timezone.utc) - timedelta(days=365 * 2)
                )
            )
        )
        old_reviews_count = len(old_reviews_result.scalars().all())

        if old_reviews_count > 0:
            validation_results["issues"].append(
                f"Found {old_reviews_count} reviews older than 2 years"
            )
            validation_results["recommendations"].append(
                "Consider archiving or anonymizing old review data"
            )

        # Check conversation data retention
        old_conversations_result = await self.db.execute(
            select(Conversation).where(
                and_(
                    Conversation.business_id == business_id,
                    Conversation.updated_at < datetime.now(timezone.utc) - timedelta(days=30)
                )
            )
        )
        old_conversations_count = len(old_conversations_result.scalars().all())

        if old_conversations_count > 0:
            validation_results["issues"].append(
                f"Found {old_conversations_count} conversations older than 30 days"
            )
            validation_results["recommendations"].append(
                "Automatically delete conversations older than 30 days"
            )

        validation_results["compliant"] = len(validation_results["issues"]) == 0

        logger.info(
            f"Data minimization validation for business {business_id}: "
            f"{'compliant' if validation_results['compliant'] else 'issues found'}"
        )

        return validation_results

    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired data according to retention policies.
        
        Returns:
            Dict containing cleanup statistics
        """
        cleanup_stats = {
            "conversations_deleted": 0,
            "messages_deleted": 0,
            "old_analytics_deleted": 0,
        }

        try:
            # Delete conversations older than 30 days
            old_conversations_result = await self.db.execute(
                select(Conversation).where(
                    Conversation.updated_at < datetime.now(timezone.utc) - timedelta(days=30)
                )
            )
            old_conversations = old_conversations_result.scalars().all()
            conversation_ids = [conv.id for conv in old_conversations]

            if conversation_ids:
                # Delete messages first
                messages_delete_result = await self.db.execute(
                    delete(ConversationMessage).where(
                        ConversationMessage.conversation_id.in_(conversation_ids)
                    )
                )
                cleanup_stats["messages_deleted"] = messages_delete_result.rowcount

                # Delete conversations
                conversations_delete_result = await self.db.execute(
                    delete(Conversation).where(
                        Conversation.updated_at < datetime.now(timezone.utc) - timedelta(days=30)
                    )
                )
                cleanup_stats["conversations_deleted"] = conversations_delete_result.rowcount

            # Delete old analytics data (older than 12 months)
            old_analytics_delete_result = await self.db.execute(
                delete(DailyAnalytics).where(
                    DailyAnalytics.date < datetime.now(timezone.utc).date() - timedelta(days=365)
                )
            )
            cleanup_stats["old_analytics_deleted"] = old_analytics_delete_result.rowcount

            await self.db.commit()

            logger.info(f"Data cleanup completed: {cleanup_stats}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error during data cleanup: {e}")
            raise

        return cleanup_stats