"""
Integration tests for business management endpoints.

This module tests the complete business CRUD operations,
Google Places integration, and business access control.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import patch, AsyncMock

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
async def test_admin_user(test_db_session: AsyncSession, test_organization):
    """Create test admin user."""
    auth_service = AuthService(test_db_session)
    password = "password123"
    hashed_password = auth_service.hash_password(password)
    
    user = User(
        email="admin@restaurant.com",
        name="Restaurant Admin",
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
async def auth_headers(client, test_admin_user):
    """Get authentication headers for test user."""
    login_data = {
        "email": test_admin_user["user"].email,
        "password": test_admin_user["password"]
    }
    login_response = client.post("/api/auth/login", json=login_data)
    token = login_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


class TestBusinessCRUD:
    """Test suite for business CRUD operations."""

    def test_create_business_success(self, client, auth_headers, test_organization):
        """Test successful business creation."""
        # Arrange
        business_data = {
            "name": "New Restaurant",
            "google_place_id": "ChIJNew123",
            "category": "restaurant",
            "address": "456 New Street, New City",
            "organization_id": str(test_organization.id)
        }
        
        # Act
        response = client.post(
            "/api/businesses/",
            json=business_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Restaurant"
        assert data["google_place_id"] == "ChIJNew123"
        assert data["category"] == "restaurant"
        assert data["address"] == "456 New Street, New City"

    def test_create_business_invalid_data(self, client, auth_headers):
        """Test business creation with invalid data."""
        # Arrange
        business_data = {
            "name": "",  # Invalid: empty name
            "google_place_id": "ChIJTest123"
        }
        
        # Act
        response = client.post(
            "/api/businesses/",
            json=business_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_create_business_unauthorized(self, client):
        """Test business creation without authentication."""
        # Arrange
        business_data = {
            "name": "Unauthorized Restaurant",
            "google_place_id": "ChIJUnauth123"
        }
        
        # Act
        response = client.post("/api/businesses/", json=business_data)
        
        # Assert
        assert response.status_code == 403  # Unauthorized

    def test_list_businesses_success(self, client, auth_headers, test_business):
        """Test successful business listing."""
        # Act
        response = client.get("/api/businesses/", headers=auth_headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check if test business is in the list
        business_names = [b["name"] for b in data]
        assert test_business.name in business_names

    def test_list_businesses_with_pagination(self, client, auth_headers):
        """Test business listing with pagination parameters."""
        # Act
        response = client.get(
            "/api/businesses/?skip=0&limit=10",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_get_business_success(self, client, auth_headers, test_business):
        """Test successful business retrieval."""
        # Act
        response = client.get(
            f"/api/businesses/{test_business.id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_business.id)
        assert data["name"] == test_business.name
        assert data["google_place_id"] == test_business.google_place_id

    def test_get_business_not_found(self, client, auth_headers):
        """Test business retrieval with non-existent ID."""
        # Arrange
        fake_id = str(uuid4())
        
        # Act
        response = client.get(
            f"/api/businesses/{fake_id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404

    def test_update_business_success(self, client, auth_headers, test_business):
        """Test successful business update."""
        # Arrange
        update_data = {
            "name": "Updated Restaurant Name",
            "category": "fine_dining",
            "address": "789 Updated Street, Updated City"
        }
        
        # Act
        response = client.put(
            f"/api/businesses/{test_business.id}",
            json=update_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Restaurant Name"
        assert data["category"] == "fine_dining"
        assert data["address"] == "789 Updated Street, Updated City"

    def test_update_business_not_found(self, client, auth_headers):
        """Test business update with non-existent ID."""
        # Arrange
        fake_id = str(uuid4())
        update_data = {"name": "Non-existent Restaurant"}
        
        # Act
        response = client.put(
            f"/api/businesses/{fake_id}",
            json=update_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404

    def test_delete_business_success(self, client, auth_headers, test_business):
        """Test successful business deletion."""
        # Act
        response = client.delete(
            f"/api/businesses/{test_business.id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 204

    def test_delete_business_not_found(self, client, auth_headers):
        """Test business deletion with non-existent ID."""
        # Arrange
        fake_id = str(uuid4())
        
        # Act
        response = client.delete(
            f"/api/businesses/{fake_id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404


class TestGooglePlacesIntegration:
    """Test suite for Google Places integration."""

    @patch('backend.external.google_places.GooglePlacesClient')
    def test_import_reviews_success(self, mock_client_class, client, auth_headers, test_business):
        """Test successful review import from Google Places."""
        # Arrange
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock successful import result
        mock_import_result = AsyncMock()
        mock_import_result.imported_count = 25
        mock_import_result.skipped_count = 5
        mock_import_result.total_processed = 30
        mock_import_result.errors = []
        
        with patch('backend.services.review_import_service.ReviewImportService.import_reviews_for_business', 
                   return_value=mock_import_result):
            
            import_request = {
                "max_reviews": 50,
                "force_refresh": False
            }
            
            # Act
            response = client.post(
                f"/api/businesses/{test_business.id}/import-reviews",
                json=import_request,
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["imported_count"] == 25
            assert data["skipped_count"] == 5
            assert data["total_processed"] == 30
            assert data["errors"] == []

    @patch('backend.external.google_places.GooglePlacesClient')
    def test_import_reviews_with_errors(self, mock_client_class, client, auth_headers, test_business):
        """Test review import with some errors."""
        # Arrange
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock import result with errors
        mock_import_result = AsyncMock()
        mock_import_result.imported_count = 20
        mock_import_result.skipped_count = 8
        mock_import_result.total_processed = 30
        mock_import_result.errors = ["API rate limit exceeded", "Invalid review format"]
        
        with patch('backend.services.review_import_service.ReviewImportService.import_reviews_for_business', 
                   return_value=mock_import_result):
            
            import_request = {
                "max_reviews": 30,
                "force_refresh": True
            }
            
            # Act
            response = client.post(
                f"/api/businesses/{test_business.id}/import-reviews",
                json=import_request,
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["imported_count"] == 20
            assert data["skipped_count"] == 8
            assert len(data["errors"]) == 2

    def test_import_reviews_invalid_request(self, client, auth_headers, test_business):
        """Test review import with invalid request data."""
        # Arrange
        import_request = {
            "max_reviews": 1000,  # Exceeds limit
            "force_refresh": "invalid"  # Wrong type
        }
        
        # Act
        response = client.post(
            f"/api/businesses/{test_business.id}/import-reviews",
            json=import_request,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error

    @patch('backend.services.review_import_service.ReviewImportService.get_google_places_info')
    def test_get_google_places_info_success(self, mock_get_info, client, auth_headers, test_business):
        """Test successful Google Places info retrieval."""
        # Arrange
        mock_places_info = {
            "name": "Test Restaurant",
            "rating": 4.2,
            "user_ratings_total": 150,
            "formatted_address": "123 Test Street, Test City",
            "types": ["restaurant", "food", "establishment"]
        }
        mock_get_info.return_value = mock_places_info
        
        # Act
        response = client.get(
            f"/api/businesses/{test_business.id}/google-places-info",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["business_id"] == str(test_business.id)
        assert data["google_place_id"] == test_business.google_place_id
        assert data["places_info"]["name"] == "Test Restaurant"
        assert data["places_info"]["rating"] == 4.2

    @patch('backend.services.review_import_service.ReviewImportService.get_import_status')
    def test_get_import_status_success(self, mock_get_status, client, auth_headers, test_business):
        """Test successful import status retrieval."""
        # Arrange
        mock_status = {
            "last_import": "2024-01-15T10:30:00Z",
            "total_imported": 150,
            "last_import_count": 25,
            "next_scheduled_import": "2024-01-16T00:00:00Z",
            "import_errors": []
        }
        mock_get_status.return_value = mock_status
        
        # Act
        response = client.get(
            f"/api/businesses/{test_business.id}/import-status",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["business_id"] == str(test_business.id)
        assert data["total_imported"] == 150
        assert data["last_import_count"] == 25
        assert data["import_errors"] == []


class TestBusinessAccessControl:
    """Test suite for business access control."""

    def test_unauthorized_access_denied(self, client, test_business):
        """Test that unauthorized users cannot access business endpoints."""
        # Act
        response = client.get(f"/api/businesses/{test_business.id}")
        
        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_role_read_only_access(self, client, test_db_session, test_business):
        """Test that viewer role has read-only access."""
        # Arrange - Create viewer user
        auth_service = AuthService(test_db_session)
        password = "password123"
        hashed_password = auth_service.hash_password(password)
        
        viewer_user = User(
            email="viewer@restaurant.com",
            name="Restaurant Viewer",
            role="viewer",
            password_hash=hashed_password
        )
        
        test_db_session.add(viewer_user)
        await test_db_session.commit()
        
        # Login to get token
        login_data = {"email": "viewer@restaurant.com", "password": password}
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Act - Try to read business (should work)
        read_response = client.get(f"/api/businesses/{test_business.id}", headers=headers)
        
        # Act - Try to delete business (should fail)
        delete_response = client.delete(f"/api/businesses/{test_business.id}", headers=headers)
        
        # Assert
        assert read_response.status_code == 200  # Read access allowed
        assert delete_response.status_code == 403  # Write access denied

    def test_organization_filtering(self, client, auth_headers, test_organization):
        """Test that businesses are filtered by organization."""
        # Act
        response = client.get(
            f"/api/businesses/?organization_id={test_organization.id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # All returned businesses should belong to the test organization
        for business in data:
            assert business["organization_id"] == str(test_organization.id)


class TestBusinessValidation:
    """Test suite for business data validation."""

    def test_create_business_missing_required_fields(self, client, auth_headers):
        """Test business creation with missing required fields."""
        # Arrange
        business_data = {
            "name": "Test Restaurant"
            # Missing google_place_id
        }
        
        # Act
        response = client.post(
            "/api/businesses/",
            json=business_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422

    def test_create_business_invalid_field_types(self, client, auth_headers):
        """Test business creation with invalid field types."""
        # Arrange
        business_data = {
            "name": 123,  # Should be string
            "google_place_id": "ChIJTest123",
            "organization_id": "not-a-uuid"  # Should be valid UUID
        }
        
        # Act
        response = client.post(
            "/api/businesses/",
            json=business_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422

    def test_update_business_partial_data(self, client, auth_headers, test_business):
        """Test business update with partial data."""
        # Arrange
        update_data = {
            "name": "Partially Updated Restaurant"
            # Only updating name, other fields should remain unchanged
        }
        
        # Act
        response = client.put(
            f"/api/businesses/{test_business.id}",
            json=update_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Partially Updated Restaurant"
        assert data["google_place_id"] == test_business.google_place_id  # Unchanged
        assert data["category"] == test_business.category  # Unchanged


class TestBusinessPerformance:
    """Test suite for business endpoint performance."""

    def test_list_businesses_response_time(self, client, auth_headers):
        """Test that business listing responds within acceptable time."""
        import time
        
        # Act
        start_time = time.time()
        response = client.get("/api/businesses/", headers=auth_headers)
        end_time = time.time()
        
        # Assert
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 0.5  # Should respond within 500ms

    def test_get_business_response_time(self, client, auth_headers, test_business):
        """Test that individual business retrieval responds within acceptable time."""
        import time
        
        # Act
        start_time = time.time()
        response = client.get(f"/api/businesses/{test_business.id}", headers=auth_headers)
        end_time = time.time()
        
        # Assert
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 0.3  # Should respond within 300ms