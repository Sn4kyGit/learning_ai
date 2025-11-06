"""
Integration tests for authentication endpoints.

This module tests the complete authentication flow including
login/logout endpoints and JWT token handling.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import patch

from backend.main import app
from backend.db.models import User, Organization
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
async def test_user_data(test_db_session: AsyncSession):
    """Create test user data."""
    auth_service = AuthService(test_db_session)
    password = "password123"
    hashed_password = auth_service.hash_password(password)
    
    user = User(
        email="test@example.com",
        name="Test User",
        role="admin",
        language_preference="en",
        password_hash=hashed_password
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return {"user": user, "password": password}


@pytest.fixture
async def test_organization(test_db_session: AsyncSession):
    """Create test organization."""
    org = Organization(
        name="Test Organization",
        subscription_tier="premium",
        cost_limit_monthly=200.00
    )
    
    test_db_session.add(org)
    await test_db_session.commit()
    await test_db_session.refresh(org)
    
    return org


class TestAuthEndpoints:
    """Test suite for authentication endpoints."""

    def test_register_user_success(self, client):
        """Test successful user registration."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "role": "admin",
            "password": "password123",
            "language_preference": "en"
        }
        
        # Act
        response = client.post("/api/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert data["role"] == "admin"
        assert "password" not in data  # Password should not be returned

    def test_register_user_invalid_email(self, client):
        """Test user registration with invalid email."""
        # Arrange
        user_data = {
            "email": "invalid-email",
            "name": "New User",
            "role": "admin",
            "password": "secure_password_123"
        }
        
        # Act
        response = client.post("/api/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_register_user_invalid_role(self, client):
        """Test user registration with invalid role."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "role": "invalid_role",
            "password": "password123"
        }
        
        # Act
        response = client.post("/api/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_register_user_short_password(self, client):
        """Test user registration with short password."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "role": "admin",
            "password": "short"
        }
        
        # Act
        response = client.post("/api/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_login_success(self, client, test_user_data):
        """Test successful user login."""
        # Arrange
        login_data = {
            "email": test_user_data["user"].email,
            "password": test_user_data["password"]
        }
        
        # Act
        response = client.post("/api/auth/login", json=login_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["user"]["email"] == test_user_data["user"].email

    def test_login_invalid_email(self, client):
        """Test login with invalid email."""
        # Arrange
        login_data = {
            "email": "nonexistent@example.com",
            "password": "any_password"
        }
        
        # Act
        response = client.post("/api/auth/login", json=login_data)
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_user_data):
        """Test login with wrong password."""
        # Arrange
        login_data = {
            "email": test_user_data["user"].email,
            "password": "wrong_password"
        }
        
        # Act
        response = client.post("/api/auth/login", json=login_data)
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client, test_user_data):
        """Test getting current user info with valid token."""
        # Arrange - Login first to get token
        login_data = {
            "email": test_user_data["user"].email,
            "password": test_user_data["password"]
        }
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Act
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["user"].email
        assert data["name"] == test_user_data["user"].name
        assert data["role"] == test_user_data["user"].role

    def test_get_current_user_no_token(self, client):
        """Test getting current user info without token."""
        # Act
        response = client.get("/api/auth/me")
        
        # Assert
        assert response.status_code == 403  # No authorization header

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user info with invalid token."""
        # Act
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_logout_success(self, client, test_user_data):
        """Test successful logout."""
        # Arrange - Login first to get token
        login_data = {
            "email": test_user_data["user"].email,
            "password": test_user_data["password"]
        }
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Act
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_accessible_businesses(self, client, test_user_data):
        """Test getting accessible businesses for user."""
        # Arrange - Login first to get token
        login_data = {
            "email": test_user_data["user"].email,
            "password": test_user_data["password"]
        }
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Act
        response = client.get(
            "/api/auth/accessible-businesses",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestRoleBasedAccess:
    """Test suite for role-based access control."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_super_admin_access(self, client, test_db_session):
        """Test super admin can access admin endpoints."""
        # Arrange - Create super admin user
        auth_service = AuthService(test_db_session)
        password = "password123"
        hashed_password = auth_service.hash_password(password)
        
        admin_user = User(
            email="admin@example.com",
            name="Super Admin",
            role="super_admin",
            password_hash=hashed_password
        )
        
        test_db_session.add(admin_user)
        await test_db_session.commit()
        
        # Login to get token
        login_data = {"email": "admin@example.com", "password": password}
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Act - Try to access admin endpoint
        response = client.get(
            "/api/auth/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_regular_user_denied_admin_access(self, client, test_db_session):
        """Test regular user cannot access admin endpoints."""
        # Arrange - Create regular user
        auth_service = AuthService(test_db_session)
        password = "password123"
        hashed_password = auth_service.hash_password(password)
        
        regular_user = User(
            email="user@example.com",
            name="Regular User",
            role="viewer",
            password_hash=hashed_password
        )
        
        test_db_session.add(regular_user)
        await test_db_session.commit()
        
        # Login to get token
        login_data = {"email": "user@example.com", "password": password}
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Act - Try to access admin endpoint
        response = client.get(
            "/api/auth/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 403  # Forbidden

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_admin_role_hierarchy(self, client, test_db_session):
        """Test admin role can access viewer-level endpoints."""
        # Arrange - Create admin user
        auth_service = AuthService(test_db_session)
        password = "password123"
        hashed_password = auth_service.hash_password(password)
        
        admin_user = User(
            email="admin@example.com",
            name="Admin User",
            role="admin",
            password_hash=hashed_password
        )
        
        test_db_session.add(admin_user)
        await test_db_session.commit()
        
        # Login to get token
        login_data = {"email": "admin@example.com", "password": password}
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Act - Access user info (viewer-level endpoint)
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200