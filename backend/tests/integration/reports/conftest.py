"""
Shared fixtures for report integration tests.

This module provides common fixtures used across all report test modules.
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