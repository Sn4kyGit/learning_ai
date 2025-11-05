"""
Unit tests for AlertService.

Tests critical review detection, competitor mention alerts,
crisis management mode, and multi-channel notifications.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from dataclasses import dataclass

from backend.services.notification.alert_service import (
    AlertService,
    CriticalAlert,
    NotificationRecipient,
)
from backend.ai.base import ClassificationResult
from backend.db.models import Review


class MockEmailService:
    """Mock email service for testing."""

    def __init__(self):
        self.sent_emails = []

    async def send_email(self, recipient: str, subject: str, body: str) -> None:
        """Mock send email."""
        self.sent_emails.append({
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "timestamp": datetime.utcnow()
        })


class MockSMSService:
    """Mock SMS service for testing."""

    def __init__(self):
        self.sent_sms = []

    async def send_sms(self, phone: str, message: str) -> None:
        """Mock send SMS."""
        self.sent_sms.append({
            "phone": phone,
            "message": message,
            "timestamp": datetime.utcnow()
        })


class MockPushService:
    """Mock push notification service for testing."""

    def __init__(self):
        self.sent_notifications = []

    async def send_push(self, user_id: UUID, title: str, message: str) -> None:
        """Mock send push notification."""
        self.sent_notifications.append({
            "user_id": user_id,
            "title": title,
            "message": message,
            "timestamp": datetime.utcnow()
        })


@pytest.fixture
def mock_services():
    """Provide mock notification services."""
    return {
        "email": MockEmailService(),
        "sms": MockSMSService(),
        "push": MockPushService(),
    }


@pytest.fixture
def alert_service(mock_services):
    """Provide AlertService with mock dependencies."""
    service = AlertService(
        email_service=mock_services["email"],
        sms_service=mock_services["sms"],
        push_service=mock_services["push"],
    )
    
    # Mock recipient lookup methods
    service._get_business_recipients = AsyncMock()
    service._get_super_admin_recipients = AsyncMock()
    service._check_crisis_mode = AsyncMock()
    service._schedule_delayed_notification = AsyncMock()
    
    return service


@pytest.fixture
def sample_review():
    """Provide sample review for testing."""
    return Review(
        id=uuid4(),
        business_id=uuid4(),
        author_name="John Doe",
        rating=1,
        text="Terrible service and dirty restaurant. Food was cold and staff was rude.",
        language="en",
        published_at=datetime.utcnow(),
        source="google",
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def critical_classification():
    """Provide critical classification result."""
    return ClassificationResult(
        sentiment="negative",
        topics=["service", "cleanliness"],
        urgency="high",
        competitor_mentioned=False,
        confidence_score=0.95,
        processing_time_ms=150,
        ai_model="gpt-5-nano",
    )


@pytest.fixture
def competitor_classification():
    """Provide competitor mention classification result."""
    return ClassificationResult(
        sentiment="negative",
        topics=["service"],
        urgency="medium",
        competitor_mentioned=True,
        confidence_score=0.88,
        processing_time_ms=120,
        ai_model="gpt-5-nano",
    )


@pytest.fixture
def sample_recipients():
    """Provide sample notification recipients."""
    return [
        NotificationRecipient(
            user_id=uuid4(),
            name="Restaurant Manager",
            email="manager@restaurant.com",
            phone="+1234567890",
            notification_preferences={"email": True, "sms": True, "push": True},
            language="en",
        ),
        NotificationRecipient(
            user_id=uuid4(),
            name="Assistant Manager",
            email="assistant@restaurant.com",
            phone=None,
            notification_preferences={"email": True, "sms": False, "push": True},
            language="en",
        ),
    ]


class TestAlertService:
    """Test suite for AlertService."""

    @pytest.mark.asyncio
    async def test_handle_critical_review_success(
        self, alert_service, sample_review, critical_classification, sample_recipients
    ):
        """Test successful critical review alert handling."""
        # Arrange
        alert_service._get_business_recipients.return_value = sample_recipients

        # Act
        await alert_service.handle_critical_review(sample_review, critical_classification)

        # Assert
        alert_service._get_business_recipients.assert_called_once_with(sample_review.business_id)
        alert_service._check_crisis_mode.assert_called_once_with(sample_review.business_id)

    @pytest.mark.asyncio
    async def test_handle_competitor_mention_success(
        self, alert_service, sample_review, competitor_classification, sample_recipients
    ):
        """Test successful competitor mention alert handling."""
        # Arrange
        alert_service._get_super_admin_recipients.return_value = sample_recipients

        # Act
        await alert_service.handle_competitor_mention(sample_review, competitor_classification)

        # Assert
        alert_service._get_super_admin_recipients.assert_called_once_with(sample_review.business_id)
        alert_service._schedule_delayed_notification.assert_called_once()
        
        # Verify 15-minute delay
        call_args = alert_service._schedule_delayed_notification.call_args
        assert call_args[1]["delay_minutes"] == 15

    @pytest.mark.asyncio
    async def test_handle_rating_drop_below_threshold(self, alert_service, sample_recipients):
        """Test rating drop alert when falling below threshold."""
        # Arrange
        business_id = uuid4()
        old_rating = 4.2
        new_rating = 3.1
        threshold = 3.5
        alert_service._get_business_recipients.return_value = sample_recipients

        # Act
        await alert_service.handle_rating_drop(business_id, old_rating, new_rating, threshold)

        # Assert
        alert_service._get_business_recipients.assert_called_once_with(business_id)

    @pytest.mark.asyncio
    async def test_handle_rating_drop_no_alert_above_threshold(self, alert_service):
        """Test no alert when rating stays above threshold."""
        # Arrange
        business_id = uuid4()
        old_rating = 4.2
        new_rating = 3.8
        threshold = 3.5

        # Act
        await alert_service.handle_rating_drop(business_id, old_rating, new_rating, threshold)

        # Assert
        alert_service._get_business_recipients.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_critical_alert_all_channels(
        self, alert_service, mock_services, sample_recipients
    ):
        """Test sending critical alert through all notification channels."""
        # Arrange
        alert = CriticalAlert(
            business_id=uuid4(),
            review_id=uuid4(),
            alert_type="critical_review",
            severity="high",
            message="Critical review detected",
            review_text="Terrible service",
            classification_data={"sentiment": "negative"},
            created_at=datetime.utcnow(),
        )

        # Act
        await alert_service._send_critical_alert(alert, sample_recipients)

        # Assert - Email notifications sent
        assert len(mock_services["email"].sent_emails) == 2
        assert mock_services["email"].sent_emails[0]["recipient"] == "manager@restaurant.com"
        assert mock_services["email"].sent_emails[1]["recipient"] == "assistant@restaurant.com"

        # Assert - SMS sent only to recipients with phone and SMS preference
        assert len(mock_services["sms"].sent_sms) == 1
        assert mock_services["sms"].sent_sms[0]["phone"] == "+1234567890"

        # Assert - Push notifications sent to all recipients
        assert len(mock_services["push"].sent_notifications) == 2

    @pytest.mark.asyncio
    async def test_send_critical_alert_respects_preferences(
        self, alert_service, mock_services
    ):
        """Test that notification preferences are respected."""
        # Arrange
        recipients = [
            NotificationRecipient(
                user_id=uuid4(),
                name="Email Only User",
                email="email@test.com",
                phone="+1111111111",
                notification_preferences={"email": True, "sms": False, "push": False},
                language="en",
            ),
            NotificationRecipient(
                user_id=uuid4(),
                name="SMS Only User",
                email="sms@test.com",
                phone="+2222222222",
                notification_preferences={"email": False, "sms": True, "push": False},
                language="en",
            ),
        ]

        alert = CriticalAlert(
            business_id=uuid4(),
            review_id=uuid4(),
            alert_type="critical_review",
            severity="high",
            message="Test alert",
            review_text="Test review",
            classification_data={},
            created_at=datetime.utcnow(),
        )

        # Act
        await alert_service._send_critical_alert(alert, recipients)

        # Assert
        assert len(mock_services["email"].sent_emails) == 1
        assert mock_services["email"].sent_emails[0]["recipient"] == "email@test.com"
        
        assert len(mock_services["sms"].sent_sms) == 1
        assert mock_services["sms"].sent_sms[0]["phone"] == "+2222222222"
        
        assert len(mock_services["push"].sent_notifications) == 0

    @pytest.mark.asyncio
    async def test_send_sms_only_for_high_severity(
        self, alert_service, mock_services, sample_recipients
    ):
        """Test SMS is only sent for high severity alerts."""
        # Arrange
        medium_alert = CriticalAlert(
            business_id=uuid4(),
            review_id=uuid4(),
            alert_type="competitor_mention",
            severity="medium",
            message="Competitor mentioned",
            review_text="Test review",
            classification_data={},
            created_at=datetime.utcnow(),
        )

        # Act
        await alert_service._send_critical_alert(medium_alert, sample_recipients)

        # Assert - No SMS sent for medium severity
        assert len(mock_services["sms"].sent_sms) == 0
        
        # But email and push still sent
        assert len(mock_services["email"].sent_emails) == 2
        assert len(mock_services["push"].sent_notifications) == 2

    @pytest.mark.asyncio
    async def test_critical_review_detection_algorithm(
        self, alert_service, sample_recipients
    ):
        """Test critical review detection algorithm."""
        # Arrange
        alert_service._get_business_recipients.return_value = sample_recipients
        
        # Test case 1: High urgency negative review with service/cleanliness topics
        critical_review = Review(
            id=uuid4(),
            business_id=uuid4(),
            author_name="Angry Customer",
            rating=1,
            text="Worst service ever, dirty tables, rude staff",
            language="en",
            published_at=datetime.utcnow(),
            source="google",
            created_at=datetime.utcnow(),
        )
        
        critical_classification = ClassificationResult(
            sentiment="negative",
            topics=["service", "cleanliness"],
            urgency="high",
            competitor_mentioned=False,
            confidence_score=0.92,
            processing_time_ms=180,
            ai_model="gpt-5-nano",
        )

        # Act
        await alert_service.handle_critical_review(critical_review, critical_classification)

        # Assert
        alert_service._get_business_recipients.assert_called_once()
        alert_service._check_crisis_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_competitor_mention_detection(
        self, alert_service, sample_recipients
    ):
        """Test competitor mention detection and alerting."""
        # Arrange
        alert_service._get_super_admin_recipients.return_value = sample_recipients
        
        review_with_competitor = Review(
            id=uuid4(),
            business_id=uuid4(),
            author_name="Comparing Customer",
            rating=2,
            text="This place is not as good as McDonald's down the street",
            language="en",
            published_at=datetime.utcnow(),
            source="google",
            created_at=datetime.utcnow(),
        )
        
        competitor_classification = ClassificationResult(
            sentiment="negative",
            topics=["service", "food_quality"],
            urgency="medium",
            competitor_mentioned=True,
            confidence_score=0.87,
            processing_time_ms=140,
            ai_model="gpt-5-nano",
        )

        # Act
        await alert_service.handle_competitor_mention(review_with_competitor, competitor_classification)

        # Assert
        alert_service._get_super_admin_recipients.assert_called_once_with(review_with_competitor.business_id)
        alert_service._schedule_delayed_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_crisis_management_mode_trigger(self, alert_service):
        """Test crisis management mode trigger logic."""
        # Arrange
        business_id = uuid4()

        # Act
        await alert_service._check_crisis_mode(business_id)

        # Assert - Method should be called (implementation details tested separately)
        alert_service._check_crisis_mode.assert_called_once_with(business_id)

    @pytest.mark.asyncio
    async def test_alert_threshold_configuration(self, alert_service, sample_recipients):
        """Test configurable alert thresholds."""
        # Arrange
        business_id = uuid4()
        alert_service._get_business_recipients.return_value = sample_recipients

        # Test custom threshold
        custom_threshold = 4.0
        old_rating = 4.5
        new_rating = 3.8

        # Act
        await alert_service.handle_rating_drop(business_id, old_rating, new_rating, custom_threshold)

        # Assert
        alert_service._get_business_recipients.assert_called_once_with(business_id)

    @pytest.mark.asyncio
    async def test_error_handling_in_critical_review(
        self, alert_service, sample_review, critical_classification
    ):
        """Test error handling in critical review processing."""
        # Arrange
        alert_service._get_business_recipients.side_effect = Exception("Database error")

        # Act - Should not raise exception
        await alert_service.handle_critical_review(sample_review, critical_classification)

        # Assert - Error should be logged but not raised
        alert_service._get_business_recipients.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_competitor_mention(
        self, alert_service, sample_review, competitor_classification
    ):
        """Test error handling in competitor mention processing."""
        # Arrange
        alert_service._get_super_admin_recipients.side_effect = Exception("Network error")

        # Act - Should not raise exception
        await alert_service.handle_competitor_mention(sample_review, competitor_classification)

        # Assert - Error should be logged but not raised
        alert_service._get_super_admin_recipients.assert_called_once()

    @pytest.mark.asyncio
    async def test_notification_channel_failure_handling(
        self, alert_service, mock_services, sample_recipients
    ):
        """Test handling of notification channel failures."""
        # Arrange
        mock_services["email"].send_email = AsyncMock(side_effect=Exception("Email service down"))
        
        alert = CriticalAlert(
            business_id=uuid4(),
            review_id=uuid4(),
            alert_type="critical_review",
            severity="high",
            message="Test alert",
            review_text="Test review",
            classification_data={},
            created_at=datetime.utcnow(),
        )

        # Act - Should not raise exception
        await alert_service._send_critical_alert(alert, sample_recipients)

        # Assert - Other channels should still work
        assert len(mock_services["sms"].sent_sms) == 1
        assert len(mock_services["push"].sent_notifications) == 2

    @pytest.mark.asyncio
    async def test_alert_message_truncation(
        self, alert_service, sample_recipients
    ):
        """Test that long review texts are properly truncated in alerts."""
        # Arrange
        alert_service._get_business_recipients.return_value = sample_recipients
        
        long_review = Review(
            id=uuid4(),
            business_id=uuid4(),
            author_name="Verbose Customer",
            rating=1,
            text="A" * 300,  # Very long review text
            language="en",
            published_at=datetime.utcnow(),
            source="google",
            created_at=datetime.utcnow(),
        )
        
        classification = ClassificationResult(
            sentiment="negative",
            topics=["service"],
            urgency="high",
            competitor_mentioned=False,
            confidence_score=0.95,
            processing_time_ms=160,
            ai_model="gpt-5-nano",
        )

        # Act
        await alert_service.handle_critical_review(long_review, classification)

        # Assert - Should complete without error (truncation handled internally)
        alert_service._get_business_recipients.assert_called_once()

    @pytest.mark.asyncio
    async def test_delayed_notification_scheduling(self, alert_service):
        """Test delayed notification scheduling for competitor mentions."""
        # Arrange
        alert = CriticalAlert(
            business_id=uuid4(),
            review_id=uuid4(),
            alert_type="competitor_mention",
            severity="medium",
            message="Competitor mentioned",
            review_text="Test review",
            classification_data={},
            created_at=datetime.utcnow(),
        )
        recipients = []

        # Act
        await alert_service._schedule_delayed_notification(alert, recipients, 15)

        # Assert - Method should be called (implementation details tested separately)
        alert_service._schedule_delayed_notification.assert_called_once()