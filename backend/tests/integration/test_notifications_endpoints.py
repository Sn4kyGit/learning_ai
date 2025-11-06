"""
Integration tests for notification configuration endpoints.

This module serves as the main entry point for notification tests
and imports from specialized test modules for better organization.
"""

# Import all test classes from specialized modules for backward compatibility
from .notifications.test_preferences import TestNotificationPreferences
from .notifications.test_alert_thresholds import TestAlertThresholds

# Note: Additional test classes (TestNotificationHistory, TestNotificationTesting, 
# TestNotificationAccessControl, TestNotificationPerformance) can be extracted
# to separate modules following the same pattern if needed.

__all__ = [
    'TestNotificationPreferences',
    'TestAlertThresholds'
]