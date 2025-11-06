"""
User and authentication fixtures for testing role-based access control.

This module provides fixtures for creating users with different roles,
authentication tokens, and permission scenarios for comprehensive testing.
"""

import pytest
import pytest_asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User, Organization, UserBusinessAccess, Business
from backend.tests.fixtures.data_factories import TestDataFactory
from backend.config import get_settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthFixtures:
    """Authentication-related test fixtures and utilities."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for testing."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(
        user_id: str,
        email: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token for testing."""
        settings = get_settings()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=24)
        
        to_encode = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": expire
        }
        
        return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    
    @staticmethod
    def create_expired_token(user_id: str, email: str, role: str) -> str:
        """Create expired JWT token for testing."""
        return AuthFixtures.create_access_token(
            user_id, email, role, 
            expires_delta=timedelta(hours=-1)
        )


@pytest_asyncio.fixture
async def test_super_admin(test_db_session: AsyncSession, test_organization: Organization) -> User:
    """Create super admin user for testing."""
    user = TestDataFactory.create_user(
        email="superadmin@example.com",
        name="Super Admin",
        role="super_admin",
        organization_id=test_organization.id,
        password_hash=AuthFixtures.hash_password("password123")
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def test_admin_user(test_db_session: AsyncSession, test_organization: Organization) -> User:
    """Create admin user for testing."""
    user = TestDataFactory.create_user(
        email="admin@example.com",
        name="Admin User",
        role="admin",
        organization_id=test_organization.id,
        password_hash=AuthFixtures.hash_password("password123")
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def test_viewer_user(test_db_session: AsyncSession, test_organization: Organization) -> User:
    """Create viewer user for testing."""
    user = TestDataFactory.create_user(
        email="viewer@example.com",
        name="Viewer User",
        role="viewer",
        organization_id=test_organization.id,
        password_hash=AuthFixtures.hash_password("password123")
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def test_users_all_roles(
    test_db_session: AsyncSession, 
    test_organization: Organization
) -> Dict[str, User]:
    """Create users with all roles for comprehensive testing."""
    users = {}
    
    # Create super admin
    super_admin = TestDataFactory.create_user(
        email="superadmin@test.com",
        name="Super Admin Test",
        role="super_admin",
        organization_id=test_organization.id,
        password_hash=AuthFixtures.hash_password("password123")
    )
    test_db_session.add(super_admin)
    users["super_admin"] = super_admin
    
    # Create admin
    admin = TestDataFactory.create_user(
        email="admin@test.com",
        name="Admin Test",
        role="admin",
        organization_id=test_organization.id,
        password_hash=AuthFixtures.hash_password("password123")
    )
    test_db_session.add(admin)
    users["admin"] = admin
    
    # Create viewer
    viewer = TestDataFactory.create_user(
        email="viewer@test.com",
        name="Viewer Test",
        role="viewer",
        organization_id=test_organization.id,
        password_hash=AuthFixtures.hash_password("password123")
    )
    test_db_session.add(viewer)
    users["viewer"] = viewer
    
    await test_db_session.commit()
    
    for user in users.values():
        await test_db_session.refresh(user)
    
    return users


@pytest_asyncio.fixture
async def test_user_business_permissions(
    test_db_session: AsyncSession,
    test_users_all_roles: Dict[str, User],
    test_business: Business
) -> Dict[str, UserBusinessAccess]:
    """Create user business access permissions for testing."""
    permissions = {}
    
    # Admin gets full access
    admin_access = TestDataFactory.create_user_business_access(
        user_id=test_users_all_roles["admin"].id,
        business_id=test_business.id,
        permission_level="full_access",
        granted_by=test_users_all_roles["super_admin"].id
    )
    test_db_session.add(admin_access)
    permissions["admin"] = admin_access
    
    # Viewer gets read-only access
    viewer_access = TestDataFactory.create_user_business_access(
        user_id=test_users_all_roles["viewer"].id,
        business_id=test_business.id,
        permission_level="read_only",
        granted_by=test_users_all_roles["admin"].id
    )
    test_db_session.add(viewer_access)
    permissions["viewer"] = viewer_access
    
    await test_db_session.commit()
    
    for access in permissions.values():
        await test_db_session.refresh(access)
    
    return permissions


@pytest.fixture
def auth_tokens(test_users_all_roles: Dict[str, User]) -> Dict[str, str]:
    """Create authentication tokens for all user roles."""
    tokens = {}
    
    for role, user in test_users_all_roles.items():
        token = AuthFixtures.create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role
        )
        tokens[role] = token
    
    return tokens


@pytest.fixture
def expired_auth_token(test_admin_user: User) -> str:
    """Create expired authentication token for testing."""
    return AuthFixtures.create_expired_token(
        user_id=str(test_admin_user.id),
        email=test_admin_user.email,
        role=test_admin_user.role
    )


@pytest.fixture
def invalid_auth_token() -> str:
    """Create invalid authentication token for testing."""
    return "invalid.jwt.token"


@pytest_asyncio.fixture
async def multi_organization_users(test_db_session: AsyncSession) -> Dict[str, Any]:
    """Create users across multiple organizations for testing isolation."""
    # Create two organizations
    org1 = TestDataFactory.create_organization(name="Organization 1")
    org2 = TestDataFactory.create_organization(name="Organization 2")
    
    test_db_session.add(org1)
    test_db_session.add(org2)
    await test_db_session.commit()
    await test_db_session.refresh(org1)
    await test_db_session.refresh(org2)
    
    # Create users for each organization
    user1_org1 = TestDataFactory.create_user(
        email="user1@org1.com",
        name="User 1 Org 1",
        role="admin",
        organization_id=org1.id
    )
    
    user2_org1 = TestDataFactory.create_user(
        email="user2@org1.com",
        name="User 2 Org 1",
        role="viewer",
        organization_id=org1.id
    )
    
    user1_org2 = TestDataFactory.create_user(
        email="user1@org2.com",
        name="User 1 Org 2",
        role="admin",
        organization_id=org2.id
    )
    
    user2_org2 = TestDataFactory.create_user(
        email="user2@org2.com",
        name="User 2 Org 2",
        role="viewer",
        organization_id=org2.id
    )
    
    users = [user1_org1, user2_org1, user1_org2, user2_org2]
    for user in users:
        test_db_session.add(user)
    
    await test_db_session.commit()
    
    for user in users:
        await test_db_session.refresh(user)
    
    return {
        "organizations": {"org1": org1, "org2": org2},
        "users": {
            "org1": {"admin": user1_org1, "viewer": user2_org1},
            "org2": {"admin": user1_org2, "viewer": user2_org2}
        }
    }


@pytest_asyncio.fixture
async def user_with_multiple_business_access(
    test_db_session: AsyncSession,
    test_organization: Organization
) -> Dict[str, Any]:
    """Create user with access to multiple businesses for testing."""
    # Create user
    user = TestDataFactory.create_user(
        email="multibusiness@example.com",
        name="Multi Business User",
        role="admin",
        organization_id=test_organization.id
    )
    test_db_session.add(user)
    
    # Create multiple businesses
    businesses = []
    for i in range(3):
        business = TestDataFactory.create_business(
            name=f"Test Restaurant {i+1}",
            organization_id=test_organization.id
        )
        test_db_session.add(business)
        businesses.append(business)
    
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    for business in businesses:
        await test_db_session.refresh(business)
    
    # Create business access permissions
    access_permissions = []
    for i, business in enumerate(businesses):
        permission_level = "full_access" if i < 2 else "read_only"
        access = TestDataFactory.create_user_business_access(
            user_id=user.id,
            business_id=business.id,
            permission_level=permission_level
        )
        test_db_session.add(access)
        access_permissions.append(access)
    
    await test_db_session.commit()
    
    for access in access_permissions:
        await test_db_session.refresh(access)
    
    return {
        "user": user,
        "businesses": businesses,
        "access_permissions": access_permissions
    }


class AuthTestHelpers:
    """Helper methods for authentication testing."""
    
    @staticmethod
    def get_auth_headers(token: str) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        return {"Authorization": f"Bearer {token}"}
    
    @staticmethod
    def assert_unauthorized_response(response):
        """Assert that response indicates unauthorized access."""
        assert response.status_code == 401
        assert "detail" in response.json()
    
    @staticmethod
    def assert_forbidden_response(response):
        """Assert that response indicates forbidden access."""
        assert response.status_code == 403
        assert "detail" in response.json()
    
    @staticmethod
    async def create_test_login_data(user: User) -> Dict[str, str]:
        """Create login data for testing authentication endpoints."""
        return {
            "email": user.email,
            "password": "password123"  # Default test password
        }