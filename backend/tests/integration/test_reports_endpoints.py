"""
Integration tests for report generation endpoints.

This module tests the complete report functionality including
weekly reports, custom reports, and report configuration.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from datetime import date, datetime

from backend.main import app
from backend.db.models import User, Business, Organization
from backend.services.auth_service import AuthService


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def test_organization(test_db_session: AsyncSession):
    """Create test organization."""
    org = Organization(
        name="Test Restaurant Group",
        subscription_tier="premium",
        cost_limit_monthly=500.00
    )
    
    test_db_session.add(org)
    await test_db_session.commit()
    await test_db_session.refresh(org)
    
    return org


@pytest.fixture
async def test_user(test_db_session: AsyncSession, test_organization):
    """Create test user."""
    auth_service = AuthService(test_db_session)
    password = "password123"
    hashed_password = auth_service.hash_password(password)
    
    user = User(
        email="owner@restaurant.com",
        name="Restaurant Owner",
        role="admin",
        language_preference="en",
        organization_id=test_organization.id,
        password_hash=hashed_password
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return {"user": user, "password": password}


@pytest.fixture
async def test_business(test_db_session: AsyncSession, test_organization):
    """Create test business."""
    business = Business(
        name="Test Restaurant",
        google_place_id="ChIJTest123",
        category="restaurant",
        address="123 Test Street, Test City",
        organization_id=test_organization.id,
        avg_rating=4.2,
        total_reviews=150
    )
    
    test_db_session.add(business)
    await test_db_session.commit()
    await test_db_session.refresh(business)
    
    return business


@pytest.fixture
async def auth_headers(client, test_user):
    """Get authentication headers for test user."""
    login_data = {
        "email": test_user["user"].email,
        "password": test_user["password"]
    }
    login_response = client.post("/api/auth/login", json=login_data)
    token = login_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


class TestReportConfiguration:
    """Test suite for report configuration functionality."""

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.configure_weekly_reports')
    def test_configure_weekly_reports_success(self, mock_configure, client, auth_headers, test_business):
        """Test successful weekly report configuration."""
        # Arrange
        mock_config = AsyncMock()
        mock_config.business_id = test_business.id
        mock_config.report_day = 1  # Monday
        mock_config.delivery_method = "web_and_email"
        mock_config.language = "en"
        mock_config.include_sections = ["sentiment_analysis", "top_topics", "action_items"]
        mock_config.next_report_date = datetime(2024, 1, 22, 9, 0, 0)
        mock_config.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_config.updated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_configure.return_value = mock_config
        
        config_data = {
            "report_day": 1,
            "delivery_method": "web_and_email",
            "language": "en",
            "include_sections": ["sentiment_analysis", "top_topics", "action_items"]
        }
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/configuration",
            json=config_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["business_id"] == str(test_business.id)
        assert data["report_day"] == 1
        assert data["delivery_method"] == "web_and_email"
        assert data["language"] == "en"
        assert len(data["include_sections"]) == 3

    def test_configure_weekly_reports_invalid_data(self, client, auth_headers, test_business):
        """Test report configuration with invalid data."""
        # Arrange
        config_data = {
            "report_day": 8,  # Invalid: should be 1-7
            "delivery_method": "invalid_method",
            "language": "en"
        }
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/configuration",
            json=config_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.get_report_configuration')
    def test_get_report_configuration_success(self, mock_get_config, client, auth_headers, test_business):
        """Test successful report configuration retrieval."""
        # Arrange
        mock_config = AsyncMock()
        mock_config.business_id = test_business.id
        mock_config.report_day = 1
        mock_config.delivery_method = "web_only"
        mock_config.language = "en"
        mock_config.include_sections = ["sentiment_analysis", "top_topics"]
        mock_config.next_report_date = datetime(2024, 1, 22, 9, 0, 0)
        mock_config.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_config.updated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_get_config.return_value = mock_config
        
        # Act
        response = client.get(
            f"/api/reports/{test_business.id}/configuration",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["business_id"] == str(test_business.id)
        assert data["report_day"] == 1
        assert data["delivery_method"] == "web_only"

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.get_report_configuration')
    def test_get_report_configuration_not_found(self, mock_get_config, client, auth_headers, test_business):
        """Test report configuration retrieval when not configured."""
        # Arrange
        mock_get_config.return_value = None
        
        # Act
        response = client.get(
            f"/api/reports/{test_business.id}/configuration",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.update_report_configuration')
    def test_update_report_configuration_success(self, mock_update, client, auth_headers, test_business):
        """Test successful report configuration update."""
        # Arrange
        mock_config = AsyncMock()
        mock_config.business_id = test_business.id
        mock_config.report_day = 5  # Friday
        mock_config.delivery_method = "web_and_email"
        mock_config.language = "de"
        mock_config.include_sections = ["sentiment_analysis", "competitor_mentions"]
        mock_config.next_report_date = datetime(2024, 1, 26, 9, 0, 0)
        mock_config.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_config.updated_at = datetime(2024, 1, 20, 14, 0, 0)
        
        mock_update.return_value = mock_config
        
        update_data = {
            "report_day": 5,
            "delivery_method": "web_and_email",
            "language": "de",
            "include_sections": ["sentiment_analysis", "competitor_mentions"]
        }
        
        # Act
        response = client.put(
            f"/api/reports/{test_business.id}/configuration",
            json=update_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["report_day"] == 5
        assert data["language"] == "de"
        assert len(data["include_sections"]) == 2


class TestWeeklyReports:
    """Test suite for weekly report functionality."""

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.generate_weekly_report')
    def test_generate_weekly_report_success(self, mock_generate, client, auth_headers, test_business):
        """Test successful weekly report generation."""
        # Arrange
        mock_report = AsyncMock()
        mock_report.report_id = uuid4()
        mock_report.business_id = test_business.id
        mock_report.report_period_start = datetime(2024, 1, 8, 0, 0, 0)
        mock_report.report_period_end = datetime(2024, 1, 14, 23, 59, 59)
        mock_report.language = "en"
        mock_report.sections = {
            "sentiment_analysis": "Overall sentiment is positive with 78% positive reviews.",
            "top_topics": ["food_quality", "service", "ambiance"],
            "competitor_mentions": "2 mentions of competing restaurants found."
        }
        mock_report.action_items = [
            "Focus on improving service speed during peak hours",
            "Address cleanliness concerns mentioned in 3 reviews",
            "Promote popular dishes mentioned in positive reviews"
        ]
        mock_report.cost_summary = {
            "total_cost": 0.15,
            "tokens_used": 3000,
            "processing_time_ms": 2500
        }
        mock_report.generated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_generate.return_value = mock_report
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/generate-weekly",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert data["business_id"] == str(test_business.id)
        assert data["language"] == "en"
        assert len(data["action_items"]) == 3
        assert "cost_summary" in data

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.generate_weekly_report')
    def test_generate_weekly_report_force_regenerate(self, mock_generate, client, auth_headers, test_business):
        """Test weekly report generation with force regenerate."""
        # Arrange
        mock_report = AsyncMock()
        mock_report.report_id = uuid4()
        mock_report.business_id = test_business.id
        mock_report.report_period_start = datetime(2024, 1, 8, 0, 0, 0)
        mock_report.report_period_end = datetime(2024, 1, 14, 23, 59, 59)
        mock_report.language = "en"
        mock_report.sections = {}
        mock_report.action_items = []
        mock_report.cost_summary = {}
        mock_report.generated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_generate.return_value = mock_report
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/generate-weekly?force_regenerate=true",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        # Verify that force_regenerate was passed to the service
        mock_generate.assert_called_once_with(
            business_id=test_business.id,
            force_regenerate=True
        )

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.get_weekly_reports')
    def test_get_weekly_reports_success(self, mock_get_reports, client, auth_headers, test_business):
        """Test successful weekly reports retrieval."""
        # Arrange
        mock_reports = [
            AsyncMock(
                report_id=uuid4(),
                business_id=test_business.id,
                report_period_start=datetime(2024, 1, 8, 0, 0, 0),
                report_period_end=datetime(2024, 1, 14, 23, 59, 59),
                language="en",
                sections={"sentiment_analysis": "Positive week"},
                action_items=["Improve service"],
                cost_summary={"total_cost": 0.12},
                generated_at=datetime(2024, 1, 15, 10, 0, 0)
            ),
            AsyncMock(
                report_id=uuid4(),
                business_id=test_business.id,
                report_period_start=datetime(2024, 1, 1, 0, 0, 0),
                report_period_end=datetime(2024, 1, 7, 23, 59, 59),
                language="en",
                sections={"sentiment_analysis": "Mixed week"},
                action_items=["Address complaints"],
                cost_summary={"total_cost": 0.10},
                generated_at=datetime(2024, 1, 8, 10, 0, 0)
            )
        ]
        mock_get_reports.return_value = mock_reports
        
        # Act
        response = client.get(
            f"/api/reports/{test_business.id}/weekly",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["business_id"] == str(test_business.id)

    def test_get_weekly_reports_with_pagination(self, client, auth_headers, test_business):
        """Test weekly reports retrieval with pagination."""
        # Act
        response = client.get(
            f"/api/reports/{test_business.id}/weekly?skip=0&limit=5",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.get_weekly_report')
    def test_get_weekly_report_success(self, mock_get_report, client, auth_headers, test_business):
        """Test successful individual weekly report retrieval."""
        # Arrange
        report_id = uuid4()
        mock_report = AsyncMock()
        mock_report.report_id = report_id
        mock_report.business_id = test_business.id
        mock_report.report_period_start = datetime(2024, 1, 8, 0, 0, 0)
        mock_report.report_period_end = datetime(2024, 1, 14, 23, 59, 59)
        mock_report.language = "en"
        mock_report.sections = {"sentiment_analysis": "Positive week"}
        mock_report.action_items = ["Improve service"]
        mock_report.cost_summary = {"total_cost": 0.12}
        mock_report.generated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_get_report.return_value = mock_report
        
        # Act
        response = client.get(
            f"/api/reports/{test_business.id}/weekly/{report_id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["report_id"] == str(report_id)
        assert data["business_id"] == str(test_business.id)

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.get_weekly_report')
    def test_get_weekly_report_not_found(self, mock_get_report, client, auth_headers, test_business):
        """Test weekly report retrieval with non-existent ID."""
        # Arrange
        fake_id = str(uuid4())
        mock_get_report.return_value = None
        
        # Act
        response = client.get(
            f"/api/reports/{test_business.id}/weekly/{fake_id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404


class TestCustomReports:
    """Test suite for custom report functionality."""

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.generate_custom_report')
    def test_generate_custom_report_success(self, mock_generate, client, auth_headers, test_business):
        """Test successful custom report generation."""
        # Arrange
        mock_report = AsyncMock()
        mock_report.report_data = {
            "sentiment_summary": "Mostly positive feedback",
            "topic_analysis": ["food_quality", "service"],
            "trend_analysis": "Improving over time"
        }
        mock_report.recommendations = [
            "Continue focusing on food quality",
            "Maintain current service standards"
        ]
        mock_report.cost_info = {"tokens_used": 2000, "cost_usd": 0.08}
        mock_report.generated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_generate.return_value = mock_report
        
        report_request = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-14",
            "report_type": "comprehensive",
            "language": "en",
            "include_recommendations": True
        }
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/custom",
            json=report_request,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["business_id"] == str(test_business.id)
        assert data["report_type"] == "comprehensive"
        assert data["language"] == "en"
        assert "report_data" in data
        assert len(data["recommendations"]) == 2

    def test_generate_custom_report_invalid_dates(self, client, auth_headers, test_business):
        """Test custom report generation with invalid date range."""
        # Arrange
        report_request = {
            "start_date": "2024-01-15",
            "end_date": "2024-01-10",  # End before start
            "report_type": "sentiment",
            "language": "en"
        }
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/custom",
            json=report_request,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 400

    def test_generate_custom_report_invalid_type(self, client, auth_headers, test_business):
        """Test custom report generation with invalid report type."""
        # Arrange
        report_request = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-14",
            "report_type": "invalid_type",
            "language": "en"
        }
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/custom",
            json=report_request,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.generate_custom_report')
    def test_generate_custom_report_without_recommendations(self, mock_generate, client, auth_headers, test_business):
        """Test custom report generation without recommendations."""
        # Arrange
        mock_report = AsyncMock()
        mock_report.report_data = {"sentiment_summary": "Positive"}
        mock_report.recommendations = []
        mock_report.cost_info = {"tokens_used": 1000, "cost_usd": 0.04}
        mock_report.generated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_generate.return_value = mock_report
        
        report_request = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-14",
            "report_type": "sentiment",
            "language": "en",
            "include_recommendations": False
        }
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/custom",
            json=report_request,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["recommendations"] == []


class TestReportEmail:
    """Test suite for report email functionality."""

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.send_report_email')
    def test_send_report_email_success(self, mock_send_email, client, auth_headers, test_business):
        """Test successful report email sending."""
        # Arrange
        report_id = uuid4()
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/email/{report_id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["report_id"] == str(report_id)
        assert "recipient" in data

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.send_report_email')
    def test_send_report_email_custom_recipient(self, mock_send_email, client, auth_headers, test_business):
        """Test report email sending with custom recipient."""
        # Arrange
        report_id = uuid4()
        custom_email = "custom@example.com"
        
        # Act
        response = client.post(
            f"/api/reports/{test_business.id}/email/{report_id}?recipient_email={custom_email}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["recipient"] == custom_email


class TestReportAccessControl:
    """Test suite for report access control."""

    def test_unauthorized_report_access_denied(self, client, test_business):
        """Test that unauthorized users cannot access report endpoints."""
        # Act
        response = client.get(f"/api/reports/{test_business.id}/configuration")
        
        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_delete_reports(self, client, test_db_session, test_organization):
        """Test that admin users can delete reports."""
        # Arrange - Create admin user
        auth_service = AuthService(test_db_session)
        password = "password123"
        hashed_password = auth_service.hash_password(password)
        
        admin_user = User(
            email="admin@restaurant.com",
            name="Admin User",
            role="admin",
            password_hash=hashed_password
        )
        test_db_session.add(admin_user)
        await test_db_session.commit()
        
        # Login as admin
        login_data = {"email": "admin@restaurant.com", "password": password}
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create business for admin
        business = Business(
            name="Admin Restaurant",
            google_place_id="ChIJAdmin123",
            organization_id=test_organization.id
        )
        test_db_session.add(business)
        await test_db_session.commit()
        
        report_id = uuid4()
        
        # Act
        with patch('backend.services.business_advisory_service.BusinessAdvisoryService.delete_weekly_report', 
                   return_value=True):
            response = client.delete(
                f"/api/reports/{business.id}/weekly/{report_id}",
                headers=headers
            )
        
        # Assert
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_viewer_cannot_delete_reports(self, client, test_db_session, test_organization):
        """Test that viewer users cannot delete reports."""
        # Arrange - Create viewer user
        auth_service = AuthService(test_db_session)
        password = "password123"
        hashed_password = auth_service.hash_password(password)
        
        viewer_user = User(
            email="viewer@restaurant.com",
            name="Viewer User",
            role="viewer",
            password_hash=hashed_password
        )
        test_db_session.add(viewer_user)
        await test_db_session.commit()
        
        # Login as viewer
        login_data = {"email": "viewer@restaurant.com", "password": password}
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create business
        business = Business(
            name="Viewer Restaurant",
            google_place_id="ChIJViewer123",
            organization_id=test_organization.id
        )
        test_db_session.add(business)
        await test_db_session.commit()
        
        report_id = uuid4()
        
        # Act
        response = client.delete(
            f"/api/reports/{business.id}/weekly/{report_id}",
            headers=headers
        )
        
        # Assert
        assert response.status_code == 403  # Forbidden


class TestReportPerformance:
    """Test suite for report performance."""

    @patch('backend.services.business_advisory_service.BusinessAdvisoryService.generate_weekly_report')
    def test_weekly_report_generation_time(self, mock_generate, client, auth_headers, test_business):
        """Test that weekly report generation completes within acceptable time."""
        import time
        
        # Arrange
        mock_report = AsyncMock()
        mock_report.report_id = uuid4()
        mock_report.business_id = test_business.id
        mock_report.report_period_start = datetime(2024, 1, 8, 0, 0, 0)
        mock_report.report_period_end = datetime(2024, 1, 14, 23, 59, 59)
        mock_report.language = "en"
        mock_report.sections = {}
        mock_report.action_items = []
        mock_report.cost_summary = {}
        mock_report.generated_at = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_generate.return_value = mock_report
        
        # Act
        start_time = time.time()
        response = client.post(
            f"/api/reports/{test_business.id}/generate-weekly",
            headers=auth_headers
        )
        end_time = time.time()
        
        # Assert
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 5.0  # Should complete within 5 seconds

    def test_report_list_response_time(self, client, auth_headers, test_business):
        """Test that report listing responds within acceptable time."""
        import time
        
        # Act
        start_time = time.time()
        response = client.get(
            f"/api/reports/{test_business.id}/weekly",
            headers=auth_headers
        )
        end_time = time.time()
        
        # Assert
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 0.5  # Should respond within 500ms