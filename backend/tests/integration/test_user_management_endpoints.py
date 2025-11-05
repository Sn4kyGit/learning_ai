"""
Integration tests for user management endpoints.

This module tests multi-tenant access control endpoints and
business permission management API.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import patch

from backend.main import app
from backend.db.models import User, Business, Organization, UserBusinessAccess
from backend.services.auth_service import AuthService


# Mock password context for testing
@pytest.fixture(autouse=True)
def mock_pwd_context():
    """Mock password context to avoid bcrypt issues in tests."""
    with patch('backend.services.auth_service.pwd_context') as mock_ctx:
        # Simple mock that just prefixes passwords with "hashed_"
        mock_ctx.hash.side_effect = lambda pwd: f"hashed_{pwd}"
        mock_ctx.verify.side_effect = lambda plain, hashed: f"hashed_{plain}" == hashed
        yield mock_ctx


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def test_admin_user(test_db_session: AsyncSession, test_organization):
    """Create test admin user with authentication."""
    auth_service = AuthService(test_db_session)
    password = "password123"
    hashed_password = auth_service.hash_password(password)
    
    user = User(
        email="admin@example.com",
        name="Admin User",
        role="admin",
        organization_id=test_organization.id,
        password_hash=hashed_password
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return {"user": user, "password": password}


@pytest.fixture
async def test_super_admin_user(test_db_session: AsyncSession):
    """Create test super admin user with authentication."""
    auth_service = AuthService(test_db_session)
    password = "password123"
    hashed_password = auth_service.hash_password(password)
    
    user = User(
        email="superadmin@example.com",
        name="Super Admin User",
        role="super_admin",
        password_hash=hashed_password
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return {"user": user, "password": password}


@pytest.fixture
async def test_viewer_user(test_db_session: AsyncSession, test_organization):
    """Create test viewer user with authentication."""
    auth_service = AuthService(test_db_session)
    password = "password123"
    hashed_password = auth_service.hash_password(password)
    
    user = User(
        email="viewer@example.com",
        name="Viewer User",
        role="viewer",
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
        google_place_id="test-place-123",
        category="restaurant",
        organization_id=test_organization.id
    )
    
    test_db_session.add(business)
    await test_db_session.commit()
    await test_db_session.refresh(business)
    
    return business


def get_auth_headers(client, email: str, password: str) -> dict:
    """Helper function to get authentication headers."""
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestUserManagementEndpoints:
    """Test suite for user management endpoints."""

    @pytest.mark.asyncio
    async def test_grant_business_access_success(
        self, client, test_admin_user, test_viewer_user, test_business
    ):
        """Test successful business access granting."""
        # Arrange
        headers = get_auth_headers(client, test_admin_user["user"].email, test_admin_user["password"])
        
        access_data = {
            "user_id": str(test_viewer_user["user"].id),
            "business_id": str(test_business.id),
            "permission_level": "read_only"
        }
        
        # Act
        response = client.post(
            "/api/users/business-access",
            json=access_data,
            headers=headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(test_viewer_user["user"].id)
        assert data["business_id"] == str(test_business.id)
        assert data["permission_level"] == "read_only"

    @pytest.mark.asyncio
    async def test_grant_business_access_insufficient_permissions(
        self, client, test_viewer_user, test_business
    ):
        """Test business access granting with insufficient permissions."""
        # Arrange
        headers = get_auth_headers(client, test_viewer_user["user"].email, test_viewer_user["password"])
        
        access_data = {
            "user_id": str(uuid4()),
            "business_id": str(test_business.id),
            "permission_level": "read_only"
        }
        
        # Act
        response = client.post(
            "/api/users/business-access",
            json=access_data,
            headers=headers
        )
        
        # Assert
        assert response.status_code == 403  # Forbidden

    @pytest.mark.asyncio
    async def test_grant_business_access_invalid_permission_level(
        self, client, test_admin_user, test_viewer_user, test_business
    ):
        """Test business access granting with invalid permission level."""
        # Arrange
        headers = get_auth_headers(client, test_admin_user["user"].email, test_admin_user["password"])
        
        access_data = {
            "user_id": str(test_viewer_user["user"].id),
            "business_id": str(test_business.id),
            "permission_level": "invalid_permission"
        }
        
        # Act
        response = client.post(
            "/api/users/business-access",
            json=access_data,
            headers=headers
        )
        
        # Assert
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_revoke_business_access_success(
        self, client, test_admin_user, test_viewer_user, test_business, test_db_session
    ):
        """Test successful business access revocation."""
        # Arrange - Create access to revoke
        access = UserBusinessAccess(
            user_id=test_viewer_user["user"].id,
            business_id=test_business.id,
            permission_level="read_only",
            granted_by=test_admin_user["user"].id
        )
        test_db_session.add(access)
        await test_db_session.commit()
        
        headers = get_auth_headers(client, test_admin_user["user"].email, test_admin_user["password"])
        
        # Act
        response = client.delete(
            f"/api/users/business-access/{test_viewer_user['user'].id}/{test_business.id}",
            headers=headers
        )
        
        # Assert
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_revoke_business_access_not_found(
        self, client, test_admin_user
    ):
        """Test revoking non-existent business access."""
        # Arrange
        headers = get_auth_headers(client, test_admin_user["user"].email, test_admin_user["password"])
        
        # Act
        response = client.delete(
            f"/api/users/business-access/{uuid4()}/{uuid4()}",
            headers=headers
        )
        
        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_business_access_success(
        self, client, test_admin_user, test_viewer_user, test_business, test_db_session
    ):
        """Test successful business access update."""
        # Arrange - Create access to update
        access = UserBusinessAccess(
            user_id=test_viewer_user["user"].id,
            business_id=test_business.id,
            permission_level="read_only",
            granted_by=test_admin_user["user"].id
        )
        test_db_session.add(access)
        await test_db_session.commit()
        
        headers = get_auth_headers(client, test_admin_user["user"].email, test_admin_user["password"])
        
        update_data = {
            "user_id": str(test_viewer_user["user"].id),
            "business_id": str(test_business.id),
            "permission_level": "full_access"
        }
        
        # Act
        response = client.put(
            "/api/users/business-access",
            json=update_data,
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["permission_level"] == "full_access"

    @pytest.mark.asyncio
    async def test_get_business_users_success(
        self, client, test_admin_user, test_viewer_user, test_business, test_db_session
    ):
        """Test getting users with access to a business."""
        # Arrange - Create access records
        access = UserBusinessAccess(
            user_id=test_viewer_user["user"].id,
            business_id=test_business.id,
            permission_level="read_only",
            granted_by=test_admin_user["user"].id
        )
        test_db_session.add(access)
        await test_db_session.commit()
        
        headers = get_auth_headers(client, test_admin_user["user"].email, test_admin_user["password"])
        
        # Act
        response = client.get(
            f"/api/users/business/{test_business.id}/users",
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["user"]["email"] == test_viewer_user["user"].email
        assert data[0]["permission_level"] == "read_only"

    @pytest.mark.asyncio
    async def test_get_user_businesses_success(
        self, client, test_admin_user, test_viewer_user, test_business, test_db_session
    ):
        """Test getting businesses accessible to a user."""
        # Arrange - Create access record
        access = UserBusinessAccess(
            user_id=test_viewer_user["user"].id,
            business_id=test_business.id,
            permission_level="read_only",
            granted_by=test_admin_user["user"].id
        )
        test_db_session.add(access)
        await test_db_session.commit()
        
        headers = get_auth_headers(client, test_admin_user["user"].email, test_admin_user["password"])
        
        # Act
        response = client.get(
            f"/api/users/user/{test_viewer_user['user'].id}/businesses",
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["business"]["name"] == test_business.name
        assert data[0]["permission_level"] == "read_only"

    @pytest.mark.asyncio
    async def test_get_my_businesses_success(
        self, client, test_viewer_user, test_business, test_db_session
    ):
        """Test getting current user's accessible businesses."""
        # Arrange - Create access record
        access = UserBusinessAccess(
            user_id=test_viewer_user["user"].id,
            business_id=test_business.id,
            permission_level="read_only",
            granted_by=uuid4()
        )
        test_db_session.add(access)
        await test_db_session.commit()
        
        headers = get_auth_headers(client, test_viewer_user["user"].email, test_viewer_user["password"])
        
        # Act
        response = client.get(
            "/api/users/my-businesses",
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["business"]["name"] == test_business.name

    @pytest.mark.asyncio
    async def test_get_my_businesses_super_admin(
        self, client, test_super_admin_user, test_business
    ):
        """Test super admin can see all businesses."""
        # Arrange
        headers = get_auth_headers(
            client, 
            test_super_admin_user["user"].email, 
            test_super_admin_user["password"]
        )
        
        # Act
        response = client.get(
            "/api/users/my-businesses",
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Super admin should see all businesses with full access
        for business_data in data:
            assert business_data["permission_level"] == "full_access"

    @pytest.mark.asyncio
    async def test_get_organization_users_success(
        self, client, test_admin_user, test_organization
    ):
        """Test getting users in an organization."""
        # Arrange
        headers = get_auth_headers(client, test_admin_user["user"].email, test_admin_user["password"])
        
        # Act
        response = client.get(
            f"/api/users/organization/{test_organization.id}/users",
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include at least the admin user
        user_emails = [user["email"] for user in data]
        assert test_admin_user["user"].email in user_emails

    @pytest.mark.asyncio
    async def test_bulk_grant_organization_access_success(
        self, client, test_super_admin_user, test_organization, test_business
    ):
        """Test bulk granting organization access to a business."""
        # Arrange
        headers = get_auth_headers(
            client, 
            test_super_admin_user["user"].email, 
            test_super_admin_user["password"]
        )
        
        bulk_data = {
            "organization_id": str(test_organization.id),
            "business_id": str(test_business.id),
            "permission_level": "read_only"
        }
        
        # Act
        response = client.post(
            "/api/users/bulk-business-access",
            json=bulk_data,
            headers=headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "granted_count" in data
        assert data["granted_count"] >= 0

    @pytest.mark.asyncio
    async def test_bulk_grant_organization_access_insufficient_permissions(
        self, client, test_admin_user, test_organization, test_business
    ):
        """Test bulk granting with insufficient permissions (non-super-admin)."""
        # Arrange
        headers = get_auth_headers(client, test_admin_user["user"].email, test_admin_user["password"])
        
        bulk_data = {
            "organization_id": str(test_organization.id),
            "business_id": str(test_business.id),
            "permission_level": "read_only"
        }
        
        # Act
        response = client.post(
            "/api/users/bulk-business-access",
            json=bulk_data,
            headers=headers
        )
        
        # Assert
        assert response.status_code == 403  # Forbidden

    def test_endpoints_require_authentication(self, client):
        """Test that all user management endpoints require authentication."""
        # Test various endpoints without authentication
        endpoints = [
            ("POST", "/api/users/business-access", {"user_id": str(uuid4()), "business_id": str(uuid4()), "permission_level": "read_only"}),
            ("DELETE", f"/api/users/business-access/{uuid4()}/{uuid4()}", None),
            ("PUT", "/api/users/business-access", {"user_id": str(uuid4()), "business_id": str(uuid4()), "permission_level": "read_only"}),
            ("GET", f"/api/users/business/{uuid4()}/users", None),
            ("GET", f"/api/users/user/{uuid4()}/businesses", None),
            ("GET", "/api/users/my-businesses", None),
            ("GET", f"/api/users/organization/{uuid4()}/users", None),
            ("POST", "/api/users/bulk-business-access", {"organization_id": str(uuid4()), "business_id": str(uuid4()), "permission_level": "read_only"}),
        ]
        
        for method, endpoint, data in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=data)
            elif method == "PUT":
                response = client.put(endpoint, json=data)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 403  # No authorization header