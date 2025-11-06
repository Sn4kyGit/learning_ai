"""
End-to-end tests for complete user workflows.

This module tests the complete user journey from registration
to business insights generation, validating all major features
work together correctly.
"""

import pytest
import pytest_asyncio
import asyncio
import time
from typing import Dict, List
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock, Mock
from decimal import Decimal
from datetime import datetime, timedelta

from backend.db.models import User, Business, Organization, Review, Classification
from backend.services.auth_service import AuthService
from backend.tests.helpers.performance_helpers import PerformanceTester
from backend.tests.helpers.assertion_helpers import TestAssertions


@pytest_asyncio.fixture
async def clean_database(test_db_session: AsyncSession):
    """Ensure clean database state for each test."""
    from sqlalchemy import text
    
    # Clean up any existing data in proper order (respecting foreign keys)
    await test_db_session.execute(text("DELETE FROM classifications"))
    await test_db_session.execute(text("DELETE FROM reviews")) 
    await test_db_session.execute(text("DELETE FROM user_business_access"))
    await test_db_session.execute(text("DELETE FROM businesses"))
    await test_db_session.execute(text("DELETE FROM users"))
    await test_db_session.execute(text("DELETE FROM organizations"))
    await test_db_session.commit()
    
    yield test_db_session


class TestCompleteUserWorkflow:
    """Test complete user workflows from registration to insights."""

    @pytest.mark.asyncio
    async def test_complete_restaurant_owner_workflow(self, test_client: AsyncClient, clean_database, test_organization):
        """
        Test complete workflow: Registration → Business Setup → Review Import → 
        Classification → Analytics → Chat → Reports
        """
        # Step 1: User Registration
        registration_data = {
            "email": "owner@restaurant.com",
            "name": "Restaurant Owner",
            "role": "admin",
            "password": "secure_password_123",
            "language_preference": "en"
        }
        
        register_response = await test_client.post("/api/auth/register", json=registration_data)
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["email"] == "owner@restaurant.com"
        
        # Step 2: User Login
        login_data = {
            "email": "owner@restaurant.com",
            "password": "secure_password_123"
        }
        
        login_response = await test_client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        login_result = login_response.json()
        assert "access_token" in login_result
        
        auth_headers = {"Authorization": f"Bearer {login_result['access_token']}"}
        
        # Step 3: Use test organization (created by fixture)
        organization_id = str(test_organization.id)
        
        # Step 4: Register Business
        business_data = {
            "name": "Delicious Bistro",
            "google_place_id": "ChIJTest123456",
            "category": "restaurant",
            "address": "123 Main Street, Food City",
            "organization_id": organization_id
        }
        
        business_response = await test_client.post("/api/businesses/", json=business_data, headers=auth_headers)
        assert business_response.status_code == 201
        business_result = business_response.json()
        business_id = business_result["id"]
        
        # Step 5: Mock Google Places API and Import Reviews
        with patch('backend.external.google_places.GooglePlacesClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock review data
            mock_reviews = [
                {
                    "author_name": "John Smith",
                    "rating": 5,
                    "text": "Excellent food and amazing service! Best restaurant in town.",
                    "time": int((datetime.now() - timedelta(days=1)).timestamp()),
                    "review_id": "review_1"
                },
                {
                    "author_name": "Sarah Johnson",
                    "rating": 2,
                    "text": "Food was cold and service was extremely slow. Very disappointed.",
                    "time": int((datetime.now() - timedelta(days=2)).timestamp()),
                    "review_id": "review_2"
                },
                {
                    "author_name": "Mike Wilson",
                    "rating": 4,
                    "text": "Good food quality and nice atmosphere. Will come back.",
                    "time": int((datetime.now() - timedelta(days=3)).timestamp()),
                    "review_id": "review_3"
                }
            ]
            
            mock_client.get_place_reviews.return_value = mock_reviews
            
            # Import reviews
            import_request = {"max_reviews": 50, "force_refresh": False}
            import_response = await test_client.post(
                f"/api/businesses/{business_id}/import-reviews",
                json=import_request,
                headers=auth_headers
            )
            
            assert import_response.status_code == 200
            import_result = import_response.json()
            assert import_result["imported_count"] >= 3
        
        # Step 6: Verify Reviews Were Classified
        # Wait a moment for async processing
        await asyncio.sleep(0.1)
        
        reviews_response = await test_client.get(
            f"/api/businesses/{business_id}/reviews",
            headers=auth_headers
        )
        assert reviews_response.status_code == 200
        reviews_data = reviews_response.json()
        assert len(reviews_data) >= 3
        
        # Verify classifications exist
        for review in reviews_data:
            assert "classification" in review
            assert review["classification"]["sentiment"] in ["positive", "negative", "neutral"]
            assert isinstance(review["classification"]["topics"], list)
            assert review["classification"]["urgency"] in ["low", "medium", "high"]
        
        # Step 7: Check Analytics Dashboard
        analytics_response = await test_client.get(
            f"/api/analytics/{business_id}/dashboard",
            headers=auth_headers
        )
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        
        # Verify dashboard metrics
        assert "avg_rating" in analytics_data
        assert "sentiment_distribution" in analytics_data
        assert "total_reviews" in analytics_data
        assert "trend_data" in analytics_data
        assert analytics_data["total_reviews"] >= 3
        
        # Step 8: Test Chat Interface
        chat_request = {
            "message": "How is my restaurant performing based on recent reviews?",
            "language": "en"
        }
        
        chat_response = await test_client.post(
            f"/api/chat/{business_id}",
            json=chat_request,
            headers=auth_headers
        )
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        assert "response" in chat_data
        assert "conversation_id" in chat_data
        assert len(chat_data["response"]) > 0
        
        # Step 9: Generate Weekly Report
        report_request = {
            "report_type": "weekly",
            "language": "en",
            "include_action_items": True
        }
        
        report_response = await test_client.post(
            f"/api/reports/{business_id}/generate",
            json=report_request,
            headers=auth_headers
        )
        assert report_response.status_code == 200
        report_data = report_response.json()
        
        assert "summary" in report_data
        assert "action_items" in report_data
        assert "sentiment_analysis" in report_data
        assert len(report_data["action_items"]) > 0
        
        # Step 10: Check Cost Tracking
        cost_response = await test_client.get(
            f"/api/budget/{business_id}/current-usage",
            headers=auth_headers
        )
        assert cost_response.status_code == 200
        cost_data = cost_response.json()
        
        assert "total_cost" in cost_data
        assert "classification_cost" in cost_data
        assert "chat_cost" in cost_data
        assert "usage_percentage" in cost_data

    @pytest.mark.asyncio
    async def test_multi_tenant_workflow(self, test_client: AsyncClient, clean_database, test_organization):
        """Test multi-tenant workflow with organization and multiple businesses."""
        # Step 1: Create Super Admin
        super_admin_data = {
            "email": "superadmin@company.com",
            "name": "Super Admin",
            "role": "super_admin",
            "password": "admin_password_123",
            "language_preference": "en"
        }
        
        register_response = await test_client.post("/api/auth/register", json=super_admin_data)
        assert register_response.status_code == 201
        
        # Login as super admin
        login_response = await test_client.post("/api/auth/login", json={
            "email": "superadmin@company.com",
            "password": "admin_password_123"
        })
        admin_token = login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Step 2: Use test organization (created by fixture)
        org_id = str(test_organization.id)
        
        # Step 3: Create Multiple Businesses
        businesses = []
        for i in range(3):
            business_data = {
                "name": f"Restaurant Branch {i+1}",
                "google_place_id": f"ChIJBranch{i+1}",
                "category": "restaurant",
                "address": f"{100+i} Branch Street, City {i+1}",
                "organization_id": org_id
            }
            
            business_response = await test_client.post("/api/businesses/", json=business_data, headers=admin_headers)
            assert business_response.status_code == 201
            businesses.append(business_response.json())
        
        # Step 4: Create Regular Admin User
        admin_user_data = {
            "email": "admin@restaurant.com",
            "name": "Restaurant Admin",
            "role": "admin",
            "password": "admin_password_456",
            "language_preference": "en",
            "organization_id": org_id
        }
        
        admin_user_response = await test_client.post("/api/users/", json=admin_user_data, headers=admin_headers)
        assert admin_user_response.status_code == 201
        
        # Step 5: Grant Business Access to Admin User
        for business in businesses[:2]:  # Grant access to first 2 businesses only
            access_data = {
                "user_id": admin_user_response.json()["id"],
                "business_id": business["id"],
                "permission_level": "full_access"
            }
            
            access_response = await test_client.post("/api/users/business-access", json=access_data, headers=admin_headers)
            assert access_response.status_code == 201
        
        # Step 6: Login as Regular Admin
        admin_login_response = await test_client.post("/api/auth/login", json={
            "email": "admin@restaurant.com",
            "password": "admin_password_456"
        })
        regular_admin_token = admin_login_response.json()["access_token"]
        regular_admin_headers = {"Authorization": f"Bearer {regular_admin_token}"}
        
        # Step 7: Verify Access Control
        # Should see only 2 businesses (not all 3)
        accessible_businesses_response = await test_client.get("/api/auth/accessible-businesses", headers=regular_admin_headers)
        accessible_businesses = accessible_businesses_response.json()
        assert len(accessible_businesses) == 2
        
        # Should be able to access first business
        business_1_response = await test_client.get(f"/api/businesses/{businesses[0]['id']}", headers=regular_admin_headers)
        assert business_1_response.status_code == 200
        
        # Should NOT be able to access third business
        business_3_response = await test_client.get(f"/api/businesses/{businesses[2]['id']}", headers=regular_admin_headers)
        assert business_3_response.status_code == 403
        
        # Step 8: Test Consolidated Analytics (Super Admin Only)
        consolidated_response = await test_client.get(f"/api/analytics/organization/{org_id}/consolidated", headers=admin_headers)
        assert consolidated_response.status_code == 200
        consolidated_data = consolidated_response.json()
        
        assert "total_businesses" in consolidated_data
        assert "total_reviews" in consolidated_data
        assert "avg_rating_across_businesses" in consolidated_data
        assert consolidated_data["total_businesses"] == 3


class TestPerformanceRequirements:
    """Test performance requirements and optimization."""

    @pytest.mark.asyncio
    async def test_500_review_batch_processing_performance(self, test_client: AsyncClient, clean_database, test_organization):
        """Test that 500 reviews can be processed within 60 seconds."""
        # Setup user and business
        user_data = {
            "email": "performance@restaurant.com",
            "name": "Performance Tester",
            "role": "admin",
            "password": "password_123",
            "language_preference": "en"
        }
        
        register_response = await test_client.post("/api/auth/register", json=user_data)
        login_response = await test_client.post("/api/auth/login", json={
            "email": "performance@restaurant.com",
            "password": "password_123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Use test organization (created by fixture)
        org_id = str(test_organization.id)
        
        business_response = await test_client.post("/api/businesses/", json={
            "name": "Performance Test Bistro",
            "google_place_id": "ChIJPerf123",
            "category": "restaurant",
            "address": "Performance Street 123",
            "organization_id": org_id
        }, headers=headers)
        business_id = business_response.json()["id"]
        
        # Generate 500 mock reviews
        mock_reviews = []
        for i in range(500):
            mock_reviews.append({
                "author_name": f"Customer {i}",
                "rating": (i % 5) + 1,
                "text": f"Review text {i}. This is a sample review for performance testing.",
                "time": int((datetime.now() - timedelta(days=i % 30)).timestamp()),
                "review_id": f"perf_review_{i}"
            })
        
        # Test batch processing performance
        with patch('backend.external.google_places.GooglePlacesClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.get_place_reviews.return_value = mock_reviews
            
            start_time = time.time()
            
            import_response = await test_client.post(
                f"/api/businesses/{business_id}/import-reviews",
                json={"max_reviews": 500, "force_refresh": False},
                headers=headers
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Assert performance requirement
            assert import_response.status_code == 200
            assert processing_time < 60.0  # Must complete within 60 seconds
            
            import_data = import_response.json()
            assert import_data["imported_count"] == 500

    @pytest.mark.asyncio
    async def test_api_response_time_requirements(self, test_client: AsyncClient, clean_database, test_organization):
        """Test API response time requirements."""
        # Setup test data
        user_data = {
            "email": "speed@restaurant.com",
            "name": "Speed Tester",
            "role": "admin",
            "password": "password_123",
            "language_preference": "en"
        }
        
        register_response = await test_client.post("/api/auth/register", json=user_data)
        login_response = await test_client.post("/api/auth/login", json={
            "email": "speed@restaurant.com",
            "password": "password_123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Use test organization (created by fixture)
        org_id = str(test_organization.id)
        
        business_response = await test_client.post("/api/businesses/", json={
            "name": "Speed Test Bistro",
            "google_place_id": "ChIJSpeed123",
            "category": "restaurant",
            "address": "Speed Street 123",
            "organization_id": org_id
        }, headers=headers)
        business_id = business_response.json()["id"]
        
        # Test dashboard loading time (< 500ms requirement)
        start_time = time.time()
        dashboard_response = await test_client.get(f"/api/analytics/{business_id}/dashboard", headers=headers)
        dashboard_time = time.time() - start_time
        
        assert dashboard_response.status_code == 200
        assert dashboard_time < 0.5  # Must load within 500ms
        
        # Test business listing time (< 500ms requirement)
        start_time = time.time()
        businesses_response = await test_client.get("/api/businesses/", headers=headers)
        businesses_time = time.time() - start_time
        
        assert businesses_response.status_code == 200
        assert businesses_time < 0.5  # Must load within 500ms
        
        # Test individual business retrieval (< 300ms requirement)
        start_time = time.time()
        business_get_response = await test_client.get(f"/api/businesses/{business_id}", headers=headers)
        business_get_time = time.time() - start_time
        
        assert business_get_response.status_code == 200
        assert business_get_time < 0.3  # Must load within 300ms


class TestDataIsolation:
    """Test multi-tenant data isolation."""

    @pytest.mark.asyncio
    async def test_organization_data_isolation(self, test_client: AsyncClient, clean_database, test_db_session):
        """Test that organizations cannot access each other's data."""
        # Create two separate organizations with users
        
        # Organization 1
        org1_admin_data = {
            "email": "admin1@org1.com",
            "name": "Org 1 Admin",
            "role": "admin",
            "password": "password_123",
            "language_preference": "en"
        }
        
        register1_response = await test_client.post("/api/auth/register", json=org1_admin_data)
        login1_response = await test_client.post("/api/auth/login", json={
            "email": "admin1@org1.com",
            "password": "password_123"
        })
        token1 = login1_response.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        # Create organization 1 directly in database
        from backend.db.models import Organization
        from decimal import Decimal
        org1 = Organization(
            name="Organization 1",
            subscription_tier="premium",
            cost_limit_monthly=Decimal("200.00")
        )
        test_db_session.add(org1)
        await test_db_session.commit()
        await test_db_session.refresh(org1)
        org1_id = str(org1.id)
        
        business1_response = await test_client.post("/api/businesses/", json={
            "name": "Org 1 Restaurant",
            "google_place_id": "ChIJOrg1",
            "category": "restaurant",
            "address": "Org 1 Street",
            "organization_id": org1_id
        }, headers=headers1)
        business1_id = business1_response.json()["id"]
        
        # Organization 2
        org2_admin_data = {
            "email": "admin2@org2.com",
            "name": "Org 2 Admin",
            "role": "admin",
            "password": "password_456",
            "language_preference": "en"
        }
        
        register2_response = await test_client.post("/api/auth/register", json=org2_admin_data)
        login2_response = await test_client.post("/api/auth/login", json={
            "email": "admin2@org2.com",
            "password": "password_456"
        })
        token2 = login2_response.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # Create organization 2 directly in database
        org2 = Organization(
            name="Organization 2",
            subscription_tier="premium",
            cost_limit_monthly=Decimal("300.00")
        )
        test_db_session.add(org2)
        await test_db_session.commit()
        await test_db_session.refresh(org2)
        org2_id = str(org2.id)
        
        business2_response = await test_client.post("/api/businesses/", json={
            "name": "Org 2 Restaurant",
            "google_place_id": "ChIJOrg2",
            "category": "restaurant",
            "address": "Org 2 Street",
            "organization_id": org2_id
        }, headers=headers2)
        business2_id = business2_response.json()["id"]
        
        # Test data isolation
        
        # Org 1 admin should see only their business
        org1_businesses_response = await test_client.get("/api/businesses/", headers=headers1)
        org1_businesses = org1_businesses_response.json()
        org1_business_ids = [b["id"] for b in org1_businesses]
        
        assert business1_id in org1_business_ids
        assert business2_id not in org1_business_ids
        
        # Org 2 admin should see only their business
        org2_businesses_response = await test_client.get("/api/businesses/", headers=headers2)
        org2_businesses = org2_businesses_response.json()
        org2_business_ids = [b["id"] for b in org2_businesses]
        
        assert business2_id in org2_business_ids
        assert business1_id not in org2_business_ids
        
        # Org 1 admin should NOT be able to access Org 2's business
        cross_access_response = await test_client.get(f"/api/businesses/{business2_id}", headers=headers1)
        assert cross_access_response.status_code == 403
        
        # Org 2 admin should NOT be able to access Org 1's business
        cross_access_response2 = await test_client.get(f"/api/businesses/{business1_id}", headers=headers2)
        assert cross_access_response2.status_code == 403

    @pytest.mark.asyncio
    async def test_user_business_access_isolation(self, test_client: AsyncClient, clean_database, test_organization):
        """Test that users can only access businesses they have permission for."""
        # Create super admin
        super_admin_data = {
            "email": "superadmin@test.com",
            "name": "Super Admin",
            "role": "super_admin",
            "password": "admin_password",
            "language_preference": "en"
        }
        
        register_response = await test_client.post("/api/auth/register", json=super_admin_data)
        login_response = await test_client.post("/api/auth/login", json={
            "email": "superadmin@test.com",
            "password": "admin_password"
        })
        admin_token = login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Use test organization (created by fixture)
        org_id = str(test_organization.id)
        
        # Create 3 businesses
        business_ids = []
        for i in range(3):
            business_response = await test_client.post("/api/businesses/", json={
                "name": f"Test Restaurant {i+1}",
                "google_place_id": f"ChIJTest{i+1}",
                "category": "restaurant",
                "address": f"Test Street {i+1}",
                "organization_id": org_id
            }, headers=admin_headers)
            business_ids.append(business_response.json()["id"])
        
        # Create regular user
        user_data = {
            "email": "user@test.com",
            "name": "Regular User",
            "role": "admin",
            "password": "user_password",
            "language_preference": "en",
            "organization_id": org_id
        }
        
        user_response = await test_client.post("/api/users/", json=user_data, headers=admin_headers)
        user_id = user_response.json()["id"]
        
        # Grant access to only first 2 businesses
        for i in range(2):
            access_data = {
                "user_id": user_id,
                "business_id": business_ids[i],
                "permission_level": "full_access"
            }
            
            access_response = await test_client.post("/api/users/business-access", json=access_data, headers=admin_headers)
            assert access_response.status_code == 201
        
        # Login as regular user
        user_login_response = await test_client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "user_password"
        })
        user_token = user_login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Test access control
        
        # Should be able to access first business
        business1_response = await test_client.get(f"/api/businesses/{business_ids[0]}", headers=user_headers)
        assert business1_response.status_code == 200
        
        # Should be able to access second business
        business2_response = await test_client.get(f"/api/businesses/{business_ids[1]}", headers=user_headers)
        assert business2_response.status_code == 200
        
        # Should NOT be able to access third business
        business3_response = await test_client.get(f"/api/businesses/{business_ids[2]}", headers=user_headers)
        assert business3_response.status_code == 403
        
        # Should see only 2 businesses in list
        businesses_response = await test_client.get("/api/businesses/", headers=user_headers)
        accessible_businesses = businesses_response.json()
        assert len(accessible_businesses) == 2
        
        accessible_ids = [b["id"] for b in accessible_businesses]
        assert business_ids[0] in accessible_ids
        assert business_ids[1] in accessible_ids
        assert business_ids[2] not in accessible_ids