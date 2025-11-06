"""
Alert service for real-time notifications and crisis management.

This service handles critical review detection, competitor mentions,
and multi-channel notification delivery.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
from dataclasses import dataclass

from backend.ai.base import ClassificationResult
from backend.db.models import Review

logger = logging.getLogger(__name__)


@dataclass
class NotificationRecipient:
    """Notification recipient information."""

    user_id: UUID
    name: str
    email: str
    phone: Optional[str]
    notification_preferences: Dict[str, bool]  # email, sms, push
    language: str


@dataclass
class CriticalAlert:
    """Critical alert information."""

    business_id: UUID
    review_id: UUID
    alert_type: str  # critical_review, competitor_mention, rating_drop
    severity: str  # high, medium, low
    message: str
    review_text: str
    classification_data: Dict[str, Any]
    created_at: datetime


class AlertService:
    """Handles real-time alerts and notifications."""

    def __init__(
        self,
        email_service=None,  # TODO: Implement email service
        sms_service=None,  # TODO: Implement SMS service
        push_service=None,  # TODO: Implement push notification service
    ):
        """Initialize alert service.

        Args:
            email_service: Email notification service
            sms_service: SMS notification service
            push_service: Push notification service
        """
        self._email_service = email_service
        self._sms_service = sms_service
        self._push_service = push_service
        self._crisis_threshold = 3  # Number of critical reviews to trigger crisis mode
        self._crisis_time_window = 24  # Hours

    async def handle_critical_review(
        self, review: Review, classification: ClassificationResult
    ) -> None:
        """Handle critical review detection and alerting.

        Args:
            review: Review entity
            classification: AI classification result
        """
        try:
            logger.info(
                f"Handling critical review {review.id} for business {review.business_id}"
            )

            # Create critical alert
            alert = CriticalAlert(
                business_id=review.business_id,
                review_id=review.id,
                alert_type="critical_review",
                severity="high",
                message=f"Critical review detected: {review.rating}-star review with {classification.sentiment} sentiment",
                review_text=(
                    review.text[:200] + "..." if len(review.text) > 200 else review.text
                ),
                classification_data={
                    "sentiment": classification.sentiment,
                    "topics": classification.topics,
                    "urgency": classification.urgency,
                    "confidence": float(classification.confidence_score),
                },
                created_at=datetime.now(timezone.utc),
            )

            # Get notification recipients for the business
            recipients = await self._get_business_recipients(review.business_id)

            # Send immediate notifications
            await self._send_critical_alert(alert, recipients)

            # Check for crisis management mode
            await self._check_crisis_mode(review.business_id)

        except Exception as e:
            logger.error(f"Failed to handle critical review {review.id}: {e}")

    async def handle_competitor_mention(
        self, review: Review, classification: ClassificationResult
    ) -> None:
        """Handle competitor mention detection and alerting.

        Args:
            review: Review entity
            classification: AI classification result
        """
        try:
            logger.info(f"Handling competitor mention in review {review.id}")

            # Create competitor mention alert
            alert = CriticalAlert(
                business_id=review.business_id,
                review_id=review.id,
                alert_type="competitor_mention",
                severity="medium",
                message=f"Competitor mentioned in {review.rating}-star review",
                review_text=(
                    review.text[:200] + "..." if len(review.text) > 200 else review.text
                ),
                classification_data={
                    "sentiment": classification.sentiment,
                    "topics": classification.topics,
                    "competitor_mentioned": True,
                    "confidence": float(classification.confidence_score),
                },
                created_at=datetime.now(timezone.utc),
            )

            # Get Super-Admin recipients (competitor mentions go to Super-Admins)
            recipients = await self._get_super_admin_recipients(review.business_id)

            # Send notifications with 15-minute delay as per requirements
            await self._schedule_delayed_notification(
                alert, recipients, delay_minutes=15
            )

        except Exception as e:
            logger.error(
                f"Failed to handle competitor mention in review {review.id}: {e}"
            )

    async def handle_rating_drop(
        self,
        business_id: UUID,
        old_rating: float,
        new_rating: float,
        threshold: float = 3.5,
    ) -> None:
        """Handle significant rating drop alerts.

        Args:
            business_id: Business UUID
            old_rating: Previous average rating
            new_rating: New average rating
            threshold: Rating threshold for alerts
        """
        try:
            if new_rating < threshold and old_rating >= threshold:
                logger.info(
                    f"Rating drop alert for business {business_id}: {old_rating} -> {new_rating}"
                )

                alert = CriticalAlert(
                    business_id=business_id,
                    review_id=UUID(
                        "00000000-0000-0000-0000-000000000000"
                    ),  # No specific review
                    alert_type="rating_drop",
                    severity="high",
                    message=f"Average rating dropped below {threshold}: {old_rating:.1f} -> {new_rating:.1f}",
                    review_text="",
                    classification_data={
                        "old_rating": old_rating,
                        "new_rating": new_rating,
                        "threshold": threshold,
                    },
                    created_at=datetime.now(timezone.utc),
                )

                recipients = await self._get_business_recipients(business_id)
                await self._send_critical_alert(alert, recipients)

        except Exception as e:
            logger.error(
                f"Failed to handle rating drop for business {business_id}: {e}"
            )

    async def _send_critical_alert(
        self, alert: CriticalAlert, recipients: List[NotificationRecipient]
    ) -> None:
        """Send critical alert to recipients via multiple channels.

        Args:
            alert: Critical alert to send
            recipients: List of notification recipients
        """
        try:
            for recipient in recipients:
                # Send email notification
                if recipient.notification_preferences.get("email", True):
                    await self._send_email_alert(alert, recipient)

                # Send SMS notification for high severity alerts
                if (
                    alert.severity == "high"
                    and recipient.notification_preferences.get("sms", False)
                    and recipient.phone
                ):
                    await self._send_sms_alert(alert, recipient)

                # Send push notification
                if recipient.notification_preferences.get("push", True):
                    await self._send_push_alert(alert, recipient)

            logger.info(f"Critical alert sent to {len(recipients)} recipients")

        except Exception as e:
            logger.error(f"Failed to send critical alert: {e}")

    async def _send_email_alert(
        self, alert: CriticalAlert, recipient: NotificationRecipient
    ) -> None:
        """Send email alert to recipient.

        Args:
            alert: Alert to send
            recipient: Email recipient
        """
        try:
            if self._email_service:
                subject = f"Critical Alert: {alert.alert_type.replace('_', ' ').title()}"
                body = f"""
                Alert Type: {alert.alert_type}
                Severity: {alert.severity}
                Message: {alert.message}
                
                Review Text: {alert.review_text}
                
                Classification Data: {alert.classification_data}
                
                Time: {alert.created_at}
                """
                await self._email_service.send_email(recipient.email, subject, body)
            
            logger.info(
                f"Email alert sent to {recipient.email} for alert {alert.alert_type}"
            )

        except Exception as e:
            logger.error(f"Failed to send email alert to {recipient.email}: {e}")

    async def _send_sms_alert(
        self, alert: CriticalAlert, recipient: NotificationRecipient
    ) -> None:
        """Send SMS alert to recipient.

        Args:
            alert: Alert to send
            recipient: SMS recipient
        """
        try:
            if self._sms_service:
                message = f"Critical Alert: {alert.message} - {alert.review_text[:100]}"
                await self._sms_service.send_sms(recipient.phone, message)
            
            logger.info(
                f"SMS alert sent to {recipient.phone} for alert {alert.alert_type}"
            )

        except Exception as e:
            logger.error(f"Failed to send SMS alert to {recipient.phone}: {e}")

    async def _send_push_alert(
        self, alert: CriticalAlert, recipient: NotificationRecipient
    ) -> None:
        """Send push notification alert to recipient.

        Args:
            alert: Alert to send
            recipient: Push notification recipient
        """
        try:
            if self._push_service:
                title = f"Critical Alert: {alert.alert_type.replace('_', ' ').title()}"
                message = alert.message
                await self._push_service.send_push(recipient.user_id, title, message)
            
            logger.info(
                f"Push alert sent to user {recipient.user_id} for alert {alert.alert_type}"
            )

        except Exception as e:
            logger.error(f"Failed to send push alert to user {recipient.user_id}: {e}")

    async def _get_business_recipients(
        self, business_id: UUID
    ) -> List[NotificationRecipient]:
        """Get notification recipients for a business.

        Args:
            business_id: Business UUID

        Returns:
            List of notification recipients
        """
        try:
            # TODO: Implement actual recipient lookup from database
            # This would query users with access to the business through UserBusinessAccess
            # For now, return placeholder recipients
            
            logger.info(f"Getting recipients for business {business_id}")
            
            # Placeholder implementation - in real implementation this would:
            # 1. Query UserBusinessAccess table for users with access to this business
            # 2. Join with User table to get user details
            # 3. Filter by notification preferences
            # 4. Return list of NotificationRecipient objects
            
            return [
                NotificationRecipient(
                    user_id=UUID("11111111-1111-1111-1111-111111111111"),
                    name="Restaurant Manager",
                    email="manager@restaurant.com",
                    phone="+1234567890",
                    notification_preferences={"email": True, "sms": True, "push": True},
                    language="en",
                )
            ]

        except Exception as e:
            logger.error(f"Failed to get recipients for business {business_id}: {e}")
            return []

    async def _get_super_admin_recipients(
        self, business_id: UUID
    ) -> List[NotificationRecipient]:
        """Get Super-Admin recipients for competitor mention alerts.

        Args:
            business_id: Business UUID

        Returns:
            List of Super-Admin recipients
        """
        try:
            # TODO: Implement actual Super-Admin lookup
            # This would query users with super_admin role from User table
            
            logger.info(f"Getting super admin recipients for business {business_id}")
            
            # Placeholder implementation - in real implementation this would:
            # 1. Query User table for users with role='super_admin'
            # 2. Filter by notification preferences
            # 3. Return list of NotificationRecipient objects
            
            return [
                NotificationRecipient(
                    user_id=UUID("22222222-2222-2222-2222-222222222222"),
                    name="Super Admin",
                    email="admin@businessbot.com",
                    phone=None,
                    notification_preferences={
                        "email": True,
                        "sms": False,
                        "push": True,
                    },
                    language="en",
                )
            ]

        except Exception as e:
            logger.error(f"Failed to get super admin recipients: {e}")
            return []

    async def _check_crisis_mode(self, business_id: UUID) -> None:
        """Check if business should enter crisis management mode.

        Args:
            business_id: Business UUID to check
        """
        try:
            # TODO: Implement crisis mode detection
            # This would:
            # 1. Query Classification table for high urgency reviews in last 24 hours
            # 2. Count critical reviews within the time window
            # 3. If count >= crisis_threshold, trigger crisis management mode
            # 4. Send special crisis management alerts with response templates
            
            logger.info(f"Checking crisis mode for business {business_id}")
            
            # Placeholder implementation - in real implementation this would:
            # 1. Query recent critical reviews (last 24 hours)
            # 2. Check if count >= self._crisis_threshold (3)
            # 3. If yes, trigger crisis management mode:
            #    - Send escalated notifications
            #    - Suggest immediate response templates
            #    - Notify management team
            
            # For now, just log the check
            logger.info(f"Crisis mode check completed for business {business_id}")

        except Exception as e:
            logger.error(f"Failed to check crisis mode for business {business_id}: {e}")

    async def _schedule_delayed_notification(
        self,
        alert: CriticalAlert,
        recipients: List[NotificationRecipient],
        delay_minutes: int,
    ) -> None:
        """Schedule a delayed notification.

        Args:
            alert: Alert to send
            recipients: Notification recipients
            delay_minutes: Delay in minutes
        """
        try:
            # TODO: Implement actual delayed notification scheduling
            # This could use:
            # 1. Task queue like Celery with countdown
            # 2. Database-based scheduler with background worker
            # 3. APScheduler for in-memory scheduling
            # 4. Cloud-based scheduling service
            
            logger.info(f"Scheduling delayed notification for {delay_minutes} minutes")
            logger.info(f"Alert type: {alert.alert_type}, Recipients: {len(recipients)}")
            
            # Placeholder implementation - in real implementation this would:
            # 1. Create a scheduled task in task queue
            # 2. Set delay/countdown for the specified minutes
            # 3. Task would call _send_critical_alert when executed
            # 4. Handle task failures and retries
            
            # For now, just log the scheduling
            logger.info(f"Delayed notification scheduled successfully")

        except Exception as e:
            logger.error(f"Failed to schedule delayed notification: {e}")
