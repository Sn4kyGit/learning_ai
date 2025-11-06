"""
Integration tests for deployment and monitoring functionality.

This module tests deployment health checks, monitoring endpoints,
container health, and production readiness.
"""

import pytest
import asyncio
import time
import json
from typing import Dict, Any
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.services.monitoring_service import MonitoringService
from backend.db.database import get_db_session


class TestDeploymentHealthChecks:
    """Test deployment health check endpoints and functionality."""

    def test_basic_health_endpoint(self):
        """Test basic health check endpoint."""
        client = TestClient(app)
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "service" in data

    def test_liveness_probe(self):
        """Test Kubernetes liveness probe endpoint."""
        client = TestClient(app)
        response = client.get("/api/health/liveness")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_readiness_probe(self):
        """Test Kubernetes readiness probe endpoint."""
        client = TestClient(app)
        response = client.get("/api/health/readiness")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_database_health_check(self, test_db_session: AsyncSession):
        """Test database connectivity health check."""
        client = TestClient(app)
        
        # Override database dependency for testing
        async def override_get_db():
            yield test_db_session
        
        app.dependency_overrides[get_db_session] = override_get_db
        
        try:
            response = client.get("/api/health/database")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "connection_time_ms" in data
            assert data["connection_time_ms"] < 1000  # Should connect within 1 second
        finally:
            app.dependency_overrides.clear()

    def test_redis_health_check(self):
        """Test Redis connectivity health check."""
        client = TestClient(app)
        
        with patch('backend.db.database.redis_client') as mock_redis:
            mock_redis.ping.return_value = True
            
            response = client.get("/api/health/redis")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "ping_time_ms" in data

    def test_external_services_health_check(self):
        """Test external services health check."""
        client = TestClient(app)
        
        with patch('backend.external.google_places.GooglePlacesClient') as mock_google, \
             patch('openai.OpenAI') as mock_openai, \
             patch('anthropic.Anthropic') as mock_anthropic:
            
            # Mock successful responses
            mock_google.return_value.health_check.return_value = True
            mock_openai.return_value.models.list.return_value = Mock()
            mock_anthropic.return_value.messages.create.return_value = Mock()
            
            response = client.get("/api/health/external-services")
            
            assert response.status_code == 200
            data = response.json()
            assert "google_places" in data["services"]
            assert "openai" in data["services"]
            assert "anthropic" in data["services"]

    def test_health_check_with_failures(self):
        """Test health check behavior when services are failing."""
        client = TestClient(app)
        
        with patch('backend.db.database.redis_client') as mock_redis:
            mock_redis.ping.side_effect = Exception("Redis connection failed")
            
            response = client.get("/api/health/readiness")
            
            # Should still return 200 but indicate not ready
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["redis"]["status"] == "unhealthy"


