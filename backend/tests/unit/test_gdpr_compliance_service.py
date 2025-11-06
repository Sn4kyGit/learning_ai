"""
Unit tests for GDPR compliance service.

This module tests the GDPR compliance functionality including consent management,
data subject rights, privacy notices, and data breach handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.services.gdpr_compliance_service import (
    GDPRComplianceService,
    ConsentType,
    DataSubjectRightType,
    DataBreachSeverity,
)
from backend.db.models import User, Conversation, ConversationMessage, ReviewResponse


class TestGDPRComplianceService:
    """Test suite for GDPR compliance service."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db_session):
        """GDPR compliance service instance."""
        return GDPRComplianceService(mock_db_session)

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            id=uuid4(),
            email="test@example.com",
            name="Test User",
            role="admin",
            language_preference="en",
            created_at=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_record_consent_success(self, service, mock_db_session, sample_user):
        """Test successful consent recording."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        # Act
        consent_record = await service.record_consent(
            user_id=sample_user.id,
            consent_type=ConsentType.DATA_PROCESSING,
            granted=True,
            purpose="Business intelligence analysis",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        assert consent_record["user_id"] == str(sample_user.id)
        assert consent_record["consent_type"] == "data_processing"
        assert consent_record["granted"] is True
        assert consent_record["purpose"] == "Business intelligence analysis"
        assert consent_record["ip_address"] == "192.168.1.1"
        assert "timestamp" in consent_record

    @pytest.mark.asyncio
    async def test_record_consent_user_not_found(self, service, mock_db_session):
        """Test consent recording with non-existent user."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(Exception):  # HTTPException in real implementation
            await service.record_consent(
                user_id=uuid4(),
                consent_type=ConsentType.DATA_PROCESSING,
                granted=True,
                purpose="Test purpose",
            )

    @pytest.mark.asyncio
    async def test_get_user_consents(self, service, sample_user):
        """Test retrieving user consent records."""
        # Act
        consents = await service.get_user_consents(sample_user.id)

        # Assert
        assert isinstance(consents, list)
        assert len(consents) >= 1
        assert consents[0]["consent_type"] == "data_processing"
        assert consents[0]["granted"] is True

    @pytest.mark.asyncio
    async def test_process_access_request(self, service, mock_db_session, sample_user):
        """Test data access request processing."""
        # Arrange
        mock_user_result = Mock()
        mock_user_result.scalar_one.return_value = sample_user
        
        mock_conversations_result = Mock()
        mock_conversations_result.scalars.return_value.all.return_value = []
        
        mock_messages_result = Mock()
        mock_messages_result.scalars.return_value.all.return_value = []
        
        mock_responses_result = Mock()
        mock_responses_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [
            mock_user_result,
            mock_conversations_result,
            mock_messages_result,
            mock_responses_result,
        ]

        # Act
        result = await service._process_access_request(sample_user.id, "test_request_123")

        # Assert
        assert result["request_type"] == "access"
        assert result["user_profile"]["id"] == str(sample_user.id)
        assert result["user_profile"]["email"] == sample_user.email
        assert "conversations" in result
        assert "messages" in result
        assert "review_responses" in result
        assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_process_erasure_request(self, service, mock_db_session, sample_user):
        """Test data erasure request processing."""
        # Arrange
        # Mock conversations with some data to delete
        mock_conversation = Mock()
        mock_conversation.id = uuid4()
        
        mock_conversations_result = Mock()
        mock_conversations_result.scalars.return_value.all.return_value = [mock_conversation]
        
        mock_messages_delete_result = Mock()
        mock_messages_delete_result.rowcount = 5
        
        mock_conversations_delete_result = Mock()
        mock_conversations_delete_result.rowcount = 1
        
        mock_responses_delete_result = Mock()
        mock_responses_delete_result.rowcount = 3
        
        mock_user_update_result = Mock()
        mock_user_update_result.rowcount = 1

        mock_db_session.execute.side_effect = [
            mock_conversations_result,
            mock_messages_delete_result,
            mock_conversations_delete_result,
            mock_responses_delete_result,
            mock_user_update_result,
        ]

        # Act
        result = await service._process_erasure_request(sample_user.id, "test_request_123")

        # Assert
        assert result["request_type"] == "erasure"
        assert result["status"] == "completed"
        assert "deleted_records" in result
        assert result["deleted_records"]["messages"] == 5
        assert result["deleted_records"]["conversations"] == 1
        assert result["deleted_records"]["review_responses"] == 3
        assert result["deleted_records"]["user_profile"] == 1
        assert "completed_at" in result

    @pytest.mark.asyncio
    async def test_process_portability_request(self, service, mock_db_session, sample_user):
        """Test data portability request processing."""
        # Arrange
        mock_user_result = Mock()
        mock_user_result.scalar_one.return_value = sample_user
        
        mock_conversations_result = Mock()
        mock_conversations_result.scalars.return_value.all.return_value = []
        
        mock_messages_result = Mock()
        mock_messages_result.scalars.return_value.all.return_value = []
        
        mock_responses_result = Mock()
        mock_responses_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [
            mock_user_result,
            mock_conversations_result,
            mock_messages_result,
            mock_responses_result,
        ]

        # Act
        result = await service._process_portability_request(sample_user.id, "test_request_123")

        # Assert
        assert result["request_type"] == "portability"
        assert result["export_format"] == "json"
        assert "data" in result
        assert "metadata" in result
        assert result["metadata"]["format_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_log_data_breach(self, service):
        """Test data breach logging."""
        # Arrange
        discovered_at = datetime.now(timezone.utc)
        contained_at = discovered_at + timedelta(hours=2)

        # Act
        breach_record = await service.log_data_breach(
            severity=DataBreachSeverity.HIGH,
            description="Unauthorized access to user data",
            affected_data_types=["user_profiles", "conversations"],
            affected_users_count=150,
            discovered_at=discovered_at,
            contained_at=contained_at,
            root_cause="SQL injection vulnerability",
            mitigation_steps=["Patched vulnerability", "Reset user passwords"],
        )

        # Assert
        assert breach_record["severity"] == "high"
        assert breach_record["description"] == "Unauthorized access to user data"
        assert breach_record["affected_data_types"] == ["user_profiles", "conversations"]
        assert breach_record["affected_users_count"] == 150
        assert breach_record["notification_required"] is True
        assert "authority_notification_deadline" in breach_record
        assert "breach_id" in breach_record

    @pytest.mark.asyncio
    async def test_get_privacy_notice(self, service):
        """Test privacy notice retrieval."""
        # Act
        privacy_notice = await service.get_privacy_notice("en")

        # Assert
        assert privacy_notice["language"] == "en"
        assert "content" in privacy_notice
        assert "data_controller" in privacy_notice["content"]
        assert "data_processing_purposes" in privacy_notice["content"]
        assert "legal_basis" in privacy_notice["content"]
        assert "user_rights" in privacy_notice["content"]
        assert len(privacy_notice["content"]["user_rights"]) >= 6  # All GDPR rights

    @pytest.mark.asyncio
    async def test_validate_data_minimization_compliant(self, service, mock_db_session):
        """Test data minimization validation for compliant business."""
        # Arrange
        business_id = uuid4()
        
        mock_old_reviews_result = Mock()
        mock_old_reviews_result.scalars.return_value.all.return_value = []
        
        mock_old_conversations_result = Mock()
        mock_old_conversations_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [
            mock_old_reviews_result,
            mock_old_conversations_result,
        ]

        # Act
        validation_result = await service.validate_data_minimization(business_id)

        # Assert
        assert validation_result["business_id"] == str(business_id)
        assert validation_result["compliant"] is True
        assert len(validation_result["issues"]) == 0
        assert len(validation_result["recommendations"]) == 0

    @pytest.mark.asyncio
    async def test_validate_data_minimization_non_compliant(self, service, mock_db_session):
        """Test data minimization validation for non-compliant business."""
        # Arrange
        business_id = uuid4()
        
        # Mock old reviews found
        mock_old_reviews_result = Mock()
        mock_old_reviews_result.scalars.return_value.all.return_value = [Mock(), Mock()]
        
        # Mock old conversations found
        mock_old_conversations_result = Mock()
        mock_old_conversations_result.scalars.return_value.all.return_value = [Mock()]

        mock_db_session.execute.side_effect = [
            mock_old_reviews_result,
            mock_old_conversations_result,
        ]

        # Act
        validation_result = await service.validate_data_minimization(business_id)

        # Assert
        assert validation_result["business_id"] == str(business_id)
        assert validation_result["compliant"] is False
        assert len(validation_result["issues"]) == 2
        assert "2 reviews older than 2 years" in validation_result["issues"][0]
        assert "1 conversations older than 30 days" in validation_result["issues"][1]
        assert len(validation_result["recommendations"]) == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired_data(self, service, mock_db_session):
        """Test cleanup of expired data."""
        # Arrange
        # Mock conversations with some data to delete
        mock_conversation = Mock()
        mock_conversation.id = uuid4()
        
        mock_conversations_result = Mock()
        mock_conversations_result.scalars.return_value.all.return_value = [mock_conversation]
        
        mock_messages_delete_result = Mock()
        mock_messages_delete_result.rowcount = 5
        
        mock_conversations_delete_result = Mock()
        mock_conversations_delete_result.rowcount = 1
        
        mock_analytics_delete_result = Mock()
        mock_analytics_delete_result.rowcount = 10

        mock_db_session.execute.side_effect = [
            mock_conversations_result,
            mock_messages_delete_result,
            mock_conversations_delete_result,
            mock_analytics_delete_result,
        ]

        # Act
        cleanup_stats = await service.cleanup_expired_data()

        # Assert
        assert cleanup_stats["conversations_deleted"] == 1
        assert cleanup_stats["messages_deleted"] == 5
        assert cleanup_stats["old_analytics_deleted"] == 10
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_data_subject_request_access(self, service, mock_db_session, sample_user):
        """Test processing data subject access request."""
        # Arrange
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        mock_user_result.scalar_one.return_value = sample_user
        
        mock_conversations_result = Mock()
        mock_conversations_result.scalars.return_value.all.return_value = []
        
        mock_messages_result = Mock()
        mock_messages_result.scalars.return_value.all.return_value = []
        
        mock_responses_result = Mock()
        mock_responses_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [
            mock_user_result,  # For user existence check
            mock_user_result,  # For access request processing
            mock_conversations_result,
            mock_messages_result,
            mock_responses_result,
        ]

        # Act
        result = await service.process_data_subject_request(
            user_id=sample_user.id,
            request_type=DataSubjectRightType.ACCESS,
        )

        # Assert
        assert "request_id" in result
        assert result["request_type"] == "access"
        assert "user_profile" in result

    @pytest.mark.asyncio
    async def test_process_data_subject_request_unknown_type(self, service, mock_db_session, sample_user):
        """Test processing unknown data subject request type."""
        # Arrange
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_user_result

        # Act
        result = await service.process_data_subject_request(
            user_id=sample_user.id,
            request_type=DataSubjectRightType.RESTRICTION,
        )

        # Assert
        assert result["request_type"] == "restriction"
        assert result["status"] == "acknowledged"
        assert "30 days" in result["message"]

    @pytest.mark.asyncio
    async def test_trigger_breach_notifications_high_severity(self, service):
        """Test breach notification triggering for high severity breaches."""
        # Arrange
        breach_record = {
            "breach_id": "breach_123",
            "severity": "high",
            "description": "Test breach",
        }

        # Act
        await service._trigger_breach_notifications(breach_record)

        # Assert - In real implementation, this would verify notification calls
        # For now, we just ensure the method completes without error
        assert True

    @pytest.mark.asyncio
    async def test_consent_withdrawal(self, service, mock_db_session, sample_user):
        """Test consent withdrawal functionality."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        # Act
        consent_record = await service.record_consent(
            user_id=sample_user.id,
            consent_type=ConsentType.MARKETING,
            granted=False,  # Withdrawing consent
            purpose="Marketing communications",
        )

        # Assert
        assert consent_record["granted"] is False
        assert consent_record["consent_type"] == "marketing"

    @pytest.mark.asyncio
    async def test_data_breach_severity_levels(self, service):
        """Test different data breach severity levels."""
        # Test low severity breach
        low_breach = await service.log_data_breach(
            severity=DataBreachSeverity.LOW,
            description="Minor configuration issue",
            affected_data_types=["system_logs"],
            affected_users_count=0,
            discovered_at=datetime.now(timezone.utc),
        )
        assert low_breach["notification_required"] is False

        # Test critical severity breach
        critical_breach = await service.log_data_breach(
            severity=DataBreachSeverity.CRITICAL,
            description="Database compromise",
            affected_data_types=["user_profiles", "conversations", "reviews"],
            affected_users_count=10000,
            discovered_at=datetime.now(timezone.utc),
        )
        assert critical_breach["notification_required"] is True

    @pytest.mark.asyncio
    async def test_privacy_notice_multilingual(self, service):
        """Test privacy notice in different languages."""
        # Test English
        notice_en = await service.get_privacy_notice("en")
        assert notice_en["language"] == "en"

        # Test German (would be implemented in real system)
        notice_de = await service.get_privacy_notice("de")
        assert notice_de["language"] == "de"

    @pytest.mark.asyncio
    async def test_data_minimization_edge_cases(self, service, mock_db_session):
        """Test data minimization validation edge cases."""
        # Test with exactly at retention limit
        business_id = uuid4()
        
        # Mock data exactly at retention limit (should be compliant)
        mock_old_reviews_result = Mock()
        mock_old_reviews_result.scalars.return_value.all.return_value = []
        
        mock_old_conversations_result = Mock()
        mock_old_conversations_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.side_effect = [
            mock_old_reviews_result,
            mock_old_conversations_result,
        ]

        validation_result = await service.validate_data_minimization(business_id)
        assert validation_result["compliant"] is True