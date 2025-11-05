"""
Unit tests for health check endpoints.

This module tests the health check functionality to ensure
the API is responding correctly.
"""

# Removed unused import
from fastapi.testclient import TestClient

from backend.main import app


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_basic_health_check(self):
        """Test basic health check endpoint returns 200."""
        client = TestClient(app)
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
        assert data["database"] == "not_checked"

    def test_liveness_check(self):
        """Test liveness probe endpoint."""
        client = TestClient(app)
        response = client.get("/api/health/liveness")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_version_endpoint(self):
        """Test version information endpoint."""
        client = TestClient(app)
        response = client.get("/api/version")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0.0"
        assert "environment" in data
        assert "timestamp" in data
