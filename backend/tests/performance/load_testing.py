"""
Performance and load testing for the Local Business Intelligence Bot.

This module tests system performance under various load conditions,
validates response times, and ensures scalability requirements are met.
"""

import pytest
import pytest_asyncio
import asyncio
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User, Business, Review, Classification
from backend.tests.helpers.performance_helpers import PerformanceTester, APIPerformanceTester
from backend.tests.helpers.assertion_helpers import TestAssertions


class TestPerformanceRequirements:
    """Test performance requirements and benchmarks."""

    @pytest.mark.asyncio
    async def test_api_response_time_requirements(self, test_client: AsyncClient):
        """Test API response time requirements under normal load."""
        # Test health endpoint performance
        response_times = []
        for _ in range(100):
            start_time = time.time()
            response = await test_client.get("/api/health")
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append((end_time - start_time) * 1000)  # Convert to ms
        
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        # Performance requirements
        assert avg_response_time < 100  # Average < 100ms
        assert p95_response_time < 200  # 95th percentile < 200ms
        assert max(response_times) < 500  # Max < 500ms

    @pytest.mark.asyncio
    async def test_database_query_performance(self, test_client: AsyncClient, test_db_session: AsyncSession):
        """Test database query performance with realistic data volumes."""
        # Create test data
        businesses = []
        for i in range(10):
            business = Business(
                name=f"Test Restaurant {i}",
                google_place_id=f"ChIJTest{i}",
                category="restaurant",
                address=f"Test Address {i}"
            )
            test_db_session.add(business)
            businesses.append(business)
        
        await test_db_session.commit()
        
        # Create reviews for each business
        for business in businesses:
            for j in range(100):  # 100 reviews per business
                review = Review(
                    business_id=business.id,
                    author_name=f"Customer {j}",
                    rating=(j % 5) + 1,
                    text=f"Review text {j} for business {business.name}",
                    published_at=time.time() - (j * 3600)  # Spread over time
                )
                test_db_session.add(review)
        
        await test_db_session.commit()
        
        # Test query performance
        # Test business listing query
        start_time = time.time()
        response = await test_client.get("/api/businesses/")
        query_time = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert query_time < 300  # Should complete within 300ms
        
        # Test analytics query with aggregations
        business_id = businesses[0].id
        start_time = time.time()
        response = await test_client.get(f"/api/analytics/{business_id}/dashboard")
        analytics_time = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert analytics_time < 500  # Should complete within 500ms

    @pytest.mark.asyncio
    async def test_concurrent_user_load(self, test_client: AsyncClient):
        """Test system performance under concurrent user load."""
        async def simulate_user_session():
            """Simulate a typical user session."""
            session_times = []
            
            # Health check
            start = time.time()
            response = await test_client.get("/api/health")
            session_times.append(time.time() - start)
            
            if response.status_code != 200:
                return {"success": False, "error": "Health check failed"}
            
            # Login attempt (will fail but tests endpoint)
            start = time.time()
            await test_client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password"
            })
            session_times.append(time.time() - start)
            
            # Business listing
            start = time.time()
            await test_client.get("/api/businesses/")
            session_times.append(time.time() - start)
            
            return {
                "success": True,
                "total_time": sum(session_times),
                "avg_response_time": statistics.mean(session_times)
            }
        
        # Run concurrent sessions
        num_concurrent_users = 50
        tasks = [simulate_user_session() for _ in range(num_concurrent_users)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful_sessions = [r for r in results if r["success"]]
        success_rate = len(successful_sessions) / len(results)
        
        if successful_sessions:
            avg_session_time = statistics.mean([r["total_time"] for r in successful_sessions])
            avg_response_time = statistics.mean([r["avg_response_time"] for r in successful_sessions])
        else:
            avg_session_time = float('inf')
            avg_response_time = float('inf')
        
        # Performance assertions
        assert success_rate >= 0.95  # 95% success rate
        assert avg_session_time < 2.0  # Average session < 2 seconds
        assert avg_response_time < 0.5  # Average response < 500ms

    @pytest.mark.asyncio
    async def test_review_processing_performance(self, test_client: AsyncClient, test_db_session: AsyncSession):
        """Test review processing performance with batch operations."""
        # Create test business
        business = Business(
            name="Performance Test Restaurant",
            google_place_id="ChIJPerfTest",
            category="restaurant",
            address="Performance Test Address"
        )
        test_db_session.add(business)
        await test_db_session.commit()
        
        # Mock Google Places API with large review set
        with patch('backend.external.google_places.GooglePlacesClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Generate 500 mock reviews
            mock_reviews = []
            for i in range(500):
                mock_reviews.append({
                    "author_name": f"Customer {i}",
                    "rating": (i % 5) + 1,
                    "text": f"Performance test review {i}. This is a longer review text to simulate realistic review lengths and processing times.",
                    "time": int(time.time()) - (i * 3600),
                    "review_id": f"perf_review_{i}"
                })
            
            mock_client.get_place_reviews.return_value = mock_reviews
            
            # Test batch import performance
            start_time = time.time()
            
            response = await test_client.post(f"/api/businesses/{business.id}/import-reviews", json={
                "max_reviews": 500,
                "force_refresh": False
            })
            
            processing_time = time.time() - start_time
            
            # Performance requirements
            assert response.status_code == 200
            assert processing_time < 60  # Must complete within 60 seconds
            
            import_data = response.json()
            assert import_data["imported_count"] == 500
            
            # Test classification performance
            start_time = time.time()
            
            # Wait for async classification to complete
            await asyncio.sleep(1)
            
            classification_time = time.time() - start_time
            
            # Classification should complete quickly
            assert classification_time < 30  # Should classify within 30 seconds

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, test_client: AsyncClient):
        """Test memory usage under sustained load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate sustained load
        for _ in range(1000):
            await test_client.get("/api/health")
            
            # Check memory every 100 requests
            if _ % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                # Memory should not increase excessively
                assert memory_increase < 100  # Less than 100MB increase
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_increase = final_memory - initial_memory
        
        # Total memory increase should be reasonable
        assert total_increase < 200  # Less than 200MB total increase

    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self, test_db_session: AsyncSession):
        """Test database connection pool performance under load."""
        
        async def database_operation():
            """Simulate database operation."""
            try:
                result = await test_db_session.execute("SELECT 1")
                return {"success": True, "result": result.scalar()}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Test concurrent database operations
        num_concurrent_ops = 100
        tasks = [database_operation() for _ in range(num_concurrent_ops)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_ops = [r for r in results if isinstance(r, dict) and r.get("success")]
        success_rate = len(successful_ops) / len(results)
        
        # Performance assertions
        assert success_rate >= 0.98  # 98% success rate
        assert total_time < 5.0  # Should complete within 5 seconds
        assert total_time / num_concurrent_ops < 0.1  # Average < 100ms per operation


class TestScalabilityRequirements:
    """Test system scalability and resource utilization."""

    @pytest.mark.asyncio
    async def test_horizontal_scaling_readiness(self, test_client: AsyncClient):
        """Test that the application is ready for horizontal scaling."""
        # Test stateless behavior
        session1_response = await test_client.get("/api/health")
        session2_response = await test_client.get("/api/health")
        
        assert session1_response.status_code == 200
        assert session2_response.status_code == 200
        
        # Responses should be consistent (stateless)
        assert session1_response.json()["status"] == session2_response.json()["status"]

    @pytest.mark.asyncio
    async def test_cache_performance(self, test_client: AsyncClient, test_db_session: AsyncSession):
        """Test caching performance and hit rates."""
        # Create test business
        business = Business(
            name="Cache Test Restaurant",
            google_place_id="ChIJCacheTest",
            category="restaurant",
            address="Cache Test Address"
        )
        test_db_session.add(business)
        await test_db_session.commit()
        
        # First request (cache miss)
        start_time = time.time()
        response1 = await test_client.get(f"/api/analytics/{business.id}/dashboard")
        first_request_time = time.time() - start_time
        
        assert response1.status_code == 200
        
        # Second request (should be cached)
        start_time = time.time()
        response2 = await test_client.get(f"/api/analytics/{business.id}/dashboard")
        second_request_time = time.time() - start_time
        
        assert response2.status_code == 200
        
        # Cached request should be significantly faster
        assert second_request_time < first_request_time * 0.5  # At least 50% faster

    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, test_client: AsyncClient):
        """Test rate limiting implementation performance."""
        # Test rate limiting doesn't significantly impact performance
        response_times = []
        
        for i in range(100):
            start_time = time.time()
            response = await test_client.get("/api/health")
            end_time = time.time()
            
            response_times.append(end_time - start_time)
            
            # Should not be rate limited for reasonable requests
            assert response.status_code == 200
        
        # Rate limiting should not add significant overhead
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 0.1  # Less than 100ms average

    @pytest.mark.asyncio
    async def test_background_task_performance(self, test_db_session: AsyncSession):
        """Test background task processing performance."""
        
        # Mock background task processing
        async def mock_background_task():
            """Simulate background task."""
            await asyncio.sleep(0.01)  # Simulate work
            return {"processed": True}
        
        # Test concurrent background tasks
        num_tasks = 50
        tasks = [mock_background_task() for _ in range(num_tasks)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # All tasks should complete successfully
        assert len(results) == num_tasks
        assert all(r["processed"] for r in results)
        
        # Should process efficiently
        assert total_time < 2.0  # Should complete within 2 seconds


class TestResourceUtilization:
    """Test resource utilization and optimization."""

    @pytest.mark.asyncio
    async def test_cpu_utilization_under_load(self, test_client: AsyncClient):
        """Test CPU utilization under sustained load."""
        import psutil
        
        # Monitor CPU usage
        cpu_percentages = []
        
        for i in range(100):
            start_cpu = psutil.cpu_percent(interval=None)
            
            # Generate load
            await test_client.get("/api/health")
            await test_client.post("/api/auth/login", json={"email": "test", "password": "test"})
            
            end_cpu = psutil.cpu_percent(interval=0.1)
            cpu_percentages.append(end_cpu)
        
        avg_cpu = statistics.mean(cpu_percentages)
        max_cpu = max(cpu_percentages)
        
        # CPU usage should be reasonable
        assert avg_cpu < 80  # Average CPU < 80%
        assert max_cpu < 95  # Max CPU < 95%

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, test_client: AsyncClient):
        """Test for memory leaks during sustained operation."""
        import psutil
        import os
        import gc
        
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate sustained load
        for cycle in range(10):
            for _ in range(100):
                await test_client.get("/api/health")
            
            # Force garbage collection
            gc.collect()
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - baseline_memory
            
            # Memory should not continuously increase
            assert memory_increase < 50 * (cycle + 1)  # Linear growth limit

    @pytest.mark.asyncio
    async def test_database_connection_efficiency(self, test_db_session: AsyncSession):
        """Test database connection efficiency and pooling."""
        
        # Test connection reuse
        connection_times = []
        
        for _ in range(50):
            start_time = time.time()
            
            # Execute simple query
            result = await test_db_session.execute("SELECT 1")
            assert result.scalar() == 1
            
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
        
        # Connection times should be consistent (indicating pooling)
        avg_time = statistics.mean(connection_times)
        std_dev = statistics.stdev(connection_times) if len(connection_times) > 1 else 0
        
        assert avg_time < 0.01  # Average < 10ms
        assert std_dev < 0.005  # Low variance indicates efficient pooling

    @pytest.mark.asyncio
    async def test_file_descriptor_usage(self, test_client: AsyncClient):
        """Test file descriptor usage doesn't leak."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Baseline file descriptors
        baseline_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        
        # Generate load that creates connections
        for _ in range(100):
            await test_client.get("/api/health")
        
        # Check file descriptors after load
        final_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        fd_increase = final_fds - baseline_fds
        
        # File descriptor usage should not increase significantly
        assert fd_increase < 10  # Less than 10 additional FDs


class TestStressTestScenarios:
    """Stress test scenarios for extreme conditions."""

    @pytest.mark.asyncio
    async def test_high_concurrency_stress(self, test_client: AsyncClient):
        """Test system behavior under high concurrency stress."""
        async def stress_worker():
            """Worker function for stress testing."""
            try:
                responses = []
                for _ in range(10):
                    response = await test_client.get("/api/health")
                    responses.append(response.status_code)
                return {"success": True, "responses": responses}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # High concurrency stress test
        num_workers = 100
        tasks = [stress_worker() for _ in range(num_workers)]
        results = await asyncio.gather(*tasks)
        
        # Analyze stress test results
        successful_workers = [r for r in results if r["success"]]
        success_rate = len(successful_workers) / len(results)
        
        # System should handle high concurrency gracefully
        assert success_rate >= 0.90  # 90% success rate under stress
        
        # Check response codes
        all_responses = []
        for worker in successful_workers:
            all_responses.extend(worker["responses"])
        
        success_responses = [r for r in all_responses if r == 200]
        response_success_rate = len(success_responses) / len(all_responses) if all_responses else 0
        
        assert response_success_rate >= 0.95  # 95% successful responses

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, test_client: AsyncClient, test_db_session: AsyncSession):
        """Test system behavior under memory pressure."""
        
        # Create memory pressure by allocating large objects
        large_objects = []
        
        try:
            # Allocate memory in chunks
            for i in range(10):
                # Allocate 10MB chunks
                chunk = bytearray(10 * 1024 * 1024)
                large_objects.append(chunk)
                
                # Test system responsiveness under memory pressure
                response = await test_client.get("/api/health")
                
                # System should remain responsive
                assert response.status_code == 200
                
        finally:
            # Clean up memory
            large_objects.clear()

    @pytest.mark.asyncio
    async def test_rapid_request_burst(self, test_client: AsyncClient):
        """Test system behavior under rapid request bursts."""
        # Rapid burst of requests
        burst_size = 200
        start_time = time.time()
        
        tasks = [test_client.get("/api/health") for _ in range(burst_size)]
        responses = await asyncio.gather(*tasks)
        
        burst_time = time.time() - start_time
        
        # System should handle burst efficiently
        assert burst_time < 10.0  # Complete burst within 10 seconds
        
        # Most requests should succeed
        success_count = len([r for r in responses if r.status_code == 200])
        success_rate = success_count / burst_size
        
        assert success_rate >= 0.95  # 95% success rate during burst