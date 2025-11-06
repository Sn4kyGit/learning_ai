"""
End-to-end tests for deployment scenarios and production workflows.

This module tests complete deployment scenarios including container startup,
service discovery, load balancing, and production user workflows.
"""

import pytest
import pytest_asyncio
import asyncio
import time
import json
import subprocess
import os
from typing import Dict, List, Any
from httpx import AsyncClient
from unittest.mock import patch, Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User, Business, Organization
from backend.tests.helpers.performance_helpers import PerformanceTester
from backend.tests.helpers.assertion_helpers import TestAssertions


class TestContainerDeployment:
    """Test container deployment scenarios."""

    @pytest.mark.skipif(
        not os.getenv("DOCKER_AVAILABLE"), 
        reason="Docker not available in test environment"
    )
    @pytest.mark.asyncio
    async def test_docker_container_startup(self, test_client: AsyncClient):
        """Test Docker container startup and health checks."""
        # This test would require Docker to be available
        # For CI/CD environments, this could be enabled with proper setup
        
        # Simulate container health check
        start_time = time.time()
        
        # Health check should succeed within startup timeout
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = await test_client.get("/health")
                if response.status_code == 200:
                    break
                await asyncio.sleep(1)
            except Exception:
                if attempt == max_attempts - 1:
                    pytest.fail("Container failed to start within timeout")
                await asyncio.sleep(1)
        
        startup_time = time.time() - start_time
        assert startup_time < 60  # Should start within 60 seconds

    @pytest.mark.asyncio
    async def test_environment_variable_configuration(self, test_client: AsyncClient):
        """Test environment variable configuration in deployment."""
        # Test that app responds correctly with environment configuration
        response = await test_client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "environment" in data
        
        # Test configuration endpoint
        config_response = await test_client.get("/api/health/config")
        assert config_response.status_code == 200
        
        config_data = config_response.json()
        assert "database_url" in config_data["config"]
        assert "redis_url" in config_data["config"]

    @pytest.mark.asyncio
    async def test_multi_instance_deployment(self, test_client: AsyncClient):
        """Test multi-instance deployment behavior."""
        # Simulate multiple instances by testing the same client multiple times
        # In a real deployment, this would test multiple actual instances
        
        # All instances should be healthy
        for i in range(3):
            response = await test_client.get("/api/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_database_migration_on_startup(self, test_db_session: AsyncSession):
        """Test database migration behavior during deployment."""
        # This would typically test Alembic migrations
        # For now, we'll test that the database schema is correct
        
        # Test that all required tables exist
        result = await test_db_session.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = [row[0] for row in result.fetchall()]
        
        required_tables = [
            "organizations", "users", "businesses", "reviews", 
            "classifications", "user_business_access", "daily_analytics"
        ]
        
        for table in required_tables:
            assert table in tables, f"Required table {table} not found"

    @pytest.mark.asyncio
    async def test_graceful_shutdown_behavior(self, test_client: AsyncClient):
        """Test graceful shutdown behavior."""
        # Test that the application handles shutdown signals properly
        # This is more of a smoke test since we can't actually send signals
        
        response = await test_client.get("/api/health")
        assert response.status_code == 200
        
        # Test shutdown endpoint (should require admin auth)
        shutdown_response = await test_client.post("/api/admin/shutdown")
        assert shutdown_response.status_code in [401, 403]


class TestLoadBalancerScenarios:
    """Test load balancer and high availability scenarios."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint_performance(self, test_client: AsyncClient):
        """Test health check endpoint performance for load balancers."""
        # Health checks should be very fast
        response_times = []
        for _ in range(10):
            start_time = time.time()
            response = await test_client.get("/health")
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # Average response time should be under 50ms
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 0.05

    @pytest.mark.asyncio
    async def test_session_affinity_handling(self, test_client: AsyncClient):
        """Test session affinity and sticky sessions."""
        # Test that sessions work correctly across requests
        # First, create a user session
        register_response = await test_client.post("/api/auth/register", json={
            "email": "session@test.com",
            "name": "Session Test",
            "role": "admin",
            "password": "password123",
            "language_preference": "en"
        })
        
        if register_response.status_code == 201:
            # Login to get session
            login_response = await test_client.post("/api/auth/login", json={
                "email": "session@test.com",
                "password": "password123"
            })
            
            if login_response.status_code == 200:
                token = login_response.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Make multiple requests with the same session
                for _ in range(5):
                    response = await test_client.get("/api/auth/me", headers=headers)
                    assert response.status_code == 200
                    assert response.json()["email"] == "session@test.com"

    @pytest.mark.asyncio
    async def test_load_balancer_headers(self, test_client: AsyncClient):
        """Test load balancer header handling."""
        # Test X-Forwarded headers
        response = await test_client.get("/api/health", headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "businessbot.example.com",
            "X-Real-IP": "192.168.1.100"
        })
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, test_client: AsyncClient):
        """Test concurrent request handling under load."""
        # Simulate concurrent requests
        async def make_request():
            try:
                response = await test_client.get("/api/health")
                return response.status_code
            except Exception as e:
                return str(e)
        
        # Create 20 concurrent tasks
        tasks = [make_request() for _ in range(20)]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Check results
        status_codes = [r for r in results if isinstance(r, int)]
        
        # All requests should succeed
        assert len(status_codes) == 20
        assert all(code == 200 for code in status_codes)


class TestKubernetesDeployment:
    """Test Kubernetes deployment scenarios."""

    @pytest.mark.asyncio
    async def test_pod_readiness_probe(self, test_client: AsyncClient):
        """Test Kubernetes readiness probe behavior."""
        # Readiness probe should check all dependencies
        response = await test_client.get("/health/readiness")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "checks" in data
        
        # Should check database and Redis
        assert "database" in data["checks"]
        assert "redis" in data["checks"]

    @pytest.mark.asyncio
    async def test_pod_liveness_probe(self, test_client: AsyncClient):
        """Test Kubernetes liveness probe behavior."""
        # Liveness probe should be simple and fast
        start_time = time.time()
        response = await test_client.get("/health/liveness")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 0.1  # Should be very fast
        
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_startup_probe_behavior(self, test_client: AsyncClient):
        """Test Kubernetes startup probe behavior."""
        # Startup probe allows more time for initialization
        response = await test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_horizontal_pod_autoscaler_metrics(self, test_client: AsyncClient):
        """Test metrics used by Horizontal Pod Autoscaler."""
        # Generate some load to create metrics
        for _ in range(10):
            await test_client.get("/api/health")
        
        # Check metrics endpoint
        metrics_response = await test_client.get("/api/metrics")
        assert metrics_response.status_code == 200
        
        metrics_text = metrics_response.text
        
        # Should include CPU and memory metrics
        assert "process_resident_memory_bytes" in metrics_text or "memory" in metrics_text
        assert "process_cpu_seconds_total" in metrics_text or "cpu" in metrics_text

    @pytest.mark.asyncio
    async def test_service_discovery(self, test_client: AsyncClient):
        """Test Kubernetes service discovery."""
        # Test that the service can be discovered
        response = await test_client.get("/api/health")
        assert response.status_code == 200
        
        # Test service endpoints
        version_response = await test_client.get("/api/version")
        assert version_response.status_code == 200

    @pytest.mark.asyncio
    async def test_config_map_integration(self, test_client: AsyncClient):
        """Test ConfigMap integration."""
        # Test that configuration is loaded correctly
        response = await test_client.get("/api/health/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "config" in data
        
        # Should have environment-specific configuration
        assert "environment" in data["config"]

    @pytest.mark.asyncio
    async def test_secret_management(self, test_client: AsyncClient):
        """Test Kubernetes secret management."""
        # Test that secrets are loaded but not exposed
        response = await test_client.get("/api/health/config")
        assert response.status_code == 200
        
        data = response.json()
        
        # Secrets should be masked or not exposed
        if "database_url" in data["config"]:
            assert "***" in data["config"]["database_url"] or data["config"]["database_url"] == "configured"


class TestProductionWorkflows:
    """Test complete production workflows and scenarios."""

    @pytest.mark.asyncio
    async def test_complete_production_user_journey(self, test_client: AsyncClient, clean_database):
        """Test complete user journey in production-like environment."""
        # Step 1: User registration with production validation
        registration_data = {
            "email": "production.user@company.com",
            "name": "Production User",
            "role": "admin",
            "password": "SecurePassword123!",
            "language_preference": "en"
        }
        
        register_response = await test_client.post("/api/auth/register", json=registration_data)
        assert register_response.status_code == 201
        
        # Step 2: Login with rate limiting consideration
        login_data = {
            "email": "production.user@company.com",
            "password": "SecurePassword123!"
        }
        
        login_response = await test_client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Create organization with production constraints
        org_data = {
            "name": "Production Restaurant Group",
            "subscription_tier": "enterprise",
            "cost_limit_monthly": 1000.00
        }
        
        org_response = await test_client.post("/api/organizations/", json=org_data, headers=headers)
        assert org_response.status_code == 201
        org_id = org_response.json()["id"]
        
        # Step 4: Register business with Google Places validation
        business_data = {
            "name": "Production Test Restaurant",
            "google_place_id": "ChIJProd123456789",
            "category": "restaurant",
            "address": "123 Production Street, Business City",
            "organization_id": org_id
        }
        
        business_response = await test_client.post("/api/businesses/", json=business_data, headers=headers)
        assert business_response.status_code == 201
        business_id = business_response.json()["id"]
        
        # Step 5: Import reviews with production volume
        with patch('backend.external.google_places.GooglePlacesClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Generate realistic production review data
            production_reviews = []
            for i in range(100):  # Production-like volume
                production_reviews.append({
                    "author_name": f"Customer {i}",
                    "rating": (i % 5) + 1,
                    "text": f"Production review {i}. This is a realistic review with proper content length and structure.",
                    "time": int(time.time()) - (i * 3600),  # Spread over time
                    "review_id": f"prod_review_{i}"
                })
            
            mock_client.get_place_reviews.return_value = production_reviews
            
            # Test import performance
            start_time = time.time()
            import_response = await test_client.post(
                f"/api/businesses/{business_id}/import-reviews",
                json={"max_reviews": 100, "force_refresh": False},
                headers=headers
            )
            import_time = time.time() - start_time
            
            assert import_response.status_code == 200
            assert import_time < 30  # Should complete within 30 seconds
        
        # Step 6: Test analytics performance with production data
        start_time = time.time()
        analytics_response = await test_client.get(f"/api/analytics/{business_id}/dashboard", headers=headers)
        analytics_time = time.time() - start_time
        
        assert analytics_response.status_code == 200
        assert analytics_time < 2  # Should load within 2 seconds
        
        analytics_data = analytics_response.json()
        assert analytics_data["total_reviews"] >= 100
        
        # Step 7: Test chat performance
        chat_request = {
            "message": "Analyze my restaurant's performance based on the recent reviews and provide actionable insights.",
            "language": "en"
        }
        
        start_time = time.time()
        chat_response = await test_client.post(f"/api/chat/{business_id}", json=chat_request, headers=headers)
        chat_time = time.time() - start_time
        
        assert chat_response.status_code == 200
        assert chat_time < 10  # Should respond within 10 seconds
        
        # Step 8: Test report generation
        report_request = {
            "report_type": "weekly",
            "language": "en",
            "include_action_items": True
        }
        
        start_time = time.time()
        report_response = await test_client.post(
            f"/api/reports/{business_id}/generate",
            json=report_request,
            headers=headers
        )
        report_time = time.time() - start_time
        
        assert report_response.status_code == 200
        assert report_time < 15  # Should generate within 15 seconds

    @pytest.mark.asyncio
    async def test_high_availability_scenario(self, test_client: AsyncClient, clean_database):
        """Test high availability scenarios with failover."""
        # Simulate database connection issues
        with patch('backend.db.database.get_db_session') as mock_db:
            # First few calls fail, then succeed (simulating recovery)
            mock_db.side_effect = [
                Exception("Database connection failed"),
                Exception("Database connection failed"),
                AsyncMock()  # Recovery
            ]
            
            # Health check should handle failures gracefully
            for attempt in range(3):
                try:
                    response = await test_client.get("/api/health/readiness")
                    if response.status_code == 200:
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.1)
            
            # Should eventually recover
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_security_in_production(self, test_client: AsyncClient):
        """Test security measures in production environment."""
        # Test security headers
        response = await test_client.get("/api/health")
        headers = response.headers
        
        # Check for security headers
        security_headers = [
            "x-content-type-options",
            "x-frame-options", 
            "x-xss-protection"
        ]
        
        for header in security_headers:
            assert header in headers or header.upper() in headers
        
        # Test that sensitive endpoints require authentication
        sensitive_endpoints = [
            "/api/admin/users",
            "/api/admin/stats", 
            "/api/admin/logs"
        ]
        
        for endpoint in sensitive_endpoints:
            response = await test_client.get(endpoint)
            assert response.status_code in [401, 403, 404]  # Should not be accessible without auth

    @pytest.mark.asyncio
    async def test_performance_under_load(self, test_client: AsyncClient, clean_database):
        """Test performance under production load."""
        # Create test user for load testing
        register_response = await test_client.post("/api/auth/register", json={
            "email": "load@test.com",
            "name": "Load Test",
            "role": "admin", 
            "password": "password123",
            "language_preference": "en"
        })
        
        if register_response.status_code == 201:
            login_response = await test_client.post("/api/auth/login", json={
                "email": "load@test.com",
                "password": "password123"
            })
            
            if login_response.status_code == 200:
                token = login_response.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Simulate concurrent users
                async def simulate_user_activity():
                    try:
                        # Simulate typical user workflow
                        await test_client.get("/api/businesses/", headers=headers)
                        await test_client.get("/api/health")
                        return "success"
                    except Exception as e:
                        return f"error: {e}"
                
                # Create 50 concurrent users
                start_time = time.time()
                
                tasks = [simulate_user_activity() for _ in range(50)]
                results = await asyncio.gather(*tasks)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Collect results
                success_count = sum(1 for r in results if r == "success")
                error_count = len(results) - success_count
                
                # Performance assertions
                assert total_time < 30  # Should complete within 30 seconds
                assert success_count >= 45  # At least 90% success rate
                assert error_count <= 5  # No more than 10% errors

    @pytest.mark.asyncio
    async def test_monitoring_and_alerting_integration(self, test_client: AsyncClient):
        """Test monitoring and alerting integration."""
        # Test metrics endpoint
        metrics_response = await test_client.get("/api/metrics")
        assert metrics_response.status_code == 200
        
        metrics_text = metrics_response.text
        
        # Should include business metrics
        expected_metrics = [
            "http_requests_total",
            "http_request_duration_seconds",
            "database_connections"
        ]
        
        for metric in expected_metrics:
            assert metric in metrics_text or "businessbot_" in metrics_text
        
        # Test health endpoints for monitoring
        health_endpoints = [
            "/api/health",
            "/api/health/liveness", 
            "/api/health/readiness"
        ]
        
        for endpoint in health_endpoints:
            response = await test_client.get(endpoint)
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_backup_and_recovery_integration(self, test_client: AsyncClient, clean_database):
        """Test backup and recovery integration in production."""
        # Test backup health endpoint
        backup_response = await test_client.get("/api/health/backup")
        
        # Should either work or require authentication
        assert backup_response.status_code in [200, 401, 403]
        
        if backup_response.status_code == 200:
            data = backup_response.json()
            assert "backup_status" in data
        
        # Test that backup service is configured
        config_response = await test_client.get("/api/health/config")
        assert config_response.status_code == 200
        
        config_data = config_response.json()
        # Should have backup configuration
        assert "config" in config_data

    @pytest.mark.asyncio
    async def test_log_aggregation_integration(self, test_client: AsyncClient):
        """Test log aggregation and monitoring integration."""
        # Generate some log entries
        await test_client.get("/api/health")
        await test_client.post("/api/auth/login", json={"email": "invalid", "password": "invalid"})
        
        # Test log endpoint (should require admin access)
        logs_response = await test_client.get("/api/admin/logs")
        assert logs_response.status_code in [401, 403]
        
        # Test log level endpoint
        log_level_response = await test_client.get("/api/admin/log-level")
        assert log_level_response.status_code in [401, 403]


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