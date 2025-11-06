"""
Integration tests for notification preferences endpoints.

This module tests notification preferences functionality including
setting, getting, and updating user notification preferences.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime


class TestNotificationPreferences:
    """Test suite for notification preferences functionality."""

    @patch('backend.services.notification.alert_service.AlertService.set_notification_preferences')
    def test_set_notification_preferences_success(self, mock_set_prefs, client, auth_headers, test_user):
        """Test successful notification preferences setting."""
        # Arrange
        mock_prefs = AsyncMock()
        mock_prefs.user_id = test_user["user"].id
        mock_prefs.business_id = None
        mock_prefs.email_enabled = True
        mock_prefs.sms_enabled = False
        mock_prefs.push_enabled = True
        mock_prefs.email_address = "owner@restaurant.com"
        mock_prefs.phone_number = None
        mock_prefs.notification_channels = ["email", "in_app"]
        mock_prefs.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_prefs.updated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_set_prefs.return_value = mock_prefs
        
        preferences_data = {
            "email_enabled": True,
            "sms_enabled": False,
            "push_enabled": True,
            "email_address": "owner@restaurant.com",
            "notification_channels": ["email", "in_app"]
        }
        
        # Act
        response = client.post(
            "/api/notifications/preferences",
            json=preferences_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(test_user["user"].id)
        assert data["email_enabled"] is True
        assert data["sms_enabled"] is False
        assert data["push_enabled"] is True
        assert data["email_address"] == "owner@restaurant.com"
        assert len(data["notification_channels"]) == 2

    def test_set_notification_preferences_invalid_data(self, client, auth_headers):
        """Test notification preferences with invalid data."""
        # Arrange
        preferences_data = {
            "email_enabled": "invalid",  # Should be boolean
            "phone_number": "invalid_phone",  # Invalid phone format
            "notification_channels": "not_a_list"  # Should be list
        }
        
        # Act
        response = client.post(
            "/api/notifications/preferences",
            json=preferences_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error

    @patch('backend.services.notification.alert_service.AlertService.get_notification_preferences')
    def test_get_notification_preferences_success(self, mock_get_prefs, client, auth_headers, test_user):
        """Test successful notification preferences retrieval."""
        # Arrange
        mock_prefs = AsyncMock()
        mock_prefs.user_id = test_user["user"].id
        mock_prefs.business_id = None
        mock_prefs.email_enabled = True
        mock_prefs.sms_enabled = True
        mock_prefs.push_enabled = False
        mock_prefs.email_address = "owner@restaurant.com"
        mock_prefs.phone_number = "+1234567890"
        mock_prefs.notification_channels = ["email", "sms"]
        mock_prefs.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_prefs.updated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_get_prefs.return_value = mock_prefs
        
        # Act
        response = client.get(
            "/api/notifications/preferences",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user["user"].id)
        assert data["email_enabled"] is True
        assert data["sms_enabled"] is True
        assert data["phone_number"] == "+1234567890"

    @patch('backend.services.notification.alert_service.AlertService.get_notification_preferences')
    def test_get_notification_preferences_not_found(self, mock_get_prefs, client, auth_headers):
        """Test notification preferences retrieval when not configured."""
        # Arrange
        mock_get_prefs.return_value = None
        
        # Act
        response = client.get(
            "/api/notifications/preferences",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404

    @patch('backend.services.notification.alert_service.AlertService.update_notification_preferences')
    def test_update_notification_preferences_success(self, mock_update_prefs, client, auth_headers, test_user):
        """Test successful notification preferences update."""
        # Arrange
        mock_prefs = AsyncMock()
        mock_prefs.user_id = test_user["user"].id
        mock_prefs.business_id = None
        mock_prefs.email_enabled = False
        mock_prefs.sms_enabled = True
        mock_prefs.push_enabled = True
        mock_prefs.email_address = "updated@restaurant.com"
        mock_prefs.phone_number = "+9876543210"
        mock_prefs.notification_channels = ["sms", "push"]
        mock_prefs.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_prefs.updated_at = datetime(2024, 1, 20, 14, 0, 0)
        
        mock_update_prefs.return_value = mock_prefs
        
        update_data = {
            "email_enabled": False,
            "sms_enabled": True,
            "push_enabled": True,
            "email_address": "updated@restaurant.com",
            "phone_number": "+9876543210",
            "notification_channels": ["sms", "push"]
        }
        
        # Act
        response = client.put(
            "/api/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email_enabled"] is False
        assert data["sms_enabled"] is True
        assert data["email_address"] == "updated@restaurant.com"

    @patch('backend.services.notification.alert_service.AlertService.set_notification_preferences')
    def test_set_business_specific_preferences(self, mock_set_prefs, client, auth_headers, test_user, test_business):
        """Test setting business-specific notification preferences."""
        # Arrange
        mock_prefs = AsyncMock()
        mock_prefs.user_id = test_user["user"].id
        mock_prefs.business_id = test_business.id
        mock_prefs.email_enabled = True
        mock_prefs.sms_enabled = True
        mock_prefs.push_enabled = False
        mock_prefs.email_address = "owner@restaurant.com"
        mock_prefs.phone_number = "+1234567890"
        mock_prefs.notification_channels = ["email", "sms"]
        mock_prefs.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_prefs.updated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_set_prefs.return_value = mock_prefs
        
        preferences_data = {
            "email_enabled": True,
            "sms_enabled": True,
            "push_enabled": False,
            "notification_channels": ["email", "sms"]
        }
        
        # Act
        response = client.post(
            f"/api/notifications/preferences?business_id={test_business.id}",
            json=preferences_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["business_id"] == str(test_business.id)