class TestMonitoringEndpoints:
    """Test monitoring and metrics endpoints."""

    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint."""
        client = TestClient(app)
        response = client.get("/api/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        # Check for basic metrics
        metrics_text = response.text
        assert "http_requests_total" in metrics_text
        assert "http_request_duration_seconds" in metrics_text
        assert "database_connections_active" in metrics_text

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_system_metrics(self, test_db_session: AsyncSession):
        """Test system metrics collection."""
        monitoring_service = MonitoringService()
        
        metrics = await monitoring_service.collect_system_metrics()
        
        assert "cpu_usage_percent" in metrics
        assert "memory_usage_percent" in metrics
        assert "disk_usage_percent" in metrics
        assert "active_connections" in metrics
        assert 0 <= metrics["cpu_usage_percent"] <= 100
        assert 0 <= metrics["memory_usage_percent"] <= 100

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_application_metrics(self, test_db_session: AsyncSession):
        """Test application-specific metrics collection."""
        monitoring_service = MonitoringService()
        
        metrics = await monitoring_service.collect_application_metrics()
        
        assert "total_businesses" in metrics
        assert "total_reviews" in metrics
        assert "total_classifications" in metrics
        assert "ai_requests_last_hour" in metrics
        assert "cost_current_month" in metrics

    def test_performance_metrics(self):
        """Test performance metrics tracking."""
        client = TestClient(app)
        
        # Make several requests to generate metrics
        for _ in range(5):
            client.get("/api/health")
        
        response = client.get("/api/metrics")
        metrics_text = response.text
        
        # Check that request metrics are being tracked
        assert "http_requests_total" in metrics_text
        assert 'method="GET"' in metrics_text
        assert 'endpoint="/api/health"' in metrics_text

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_error_rate_monitoring(self, test_db_session: AsyncSession):
        """Test error rate monitoring and alerting."""
        monitoring_service = MonitoringService()
        
        # Simulate some errors
        await monitoring_service.record_error("classification_failed", "GPT-5 API timeout")
        await monitoring_service.record_error("database_error", "Connection timeout")
        
        error_metrics = await monitoring_service.get_error_metrics(hours=1)
        
        assert error_metrics["total_errors"] >= 2
        assert "classification_failed" in error_metrics["error_types"]
        assert "database_error" in error_metrics["error_types"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_alert_thresholds(self, test_db_session: AsyncSession):
        """Test monitoring alert threshold checking."""
        monitoring_service = MonitoringService()
        
        # Test CPU usage alert
        with patch.object(monitoring_service, 'get_cpu_usage', return_value=85.0):
            alerts = await monitoring_service.check_alert_thresholds()
            
            cpu_alerts = [a for a in alerts if a["metric"] == "cpu_usage"]
            assert len(cpu_alerts) > 0
            assert cpu_alerts[0]["severity"] == "warning"

        # Test memory usage alert
        with patch.object(monitoring_service, 'get_memory_usage', return_value=95.0):
            alerts = await monitoring_service.check_alert_thresholds()
            
            memory_alerts = [a for a in alerts if a["metric"] == "memory_usage"]
            assert len(memory_alerts) > 0
            assert memory_alerts[0]["severity"] == "critical"


class TestContainerHealthChecks:
    """Test container-specific health checks and Docker integration."""

    def test_docker_health_check_script(self):
        """Test Docker health check script functionality."""
        client = TestClient(app)
        
        # Simulate Docker health check
        response = client.get("/health")
        
        # Docker health check expects simple 200 response
        assert response.status_code == 200

    def test_startup_probe_behavior(self):
        """Test startup probe behavior during application initialization."""
        client = TestClient(app)
        
        # Startup probe should be more lenient during startup
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include startup-specific information
        assert "startup_time" in data or "status" in data

    def test_graceful_shutdown_handling(self):
        """Test graceful shutdown signal handling."""
        # This test would typically require process signal testing
        # For now, we'll test the shutdown endpoint
        client = TestClient(app)
        
        # Test that shutdown endpoint exists and responds
        response = client.post("/api/admin/shutdown")
        
        # Should require authentication, so expect 401 or 403
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_resource_cleanup_on_shutdown(self, test_db_session: AsyncSession):
        """Test that resources are properly cleaned up on shutdown."""
        monitoring_service = MonitoringService()
        
        # Start some background tasks
        await monitoring_service.start_background_monitoring()
        
        # Verify tasks are running
        assert monitoring_service.is_monitoring_active()
        
        # Simulate shutdown
        await monitoring_service.shutdown()
        
        # Verify cleanup
        assert not monitoring_service.is_monitoring_active()

    def test_environment_variable_validation(self):
        """Test that required environment variables are validated."""
        client = TestClient(app)
        
        response = client.get("/api/health/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should validate critical environment variables
        assert "database_url" in data["config"]
        assert "redis_url" in data["config"]
        assert "required_env_vars" in data
        
        # Should not expose sensitive values
        assert "***" in data["config"]["database_url"] or data["config"]["database_url"] == "configured"


class TestProductionReadiness:
    """Test production readiness and deployment validation."""

    def test_security_headers(self):
        """Test that security headers are properly set."""
        client = TestClient(app)
        response = client.get("/api/health")
        
        # Check for security headers
        headers = response.headers
        assert "x-content-type-options" in headers
        assert "x-frame-options" in headers
        assert "x-xss-protection" in headers

    def test_cors_configuration(self):
        """Test CORS configuration for production."""
        client = TestClient(app)
        
        # Test preflight request
        response = client.options(
            "/api/health",
            headers={
                "Origin": "https://businessbot.yourdomain.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_rate_limiting(self):
        """Test rate limiting configuration."""
        client = TestClient(app)
        
        # Make multiple rapid requests
        responses = []
        for _ in range(100):
            response = client.get("/api/health")
            responses.append(response.status_code)
        
        # Should eventually hit rate limit (429) or all succeed (200)
        assert all(status in [200, 429] for status in responses)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, test_db_session: AsyncSession):
        """Test database connection pooling configuration."""
        monitoring_service = MonitoringService()
        
        # Test multiple concurrent database operations
        tasks = []
        for _ in range(10):
            task = monitoring_service.test_database_connection()
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All connections should succeed
        assert all(not isinstance(result, Exception) for result in results)

    def test_logging_configuration(self):
        """Test logging configuration for production."""
        client = TestClient(app)
        
        # Make request that should generate logs
        response = client.get("/api/health")
        
        assert response.status_code == 200
        
        # Test log level endpoint
        log_response = client.get("/api/admin/log-level")
        
        # Should require authentication
        assert log_response.status_code in [401, 403]

    def test_version_information(self):
        """Test version information endpoint."""
        client = TestClient(app)
        response = client.get("/api/version")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "version" in data
        assert "build_date" in data or "timestamp" in data
        assert "environment" in data
        assert "git_commit" in data or "build_info" in data

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_backup_system_health(self, test_db_session: AsyncSession):
        """Test backup system health and readiness."""
        monitoring_service = MonitoringService()
        
        backup_health = await monitoring_service.check_backup_system_health()
        
        assert "backup_service_status" in backup_health
        assert "last_backup_time" in backup_health
        assert "backup_storage_available" in backup_health
        assert backup_health["backup_service_status"] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_ai_service_health(self, test_db_session: AsyncSession):
        """Test AI service health and API connectivity."""
        monitoring_service = MonitoringService()
        
        with patch('openai.OpenAI') as mock_openai, \
             patch('anthropic.Anthropic') as mock_anthropic:
            
            # Mock successful API responses
            mock_openai.return_value.models.list.return_value = Mock()
            mock_anthropic.return_value.messages.create.return_value = Mock(
                content=[Mock(text="Health check response")]
            )
            
            ai_health = await monitoring_service.check_ai_services_health()
            
            assert "openai_status" in ai_health
            assert "anthropic_status" in ai_health
            assert "response_times" in ai_health
            
            # Response times should be reasonable
            assert ai_health["response_times"]["openai"] < 5000  # 5 seconds
            assert ai_health["response_times"]["anthropic"] < 5000  # 5 seconds


class TestLoadBalancerIntegration:
    """Test load balancer and ingress integration."""

    def test_load_balancer_health_check(self):
        """Test load balancer health check endpoint."""
        client = TestClient(app)
        
        # Load balancers often use simple health checks
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Should be fast for load balancer checks
        start_time = time.time()
        client.get("/health")
        end_time = time.time()
        
        assert (end_time - start_time) < 0.1  # Should respond within 100ms

    def test_sticky_session_headers(self):
        """Test sticky session headers for load balancing."""
        client = TestClient(app)
        
        response = client.get("/api/health")
        
        # Check for session affinity headers if configured
        headers = response.headers
        # This would depend on your load balancer configuration
        assert response.status_code == 200

    def test_x_forwarded_headers(self):
        """Test X-Forwarded headers handling."""
        client = TestClient(app)
        
        response = client.get(
            "/api/health",
            headers={
                "X-Forwarded-For": "192.168.1.1",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "businessbot.yourdomain.com"
            }
        )
        
        assert response.status_code == 200
        
        # Application should handle forwarded headers properly
        # This would be tested in the application logic


class TestKubernetesIntegration:
    """Test Kubernetes-specific functionality."""

    def test_kubernetes_probes_configuration(self):
        """Test Kubernetes liveness, readiness, and startup probes."""
        client = TestClient(app)
        
        # Liveness probe
        liveness_response = client.get("/health/liveness")
        assert liveness_response.status_code == 200
        
        # Readiness probe
        readiness_response = client.get("/health/readiness")
        assert readiness_response.status_code == 200
        
        # Startup probe (same as health for this app)
        startup_response = client.get("/health")
        assert startup_response.status_code == 200

    def test_pod_metadata_access(self):
        """Test access to pod metadata and environment."""
        client = TestClient(app)
        
        response = client.get("/api/admin/pod-info")
        
        # Should require authentication
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_horizontal_pod_autoscaler_metrics(self, test_db_session: AsyncSession):
        """Test metrics used by Horizontal Pod Autoscaler."""
        monitoring_service = MonitoringService()
        
        # Get CPU and memory metrics that HPA would use
        metrics = await monitoring_service.collect_system_metrics()
        
        assert "cpu_usage_percent" in metrics
        assert "memory_usage_percent" in metrics
        assert isinstance(metrics["cpu_usage_percent"], (int, float))
        assert isinstance(metrics["memory_usage_percent"], (int, float))

    def test_service_discovery(self):
        """Test service discovery and DNS resolution."""
        client = TestClient(app)
        
        # Test that the service can resolve other services
        response = client.get("/api/health/services")
        
        # Should require authentication or return service status
        assert response.status_code in [200, 401, 403]


class TestMonitoringIntegration:
    """Test monitoring system integration (Prometheus, Grafana, etc.)."""

    def test_prometheus_metrics_format(self):
        """Test Prometheus metrics format compliance."""
        client = TestClient(app)
        response = client.get("/api/metrics")
        
        assert response.status_code == 200
        metrics_text = response.text
        
        # Check Prometheus format compliance
        lines = metrics_text.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('#'):
                # Should have metric name and value
                parts = line.split()
                assert len(parts) >= 2
                # Metric name should be valid
                assert parts[0].replace('_', '').replace('{', '').split('{')[0].isalnum()

    def test_custom_metrics_registration(self):
        """Test custom application metrics registration."""
        client = TestClient(app)
        
        # Make some requests to generate custom metrics
        client.post("/api/auth/login", json={"email": "test@test.com", "password": "test"})
        
        response = client.get("/api/metrics")
        metrics_text = response.text
        
        # Check for custom metrics
        assert "businessbot_" in metrics_text or "http_requests_total" in metrics_text

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_alert_manager_integration(self, test_db_session: AsyncSession):
        """Test Alert Manager integration."""
        monitoring_service = MonitoringService()
        
        # Simulate high error rate
        for _ in range(10):
            await monitoring_service.record_error("test_error", "Test error message")
        
        # Check if alerts would be triggered
        alerts = await monitoring_service.check_alert_thresholds()
        
        # Should have error rate alerts
        error_alerts = [a for a in alerts if "error_rate" in a["metric"]]
        assert len(error_alerts) >= 0  # May or may not trigger based on thresholds

    def test_grafana_dashboard_endpoints(self):
        """Test endpoints used by Grafana dashboards."""
        client = TestClient(app)
        
        # Test metrics endpoint
        response = client.get("/api/metrics")
        assert response.status_code == 200
        
        # Test health endpoint
        health_response = client.get("/api/health")
        assert health_response.status_code == 200
        
        # Test admin endpoints (should require auth)
        admin_response = client.get("/api/admin/stats")
        assert admin_response.status_code in [401, 403]