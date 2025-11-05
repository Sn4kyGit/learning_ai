"""
Integration tests for alert and notification system.

Tests the complete alert workflow including database interactions,
multi-channel notifications, and crisis management mode.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from backend.services.notification.alert_service import (
    AlertService,
    NotificationRecipient,
)
from backend.ai.base import ClassificationResult
from backend.db.models import Review, Business, User, Classification
from backend.db.repositories.review import ReviewRepository
from backend.db.repositories.business import BusinessRepository
from backend.db.repositories.classification import ClassificationRepository


class TestAlertNotificationIntegration:
    """Integration tests for alert and notification system."""

    @pytest.mark.asyncio
    async def test_complete_critical_review_alert_workflow(
        self, test_db_session, test_business, test_user
    ):
        """Test complete workflow from critical review to notification delivery."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        # Create mock notification services
        mock_email = AsyncMock()
        mock_sms = AsyncMock()
        mock_push = AsyncMock()
        
        alert_service = AlertService(
            email_service=mock_email,
            sms_service=mock_sms,
            push_service=mock_push,
        )
        
        # Create test review
        review = Review(
            id=uuid4(),
            business_id=test_business.id,
            author_name="Angry Customer",
            rating=1,
            text="Terrible service, dirty restaurant, rude staff. Never coming back!",
            language="en",
            published_at=datetime.utcnow(),
            source="google",
            created_at=datetime.utcnow(),
        )
        
        # Create critical classification
        classification = ClassificationResult(
            sentiment="negative",
            topics=["service", "cleanliness"],
            urgency="high",
            competitor_mentioned=False,
            confidence_score=0.95,
            processing_time_ms=150,
            ai_model="gpt-5-nano",
        )
        
        # Mock recipient lookup to return test user
        test_recipient = NotificationRecipient(
            user_id=test_user.id,
            name=test_user.name,
            email=test_user.email,
            phone="+1234567890",
            notification_preferences={"email": True, "sms": True, "push": True},
            language="en",
        )
        alert_service._get_business_recipients = AsyncMock(return_value=[test_recipient])
        alert_service._check_crisis_mode = AsyncMock()

        # Act
        await alert_service.handle_critical_review(review, classification)

        # Assert
        alert_service._get_business_recipients.assert_called_once_with(review.business_id)
        alert_service._check_crisis_mode.assert_called_once_with(review.business_id)

    @pytest.mark.asyncio
    async def test_competitor_mention_super_admin_notification(
        self, test_db_session, test_business
    ):
        """Test competitor mention notifications are sent to Super-Admins."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        mock_email = AsyncMock()
        alert_service = AlertService(email_service=mock_email)
        
        # Create review with competitor mention
        review = Review(
            id=uuid4(),
            business_id=test_business.id,
            author_name="Comparing Customer",
            rating=2,
            text="This place is okay but McDonald's has better service and cleaner tables.",
            language="en",
            published_at=datetime.utcnow(),
            source="google",
            created_at=datetime.utcnow(),
        )
        
        classification = ClassificationResult(
            sentiment="negative",
            topics=["service", "cleanliness"],
            urgency="medium",
            competitor_mentioned=True,
            confidence_score=0.88,
            processing_time_ms=120,
            ai_model="gpt-5-nano",
        )
        
        # Mock Super-Admin recipient
        super_admin = NotificationRecipient(
            user_id=uuid4(),
            name="Super Admin",
            email="admin@businessbot.com",
            phone=None,
            notification_preferences={"email": True, "sms": False, "push": True},
            language="en",
        )
        alert_service._get_super_admin_recipients = AsyncMock(return_value=[super_admin])
        alert_service._schedule_delayed_notification = AsyncMock()

        # Act
        await alert_service.handle_competitor_mention(review, classification)

        # Assert
        alert_service._get_super_admin_recipients.assert_called_once_with(review.business_id)
        alert_service._schedule_delayed_notification.assert_called_once()
        
        # Verify 15-minute delay
        call_args = alert_service._schedule_delayed_notification.call_args
        assert call_args[1]["delay_minutes"] == 15

    @pytest.mark.asyncio
    async def test_rating_drop_alert_with_database_integration(
        self, test_db_session, test_business, test_user
    ):
        """Test rating drop alert with actual database operations."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        from backend.services.analytics_service import AnalyticsService
        from backend.db.repositories.business import BusinessRepository
        
        mock_email = AsyncMock()
        alert_service = AlertService(email_service=mock_email)
        
        business_repo = BusinessRepository(test_db_session)
        
        # Set initial business rating
        from backend.db.schemas import BusinessUpdate
        business_update = BusinessUpdate(avg_rating=4.2, total_reviews=50)
        await business_repo.update(test_business.id, business_update)
        
        # Mock recipient lookup
        test_recipient = NotificationRecipient(
            user_id=test_user.id,
            name=test_user.name,
            email=test_user.email,
            phone=None,
            notification_preferences={"email": True, "sms": False, "push": True},
            language="en",
        )
        alert_service._get_business_recipients = AsyncMock(return_value=[test_recipient])

        # Act - Simulate rating drop below threshold
        old_rating = 4.2
        new_rating = 3.1
        await alert_service.handle_rating_drop(
            test_business.id, old_rating, new_rating, threshold=3.5
        )

        # Assert
        alert_service._get_business_recipients.assert_called_once_with(test_business.id)

    @pytest.mark.asyncio
    async def test_multi_channel_notification_delivery(
        self, test_db_session, test_business, test_user
    ):
        """Test multi-channel notification delivery integration."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        # Create real-like mock services that track calls
        class MockEmailService:
            def __init__(self):
                self.sent_emails = []
            
            async def send_email(self, recipient, subject, body):
                self.sent_emails.append({
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                    "timestamp": datetime.utcnow()
                })
        
        class MockSMSService:
            def __init__(self):
                self.sent_sms = []
            
            async def send_sms(self, phone, message):
                self.sent_sms.append({
                    "phone": phone,
                    "message": message,
                    "timestamp": datetime.utcnow()
                })
        
        class MockPushService:
            def __init__(self):
                self.sent_notifications = []
            
            async def send_push(self, user_id, title, message):
                self.sent_notifications.append({
                    "user_id": user_id,
                    "title": title,
                    "message": message,
                    "timestamp": datetime.utcnow()
                })
        
        email_service = MockEmailService()
        sms_service = MockSMSService()
        push_service = MockPushService()
        
        alert_service = AlertService(
            email_service=email_service,
            sms_service=sms_service,
            push_service=push_service,
        )
        
        # Create test recipients with different preferences
        recipients = [
            NotificationRecipient(
                user_id=test_user.id,
                name="Manager",
                email="manager@restaurant.com",
                phone="+1234567890",
                notification_preferences={"email": True, "sms": True, "push": True},
                language="en",
            ),
            NotificationRecipient(
                user_id=uuid4(),
                name="Assistant",
                email="assistant@restaurant.com",
                phone=None,
                notification_preferences={"email": True, "sms": False, "push": True},
                language="en",
            ),
        ]
        
        # Create critical review and classification
        review = Review(
            id=uuid4(),
            business_id=test_business.id,
            author_name="Upset Customer",
            rating=1,
            text="Worst experience ever! Dirty tables, cold food, rude staff.",
            language="en",
            published_at=datetime.utcnow(),
            source="google",
            created_at=datetime.utcnow(),
        )
        
        classification = ClassificationResult(
            sentiment="negative",
            topics=["service", "cleanliness", "food_quality"],
            urgency="high",
            competitor_mentioned=False,
            confidence_score=0.93,
            processing_time_ms=180,
            ai_model="gpt-5-nano",
        )
        
        alert_service._get_business_recipients = AsyncMock(return_value=recipients)
        alert_service._check_crisis_mode = AsyncMock()

        # Act
        await alert_service.handle_critical_review(review, classification)

        # Assert - Check all notification channels were used appropriately
        assert len(email_service.sent_emails) == 2  # Both recipients get email
        assert len(sms_service.sent_sms) == 1  # Only manager has SMS enabled and phone
        assert len(push_service.sent_notifications) == 2  # Both get push notifications
        
        # Verify email content
        assert "Critical Alert" in email_service.sent_emails[0]["subject"]
        assert "manager@restaurant.com" in [email["recipient"] for email in email_service.sent_emails]
        assert "assistant@restaurant.com" in [email["recipient"] for email in email_service.sent_emails]
        
        # Verify SMS content
        assert "+1234567890" == sms_service.sent_sms[0]["phone"]
        assert "Critical review" in sms_service.sent_sms[0]["message"]

    @pytest.mark.asyncio
    async def test_crisis_management_mode_detection(
        self, test_db_session, test_business
    ):
        """Test crisis management mode detection with multiple critical reviews."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        alert_service = AlertService()
        
        # Create multiple critical reviews within 24 hours
        critical_reviews = []
        for i in range(4):  # More than crisis threshold (3)
            review = Review(
                id=uuid4(),
                business_id=test_business.id,
                author_name=f"Angry Customer {i+1}",
                rating=1,
                text=f"Terrible experience {i+1}. Never coming back!",
                language="en",
                published_at=datetime.utcnow() - timedelta(hours=i*2),
                source="google",
                created_at=datetime.utcnow(),
            )
            critical_reviews.append(review)
        
        classification = ClassificationResult(
            sentiment="negative",
            topics=["service"],
            urgency="high",
            competitor_mentioned=False,
            confidence_score=0.90,
            processing_time_ms=160,
            ai_model="gpt-5-nano",
        )
        
        alert_service._get_business_recipients = AsyncMock(return_value=[])
        alert_service._check_crisis_mode = AsyncMock()

        # Act - Process multiple critical reviews
        for review in critical_reviews:
            await alert_service.handle_critical_review(review, classification)

        # Assert - Crisis mode check should be called for each review
        assert alert_service._check_crisis_mode.call_count == 4

    @pytest.mark.asyncio
    async def test_alert_threshold_configuration_integration(
        self, test_db_session, test_business
    ):
        """Test configurable alert thresholds integration."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        alert_service = AlertService()
        alert_service._get_business_recipients = AsyncMock(return_value=[])
        
        business_id = test_business.id

        # Test different threshold configurations
        test_cases = [
            {"old": 4.5, "new": 3.8, "threshold": 4.0, "should_alert": True},
            {"old": 4.5, "new": 3.8, "threshold": 3.5, "should_alert": False},
            {"old": 3.8, "new": 3.2, "threshold": 3.5, "should_alert": True},
            {"old": 3.8, "new": 3.6, "threshold": 3.5, "should_alert": False},
        ]

        for case in test_cases:
            # Reset mock
            alert_service._get_business_recipients.reset_mock()
            
            # Act
            await alert_service.handle_rating_drop(
                business_id, case["old"], case["new"], case["threshold"]
            )
            
            # Assert
            if case["should_alert"]:
                alert_service._get_business_recipients.assert_called_once()
            else:
                alert_service._get_business_recipients.assert_not_called()

    @pytest.mark.asyncio
    async def test_notification_error_recovery(
        self, test_db_session, test_business, test_user
    ):
        """Test notification system error recovery and fallback behavior."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        # Create services that fail
        failing_email = AsyncMock(side_effect=Exception("Email service unavailable"))
        working_sms = AsyncMock()
        working_push = AsyncMock()
        
        alert_service = AlertService(
            email_service=failing_email,
            sms_service=working_sms,
            push_service=working_push,
        )
        
        recipient = NotificationRecipient(
            user_id=test_user.id,
            name="Test User",
            email="test@example.com",
            phone="+1234567890",
            notification_preferences={"email": True, "sms": True, "push": True},
            language="en",
        )
        
        review = Review(
            id=uuid4(),
            business_id=test_business.id,
            author_name="Test Customer",
            rating=1,
            text="Test critical review",
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
            processing_time_ms=140,
            ai_model="gpt-5-nano",
        )
        
        alert_service._get_business_recipients = AsyncMock(return_value=[recipient])
        alert_service._check_crisis_mode = AsyncMock()

        # Act - Should not raise exception despite email failure
        await alert_service.handle_critical_review(review, classification)

        # Assert - Other channels should still work
        # Email was attempted (through send_email method)
        working_sms.send_sms.assert_called_once()    # SMS still worked
        working_push.send_push.assert_called_once()   # Push still worked

    @pytest.mark.asyncio
    async def test_language_specific_notifications(
        self, test_db_session, test_business
    ):
        """Test notifications respect user language preferences."""
        # Arrange
        from backend.services.notification.alert_service import AlertService
        
        mock_email = AsyncMock()
        alert_service = AlertService(email_service=mock_email)
        
        # Create recipients with different language preferences
        recipients = [
            NotificationRecipient(
                user_id=uuid4(),
                name="English User",
                email="en@test.com",
                phone=None,
                notification_preferences={"email": True, "sms": False, "push": False},
                language="en",
            ),
            NotificationRecipient(
                user_id=uuid4(),
                name="German User",
                email="de@test.com",
                phone=None,
                notification_preferences={"email": True, "sms": False, "push": False},
                language="de",
            ),
        ]
        
        review = Review(
            id=uuid4(),
            business_id=test_business.id,
            author_name="Test Customer",
            rating=1,
            text="Critical review text",
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
            processing_time_ms=140,
            ai_model="gpt-5-nano",
        )
        
        alert_service._get_business_recipients = AsyncMock(return_value=recipients)
        alert_service._check_crisis_mode = AsyncMock()

        # Act
        await alert_service.handle_critical_review(review, classification)

        # Assert - Both users should receive notifications
        # (Language-specific content would be handled by email service implementation)
        assert len(mock_email.send_email.call_args_list) == 2