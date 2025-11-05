"""
Integration tests for GDPR compliance endpoints.

This module tests the complete GDPR compliance workflow including consent management,
data subject rights requests, privacy notices, and data breach reporting.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from uuid import uuid4

from backend.main import app
from backend.db.models import User, Business, Review, Conversation, ConversationMessage


class TestGDPRComplianceIntegration:
    """Integration test suite for GDPR compliance endpoints."""

    @pytest.fixture
    async def test_user(self, test_db):
        """Create a test user."""
        user = User(
            email="gdpr.test@example.com",
            name="GDPR Test User",
            role="admin",
            language_preference="en",
            password_hash="hashed_password",
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        return user

    @pytest.fixture
    async def test_super_admin(self, test_db):
        """Create a test super admin user."""
        user = User(
            email="super.admin@example.com",
            name="Super Admin",
            role="super_admin",
            language_preference="en",
            password_hash="hashed_password",
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        return user

    @pytest.fixture
    async def test_business(self, test_db):
        """Create a test business."""
        business = Business(
            name="Test Restaurant",
            google_place_id="test_place_123",
            category="restaurant",
            address="123 Test Street",
        )
        test_db.add(business)
        await test_db.commit()
        await test_db.refresh(business)
        return business

    @pytest.fixture
    async def test_conversation(self, test_db, test_user, test_business):
        """Create a test conversation with messages."""
        conversation = Conversation(
            business_id=test_business.id,
            user_id=test_user.id,
            language="en",
        )
        test_db.add(conversation)
        await test_db.commit()
        await test_db.refresh(conversation)

        # Add some messages
        messages = [
            ConversationMessage(
                conversation_id=conversation.id,
                role="user",
                content="How is my restaurant performing?",
            ),
            ConversationMessage(
                conversation_id=conversation.id,
                role="assistant",
                content="Your restaurant is performing well with positive sentiment.",
                ai_model="claude-haiku",
            ),
        ]
        
        for message in messages:
            test_db.add(message)
        
        await test_db.commit()
        return conversation

    async def test_record_consent_success(self, client: AsyncClient, auth_headers):
        """Test successful consent recording."""
        # Arrange
        consent_data = {
            "consent_type": "data_processing",
            "purpose": "Business intelligence and review analysis",
            "granted": True,
            "legal_basis": "consent",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0 Test Browser",
        }

        # Act
        response = await client.post(
            "/api/gdpr/consent",
            json=consent_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["consent_type"] == "data_processing"
        assert data["granted"] is True
        assert data["purpose"] == consent_data["purpose"]
        assert "timestamp" in data

    async def test_record_consent_withdrawal(self, client: AsyncClient, auth_headers):
        """Test consent withdrawal."""
        # Arrange
        consent_data = {
            "consent_type": "marketing",
            "purpose": "Marketing communications",
            "granted": False,  # Withdrawing consent
            "legal_basis": "consent",
        }

        # Act
        response = await client.post(
            "/api/gdpr/consent",
            json=consent_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["granted"] is False

    async def test_get_user_consents(self, client: AsyncClient, auth_headers):
        """Test retrieving user consent records."""
        # Act
        response = await client.get(
            "/api/gdpr/consent",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least the default consent
        assert len(data) >= 1

    async def test_create_data_access_request(self, client: AsyncClient, auth_headers):
        """Test creating a data access request."""
        # Arrange
        request_data = {
            "request_type": "access",
            "request_details": {"format": "json"},
        }

        # Act
        response = await client.post(
            "/api/gdpr/data-subject-request",
            json=request_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["request_type"] == "access"
        assert "user_profile" in data
        assert "conversations" in data
        assert "messages" in data
        assert "review_responses" in data

    async def test_create_data_erasure_request(self, client: AsyncClient, auth_headers, test_conversation):
        """Test creating a data erasure request."""
        # Arrange
        request_data = {
            "request_type": "erasure",
            "request_details": {"reason": "No longer using service"},
        }

        # Act
        response = await client.post(
            "/api/gdpr/data-subject-request",
            json=request_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["request_type"] == "erasure"
        assert data["status"] == "completed"
        assert "deleted_records" in data

    async def test_create_data_portability_request(self, client: AsyncClient, auth_headers):
        """Test creating a data portability request."""
        # Arrange
        request_data = {
            "request_type": "portability",
            "request_details": {"format": "json"},
        }

        # Act
        response = await client.post(
            "/api/gdpr/data-subject-request",
            json=request_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["request_type"] == "portability"
        assert data["export_format"] == "json"
        assert "data" in data
        assert "metadata" in data

    async def test_get_privacy_notice_default_language(self, client: AsyncClient):
        """Test getting privacy notice in default language."""
        # Act
        response = await client.get("/api/gdpr/privacy-notice")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "en"
        assert "content" in data
        assert "data_controller" in data["content"]
        assert "user_rights" in data["content"]
        assert len(data["content"]["user_rights"]) >= 6

    async def test_get_privacy_notice_specific_language(self, client: AsyncClient):
        """Test getting privacy notice in specific language."""
        # Act
        response = await client.get("/api/gdpr/privacy-notice?language=de")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "de"

    async def test_log_data_breach_success(self, client: AsyncClient, super_admin_auth_headers):
        """Test successful data breach logging by super admin."""
        # Arrange
        breach_data = {
            "severity": "high",
            "description": "Unauthorized access to user database",
            "affected_data_types": ["user_profiles", "conversations"],
            "affected_users_count": 150,
            "discovered_at": datetime.utcnow().isoformat(),
            "contained_at": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "root_cause": "SQL injection vulnerability in login endpoint",
            "mitigation_steps": [
                "Patched SQL injection vulnerability",
                "Reset all user passwords",
                "Implemented additional input validation",
            ],
        }

        # Act
        response = await client.post(
            "/api/gdpr/data-breach",
            json=breach_data,
            headers=super_admin_auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["severity"] == "high"
        assert data["affected_users_count"] == 150
        assert data["notification_required"] is True
        assert "breach_id" in data

    async def test_log_data_breach_insufficient_permissions(self, client: AsyncClient, auth_headers):
        """Test data breach logging with insufficient permissions."""
        # Arrange
        breach_data = {
            "severity": "low",
            "description": "Minor configuration issue",
            "affected_data_types": ["system_logs"],
            "affected_users_count": 0,
            "discovered_at": datetime.utcnow().isoformat(),
        }

        # Act
        response = await client.post(
            "/api/gdpr/data-breach",
            json=breach_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 403
        assert "super administrators" in response.json()["detail"]

    async def test_validate_data_minimization_success(self, client: AsyncClient, auth_headers, test_business):
        """Test data minimization validation."""
        # Act
        response = await client.get(
            f"/api/gdpr/data-minimization/{test_business.id}",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["business_id"] == str(test_business.id)
        assert "compliant" in data
        assert "issues" in data
        assert "recommendations" in data

    async def test_validate_data_minimization_insufficient_permissions(self, client: AsyncClient, test_business):
        """Test data minimization validation with insufficient permissions."""
        # Create viewer user
        from backend.services.auth_service import AuthService
        auth_service = AuthService()
        
        viewer_token = auth_service.create_access_token(
            data={"sub": "viewer@example.com", "role": "viewer"}
        )
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        # Act
        response = await client.get(
            f"/api/gdpr/data-minimization/{test_business.id}",
            headers=viewer_headers,
        )

        # Assert
        assert response.status_code == 403

    async def test_cleanup_expired_data_success(self, client: AsyncClient, super_admin_auth_headers):
        """Test expired data cleanup by super admin."""
        # Act
        response = await client.post(
            "/api/gdpr/cleanup-expired-data",
            headers=super_admin_auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "conversations_deleted" in data
        assert "messages_deleted" in data
        assert "old_analytics_deleted" in data
        assert "cleanup_completed_at" in data

    async def test_cleanup_expired_data_insufficient_permissions(self, client: AsyncClient, auth_headers):
        """Test expired data cleanup with insufficient permissions."""
        # Act
        response = await client.post(
            "/api/gdpr/cleanup-expired-data",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 403

    async def test_get_my_data(self, client: AsyncClient, auth_headers):
        """Test getting user's own data."""
        # Act
        response = await client.get(
            "/api/gdpr/my-data",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["request_type"] == "access"
        assert "user_profile" in data

    async def test_delete_my_data(self, client: AsyncClient, auth_headers):
        """Test deleting user's own data."""
        # Act
        response = await client.delete(
            "/api/gdpr/delete-my-data",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["request_type"] == "erasure"
        assert data["status"] == "completed"

    async def test_export_my_data(self, client: AsyncClient, auth_headers):
        """Test exporting user's own data."""
        # Act
        response = await client.get(
            "/api/gdpr/export-my-data",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["request_type"] == "portability"
        assert data["export_format"] == "json"
        assert "metadata" in data

    async def test_invalid_consent_type(self, client: AsyncClient, auth_headers):
        """Test recording consent with invalid consent type."""
        # Arrange
        consent_data = {
            "consent_type": "invalid_type",
            "purpose": "Test purpose",
            "granted": True,
        }

        # Act
        response = await client.post(
            "/api/gdpr/consent",
            json=consent_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 422  # Validation error

    async def test_invalid_data_subject_request_type(self, client: AsyncClient, auth_headers):
        """Test creating data subject request with invalid type."""
        # Arrange
        request_data = {
            "request_type": "invalid_type",
            "request_details": {},
        }

        # Act
        response = await client.post(
            "/api/gdpr/data-subject-request",
            json=request_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 422  # Validation error

    async def test_privacy_notice_invalid_language(self, client: AsyncClient):
        """Test getting privacy notice with invalid language."""
        # Act
        response = await client.get("/api/gdpr/privacy-notice?language=invalid")

        # Assert
        assert response.status_code == 422  # Validation error

    async def test_data_breach_invalid_severity(self, client: AsyncClient, super_admin_auth_headers):
        """Test logging data breach with invalid severity."""
        # Arrange
        breach_data = {
            "severity": "invalid_severity",
            "description": "Test breach",
            "affected_data_types": ["test_data"],
            "affected_users_count": 1,
            "discovered_at": datetime.utcnow().isoformat(),
        }

        # Act
        response = await client.post(
            "/api/gdpr/data-breach",
            json=breach_data,
            headers=super_admin_auth_headers,
        )

        # Assert
        assert response.status_code == 422  # Validation error

    async def test_consent_workflow_complete(self, client: AsyncClient, auth_headers):
        """Test complete consent workflow: grant, view, withdraw."""
        # Step 1: Grant consent
        grant_data = {
            "consent_type": "analytics",
            "purpose": "Analytics and performance monitoring",
            "granted": True,
        }
        
        grant_response = await client.post(
            "/api/gdpr/consent",
            json=grant_data,
            headers=auth_headers,
        )
        assert grant_response.status_code == 200
        assert grant_response.json()["granted"] is True

        # Step 2: View consents
        view_response = await client.get(
            "/api/gdpr/consent",
            headers=auth_headers,
        )
        assert view_response.status_code == 200
        consents = view_response.json()
        assert any(c["consent_type"] == "analytics" for c in consents)

        # Step 3: Withdraw consent
        withdraw_data = {
            "consent_type": "analytics",
            "purpose": "Analytics and performance monitoring",
            "granted": False,
        }
        
        withdraw_response = await client.post(
            "/api/gdpr/consent",
            json=withdraw_data,
            headers=auth_headers,
        )
        assert withdraw_response.status_code == 200
        assert withdraw_response.json()["granted"] is False

    async def test_data_subject_rights_workflow(self, client: AsyncClient, auth_headers):
        """Test complete data subject rights workflow."""
        # Step 1: Access request
        access_response = await client.get(
            "/api/gdpr/my-data",
            headers=auth_headers,
        )
        assert access_response.status_code == 200
        access_data = access_response.json()
        assert "user_profile" in access_data

        # Step 2: Export request
        export_response = await client.get(
            "/api/gdpr/export-my-data",
            headers=auth_headers,
        )
        assert export_response.status_code == 200
        export_data = export_response.json()
        assert export_data["export_format"] == "json"

        # Step 3: Deletion request (commented out as it would delete the user)
        # delete_response = await client.delete(
        #     "/api/gdpr/delete-my-data",
        #     headers=auth_headers,
        # )
        # assert delete_response.status_code == 200