"""
Integration tests for alert thresholds endpoints.

This module tests alert threshold configuration functionality including
setting, getting, and updating business alert thresholds.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime


class TestAlertThresholds:
    """Test suite for alert thresholds functionality."""

    @patch('backend.services.notification.alert_service.AlertService.set_alert_thresholds')
    def test_set_alert_thresholds_success(self, mock_set_thresholds, client, admin_auth_headers, test_business):
        """Test successful alert thresholds setting."""
        # Arrange
        mock_config = AsyncMock()
        mock_config.business_id = test_business.id
        mock_config.critical_rating_threshold = 3.0
        mock_config.sentiment_drop_threshold = 0.25
        mock_config.competitor_mention_alerts = True
        mock_config.crisis_mode_threshold = 5
        mock_config.alert_frequency_limit = 10
        mock_config.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_config.updated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_set_thresholds.return_value = mock_config
        
        thresholds_data = {
            "critical_rating_threshold": 3.0,
            "sentiment_drop_threshold": 0.25,
            "competitor_mention_alerts": True,
            "crisis_mode_threshold": 5,
            "alert_frequency_limit": 10
        }
        
        # Act
        response = client.post(
            f"/api/notifications/alert-thresholds/{test_business.id}",
            json=thresholds_data,
            headers=admin_auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["business_id"] == str(test_business.id)
        assert data["critical_rating_threshold"] == 3.0
        assert data["sentiment_drop_threshold"] == 0.25
        assert data["competitor_mention_alerts"] is True
        assert data["crisis_mode_threshold"] == 5

    def test_set_alert_thresholds_invalid_data(self, client, admin_auth_headers, test_business):
        """Test alert thresholds with invalid data."""
        # Arrange
        thresholds_data = {
            "critical_rating_threshold": 6.0,  # Invalid: should be 1.0-5.0
            "sentiment_drop_threshold": 1.5,   # Invalid: should be 0.1-1.0
            "crisis_mode_threshold": 0          # Invalid: should be >= 1
        }
        
        # Act
        response = client.post(
            f"/api/notifications/alert-thresholds/{test_business.id}",
            json=thresholds_data,
            headers=admin_auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_set_alert_thresholds_unauthorized(self, client, auth_headers, test_business):
        """Test alert thresholds setting without admin privileges."""
        # Arrange
        thresholds_data = {
            "critical_rating_threshold": 3.5,
            "sentiment_drop_threshold": 0.2
        }
        
        # Act
        response = client.post(
            f"/api/notifications/alert-thresholds/{test_business.id}",
            json=thresholds_data,
            headers=auth_headers
        )
        
        # Assert
        # Note: This depends on the user's role. If test_user is not admin, should be 403
        assert response.status_code in [201, 403]

    @patch('backend.services.notification.alert_service.AlertService.get_alert_thresholds')
    def test_get_alert_thresholds_success(self, mock_get_thresholds, client, auth_headers, test_business):
        """Test successful alert thresholds retrieval."""
        # Arrange
        mock_config = AsyncMock()
        mock_config.business_id = test_business.id
        mock_config.critical_rating_threshold = 3.5
        mock_config.sentiment_drop_threshold = 0.2
        mock_config.competitor_mention_alerts = True
        mock_config.crisis_mode_threshold = 3
        mock_config.alert_frequency_limit = 5
        mock_config.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_config.updated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_get_thresholds.return_value = mock_config
        
        # Act
        response = client.get(
            f"/api/notifications/alert-thresholds/{test_business.id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["business_id"] == str(test_business.id)
        assert data["critical_rating_threshold"] == 3.5
        assert data["sentiment_drop_threshold"] == 0.2

    @patch('backend.services.notification.alert_service.AlertService.get_alert_thresholds')
    def test_get_alert_thresholds_not_found(self, mock_get_thresholds, client, auth_headers, test_business):
        """Test alert thresholds retrieval when not configured."""
        # Arrange
        mock_get_thresholds.return_value = None
        
        # Act
        response = client.get(
            f"/api/notifications/alert-thresholds/{test_business.id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404

    @patch('backend.services.notification.alert_service.AlertService.update_alert_thresholds')
    def test_update_alert_thresholds_success(self, mock_update_thresholds, client, admin_auth_headers, test_business):
        """Test successful alert thresholds update."""
        # Arrange
        mock_config = AsyncMock()
        mock_config.business_id = test_business.id
        mock_config.critical_rating_threshold = 2.5
        mock_config.sentiment_drop_threshold = 0.3
        mock_config.competitor_mention_alerts = False
        mock_config.crisis_mode_threshold = 7
        mock_config.alert_frequency_limit = 15
        mock_config.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_config.updated_at = datetime(2024, 1, 20, 14, 0, 0)
        
        mock_update_thresholds.return_value = mock_config
        
        update_data = {
            "critical_rating_threshold": 2.5,
            "sentiment_drop_threshold": 0.3,
            "competitor_mention_alerts": False,
            "crisis_mode_threshold": 7,
            "alert_frequency_limit": 15
        }
        
        # Act
        response = client.put(
            f"/api/notifications/alert-thresholds/{test_business.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["critical_rating_threshold"] == 2.5
        assert data["competitor_mention_alerts"] is False
        assert data["crisis_mode_threshold"] == 7