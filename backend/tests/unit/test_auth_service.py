"""
Unit tests for authentication service.

This module tests password hashing, JWT token generation/validation,
and user authentication functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from fastapi import HTTPException, status
from jose import jwt

from backend.services.auth_service import AuthService, AuthenticationError
from backend.db.models import User, Organization
from backend.db.schemas import UserCreate


# Mock password context for testing
@pytest.fixture(autouse=True)
def mock_pwd_context():
    """Mock password context to avoid bcrypt issues in tests."""
    with patch('backend.services.auth_service.pwd_context') as mock_ctx:
        # Simple mock that just prefixes passwords with "hashed_"
        mock_ctx.hash.side_effect = lambda pwd: f"hashed_{pwd}"
        mock_ctx.verify.side_effect = lambda plain, hashed: f"hashed_{plain}" == hashed
        yield mock_ctx


class TestAuthService:
    """Test suite for AuthService."""

    def test_hash_password(self):
        """Test password hashing functionality."""
        # Arrange
        password = "test_pass_123"
        
        # Act
        hashed = AuthService.hash_password(password)
        
        # Assert
        assert hashed != password
        assert hashed == f"hashed_{password}"

    def test_verify_password_success(self):
        """Test successful password verification."""
        # Arrange
        password = "test_pass_123"
        hashed = AuthService.hash_password(password)
        
        # Act
        result = AuthService.verify_password(password, hashed)
        
        # Assert
        assert result is True

    def test_verify_password_failure(self):
        """Test failed password verification."""
        # Arrange
        password = "test_pass_123"
        wrong_password = "wrong_pass"
        hashed = AuthService.hash_password(password)
        
        # Act
        result = AuthService.verify_password(wrong_password, hashed)
        
        # Assert
        assert result is False

    def test_create_access_token(self):
        """Test JWT access token creation."""
        # Arrange
        data = {"sub": "user123", "email": "test@example.com"}
        
        # Act
        token = AuthService.create_access_token(data)
        
        # Assert
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
        
        # Verify token can be decoded
        from backend.config import get_settings
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_refresh_token(self):
        """Test JWT refresh token creation."""
        # Arrange
        data = {"sub": "user123", "email": "test@example.com"}
        
        # Act
        token = AuthService.create_refresh_token(data)
        
        # Assert
        assert isinstance(token, str)
        assert len(token) > 100
        
        # Verify token can be decoded
        from backend.config import get_settings
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_verify_token_success(self):
        """Test successful token verification."""
        # Arrange
        data = {"sub": "user123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)
        
        # Act
        payload = AuthService.verify_token(token, "access")
        
        # Assert
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_verify_token_wrong_type(self):
        """Test token verification with wrong type."""
        # Arrange
        data = {"sub": "user123"}
        token = AuthService.create_access_token(data)
        
        # Act & Assert
        with pytest.raises(AuthenticationError, match="Invalid token type"):
            AuthService.verify_token(token, "refresh")

    def test_verify_token_expired(self):
        """Test verification of expired token."""
        # Arrange
        data = {"sub": "user123"}
        # Create token that expires immediately
        with patch('backend.services.auth_service.datetime') as mock_datetime:
            past_time = datetime.now(timezone.utc) - timedelta(hours=1)
            mock_datetime.now.return_value = past_time
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            token = AuthService.create_access_token(data)
        
        # Act & Assert
        with pytest.raises(AuthenticationError, match="Invalid token"):
            AuthService.verify_token(token, "access")

    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        # Arrange
        invalid_token = "invalid.token.here"
        
        # Act & Assert
        with pytest.raises(AuthenticationError, match="Invalid token"):
            AuthService.verify_token(invalid_token, "access")

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self, test_db_session):
        """Test getting user by email when user exists."""
        # Arrange
        auth_service = AuthService(test_db_session)
        user = User(
            email="test@example.com",
            name="Test User",
            role="admin",
            password_hash="hashed_password"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Act
        result = await auth_service.get_user_by_email("test@example.com")
        
        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        assert result.name == "Test User"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, test_db_session):
        """Test getting user by email when user doesn't exist."""
        # Arrange
        auth_service = AuthService(test_db_session)
        
        # Act
        result = await auth_service.get_user_by_email("nonexistent@example.com")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self, test_db_session):
        """Test getting user by ID when user exists."""
        # Arrange
        auth_service = AuthService(test_db_session)
        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            name="Test User",
            role="admin",
            password_hash="hashed_password"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Act
        result = await auth_service.get_user_by_id(user_id)
        
        # Assert
        assert result is not None
        assert result.id == user_id
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, test_db_session):
        """Test successful user authentication."""
        # Arrange
        auth_service = AuthService(test_db_session)
        password = "test_pass"
        hashed_password = AuthService.hash_password(password)
        
        user = User(
            email="test@example.com",
            name="Test User",
            role="admin",
            password_hash=hashed_password
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Act
        result = await auth_service.authenticate_user("test@example.com", password)
        
        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        assert result.last_login is not None

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, test_db_session):
        """Test authentication with wrong password."""
        # Arrange
        auth_service = AuthService(test_db_session)
        password = "test_pass"
        hashed_password = AuthService.hash_password(password)
        
        user = User(
            email="test@example.com",
            name="Test User",
            role="admin",
            password_hash=hashed_password
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Act
        result = await auth_service.authenticate_user("test@example.com", "wrong_pass")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, test_db_session):
        """Test authentication with non-existent user."""
        # Arrange
        auth_service = AuthService(test_db_session)
        
        # Act
        result = await auth_service.authenticate_user("nonexistent@example.com", "password")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_user_success(self, test_db_session):
        """Test successful user creation."""
        # Arrange
        auth_service = AuthService(test_db_session)
        user_data = UserCreate(
            email="new@example.com",
            name="New User",
            role="admin",
            password="test_pass",
            language_preference="en"
        )
        
        # Act
        result = await auth_service.create_user(user_data)
        
        # Assert
        assert result.email == "new@example.com"
        assert result.name == "New User"
        assert result.role == "admin"
        assert result.password_hash != "test_pass"  # Should be hashed
        assert result.password_hash == "hashed_test_pass"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, test_db_session):
        """Test user creation with duplicate email."""
        # Arrange
        auth_service = AuthService(test_db_session)
        
        # Create first user
        existing_user = User(
            email="existing@example.com",
            name="Existing User",
            role="admin",
            password_hash="hashed_password"
        )
        test_db_session.add(existing_user)
        await test_db_session.commit()
        
        user_data = UserCreate(
            email="existing@example.com",
            name="New User",
            role="admin",
            password="test_password"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.create_user(user_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_login_user_success(self, test_db_session):
        """Test successful user login."""
        # Arrange
        auth_service = AuthService(test_db_session)
        password = "test_pass"
        hashed_password = AuthService.hash_password(password)
        
        user = User(
            email="test@example.com",
            name="Test User",
            role="admin",
            password_hash=hashed_password
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Act
        result = await auth_service.login_user("test@example.com", password)
        
        # Assert
        assert result.access_token is not None
        assert result.token_type == "bearer"
        assert result.expires_in > 0
        assert result.user.email == "test@example.com"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_login_user_invalid_credentials(self, test_db_session):
        """Test login with invalid credentials."""
        # Arrange
        auth_service = AuthService(test_db_session)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login_user("nonexistent@example.com", "password")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_check_user_business_access_super_admin(self, test_db_session):
        """Test business access check for super admin."""
        # Arrange
        auth_service = AuthService(test_db_session)
        user_id = uuid4()
        business_id = uuid4()
        
        user = User(
            id=user_id,
            email="admin@example.com",
            name="Super Admin",
            role="super_admin",
            password_hash="hashed_password"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Act
        result = await auth_service.check_user_business_access(user_id, business_id)
        
        # Assert
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_check_user_business_access_no_access(self, test_db_session):
        """Test business access check when user has no access."""
        # Arrange
        auth_service = AuthService(test_db_session)
        user_id = uuid4()
        business_id = uuid4()
        
        user = User(
            id=user_id,
            email="user@example.com",
            name="Regular User",
            role="admin",
            password_hash="hashed_password"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Act
        result = await auth_service.check_user_business_access(user_id, business_id)
        
        # Assert
        assert result is False