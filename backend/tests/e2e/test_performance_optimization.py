"""
Performance optimization and load testing for Local Business Intelligence Bot.

This module contains tests that validate performance requirements,
database query optimization, and system scalability.
"""

import pytest
import pytest_asyncio
import asyncio
import time
import statistics
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta

from backend.db.models import User, Business, Organization, Review, Classification
from backend.tests.helpers.performance_helpers import PerformanceTester, APIPerformanceTester
from backend.tests.helpers.assertion_helpers import TestAssertions


@pytest_asyncio.fixture
async def performance_test_setup(test_db_session: AsyncSession):
    """Setup performance test environment with large dataset."""
    # Create organization
    org = Organization(
        name="Performance Test Organization",
        subscription_tier="enterprise",
        cost_limit_monthly=5000.00
    )
    test_db_session.add(org)
    await test_db_session.commit()
    await test_db_session.refresh(org)
    
    # Create user
    from backend.services.auth_service import AuthService
    auth_service = AuthService(test_db_session)
    password = "performance_test_123"
    hashed_password = auth_service.hash_password(password)
    
    user = User(
        email="performance@test.com",
        name="Performance Tester",
        role="super_admin",
        language_preference="en",
        organization_id=org.id,
        password_hash=hashed_password
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    # Create multiple businesses
    businesses = []
    for i in range(10):
        business = Business(
            name=f"Performance Restaurant {i+1}",
            google_place_id=f"ChIJPerf{i+1}",
            category="restaurant",
            address=f"Performance Street {i+1}",
            organization_id=org.id,
            avg_rating=4.0 + (i % 10) * 0.1,
            total_reviews=100 + i * 10
        )
        test_db_session.add(business)
        businesses.append(business)
    
    await test_db_session.commit()
    for business in businesses:
        await test_db_session.refresh(business)
    
    # Create reviews for each business
    all_reviews = []
    for business in businesses:
        for j in range(50):  # 50 reviews per business = 500 total
            review = Review(
                business_id=business.id,
                author_name=f"Customer {j}",
                rating=(j % 5) + 1,
                text=f"Review {j} for {business.name}. This is a sample review for performance testing.",
                language="en",
                published_at=datetime.now(timezone.utc) - timedelta(days=j % 30),
                source="google",
                external_id=f"perf_review_{business.id}_{j}"
            )
            test_db_session.add(review)
            all_reviews.append(review)
    
    await test_db_session.commit()
    for review in all_reviews:
        await test_db_session.refresh(review)
    
    # Create classifications for reviews
    for review in all_reviews:
        classification = Classification(
            review_id=review.id,
            sentiment="positive" if review.rating >= 4 else "negative" if review.rating <= 2 else "neutral",
            topics=["food_quality", "service"] if review.rating >= 4 else ["service", "cleanliness"],
            urgency="low" if review.rating >= 4 else "high" if review.rating <= 2 else "medium",
            competitor_mentioned=False,
            confidence_score=0.85 + (review.rating * 0.03),
            ai_model="test-model",
            processing_time_ms=100 + (review.rating * 10)
        )
        test_db_session.add(classification)
    
    await test_db_session.commit()
    
    return {
        "user": user,
        "password": password,
        "organization": org,
        "businesses": businesses,
        "reviews": all_reviews
    }


class TestBatchProcessingPerformance:
    """Test batch processing performance requirements."""

    @pytest.mark.asyncio
    async def test_500_review_classification_performance(self, test_client: AsyncClient, performance_test_setup):
        """Test that 500 reviews can be classified within 60 seconds."""
        # Login
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Generate 500 reviews for batch processing
        mock_reviews = []
        for i in range(500):
            mock_reviews.append({
                "author_name": f"Batch Customer {i}",
                "rating": (i % 5) + 1,
                "text": f"Batch review {i}. Testing batch processing performance with various review lengths and content.",
                "time": int((datetime.now() - timedelta(days=i % 30)).timestamp()),
                "review_id": f"batch_review_{i}"
            })
        
        business_id = performance_test_setup["businesses"][0].id
        
        # Mock the classification service to simulate real processing time
        with patch('backend.ai.gpt5_classifier.GPT5NanoClassifier.classify_batch') as mock_classify:
            async def mock_batch_classify(reviews):
                # Simulate realistic processing time (should be under 60 seconds)
                await asyncio.sleep(0.1)  # Simulate API call time
                results = []
                for review in reviews:
                    results.append({
                        "sentiment": "positive" if "good" in review.text.lower() else "neutral",
                        "topics": ["food_quality", "service"],
                        "urgency": "low",
                        "competitor_mentioned": False,
                        "confidence_score": 0.92,
                        "processing_time_ms": 50,
                        "ai_model": "gpt-5-nano"
                    })
                return results
            
            mock_classify.side_effect = mock_batch_classify
            
            # Test batch processing
            start_time = time.time()
            
            # Process reviews in batches (simulating real import)
            batch_size = 100
            total_processed = 0
            
            for i in range(0, len(mock_reviews), batch_size):
                batch = mock_reviews[i:i + batch_size]
                
                # Simulate review import and classification
                with patch('backend.external.google_places.GooglePlacesClient') as mock_client_class:
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    mock_client.get_place_reviews.return_value = batch
                    
                    batch_response = await test_client.post(
                        f"/api/businesses/{business_id}/import-reviews",
                        json={"max_reviews": len(batch), "force_refresh": True},
                        headers=headers
                    )
                    
                    assert batch_response.status_code == 200
                    total_processed += batch_response.json()["imported_count"]
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Assert performance requirement
            assert processing_time < 60.0  # Must complete within 60 seconds
            assert total_processed == 500
            
            # Calculate throughput
            throughput = total_processed / processing_time
            assert throughput > 8.33  # At least 8.33 reviews/second (500/60)

    @pytest.mark.asyncio
    async def test_concurrent_user_performance(self, test_client: AsyncClient, performance_test_setup):
        """Test system performance under concurrent user load."""
        # Create multiple user sessions
        users_data = []
        for i in range(5):
            user_data = {
                "email": f"concurrent{i}@test.com",
                "name": f"Concurrent User {i}",
                "role": "admin",
                "password": "password_123",
                "language_preference": "en"
            }
            
            register_response = await test_client.post("/api/auth/register", json=user_data)
            assert register_response.status_code == 201
            
            login_response = await test_client.post("/api/auth/login", json={
                "email": f"concurrent{i}@test.com",
                "password": "password_123"
            })
            token = login_response.json()["access_token"]
            users_data.append({"Authorization": f"Bearer {token}"})
        
        business_id = performance_test_setup["businesses"][0].id
        
        async def make_concurrent_requests(headers):
            """Make multiple API requests concurrently."""
            response_times = []
            
            # Dashboard request
            start_time = time.time()
            dashboard_response = await test_client.get(f"/api/analytics/{business_id}/dashboard", headers=headers)
            response_times.append(time.time() - start_time)
            assert dashboard_response.status_code == 200
            
            # Business list request
            start_time = time.time()
            businesses_response = await test_client.get("/api/businesses/", headers=headers)
            response_times.append(time.time() - start_time)
            assert businesses_response.status_code == 200
            
            # Reviews request
            start_time = time.time()
            reviews_response = await test_client.get(f"/api/businesses/{business_id}/reviews", headers=headers)
            response_times.append(time.time() - start_time)
            assert reviews_response.status_code == 200
            
            return response_times
        
        # Execute concurrent requests
        start_time = time.time()
        
        tasks = [make_concurrent_requests(headers) for headers in users_data]
        all_response_times_lists = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Flatten response times
        all_response_times = []
        for response_times in all_response_times_lists:
            all_response_times.extend(response_times)
        
        # Assert performance requirements
        assert total_time < 10.0  # All concurrent requests should complete within 10 seconds
        
        # Check individual response times
        avg_response_time = statistics.mean(all_response_times)
        max_response_time = max(all_response_times)
        
        assert avg_response_time < 1.0  # Average response time under 1 second
        assert max_response_time < 3.0  # No single request takes more than 3 seconds

    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self, test_client: AsyncClient, performance_test_setup):
        """Test memory usage remains stable during large operations."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Login
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Perform memory-intensive operations
        for business in performance_test_setup["businesses"]:
            # Get analytics data
            analytics_response = await test_client.get(f"/api/analytics/{business.id}/dashboard", headers=headers)
            assert analytics_response.status_code == 200
            
            # Get reviews
            reviews_response = await test_client.get(f"/api/businesses/{business.id}/reviews", headers=headers)
            assert reviews_response.status_code == 200
            
            # Generate report
            report_response = await test_client.post(f"/api/reports/{business.id}/generate", json={
                "report_type": "weekly",
                "language": "en",
                "include_action_items": True
            }, headers=headers)
            assert report_response.status_code == 200
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB"


class TestDatabaseQueryOptimization:
    """Test database query optimization and indexing."""

    @pytest.mark.asyncio
    async def test_dashboard_query_performance(self, test_client: AsyncClient, performance_test_setup):
        """Test dashboard queries are optimized and fast."""
        # Login
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        business_id = performance_test_setup["businesses"][0].id
        
        # Test multiple dashboard requests to ensure consistent performance
        response_times = []
        
        for _ in range(10):
            start_time = time.time()
            
            dashboard_response = await test_client.get(f"/api/analytics/{business_id}/dashboard", headers=headers)
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert dashboard_response.status_code == 200
            
            # Verify dashboard data structure
            dashboard_data = dashboard_response.json()
            assert "avg_rating" in dashboard_data
            assert "sentiment_distribution" in dashboard_data
            assert "total_reviews" in dashboard_data
            assert "trend_data" in dashboard_data
        
        # Assert performance requirements
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 0.5  # Average under 500ms
        assert max_response_time < 1.0  # No request over 1 second
        
        # Check response time consistency (standard deviation should be low)
        std_dev = statistics.stdev(response_times)
        assert std_dev < 0.2  # Low variance in response times

    @pytest.mark.asyncio
    async def test_pagination_performance(self, test_client: AsyncClient, performance_test_setup):
        """Test pagination queries are optimized."""
        # Login
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        business_id = performance_test_setup["businesses"][0].id
        
        # Test different pagination scenarios
        pagination_tests = [
            {"skip": 0, "limit": 10},
            {"skip": 10, "limit": 10},
            {"skip": 20, "limit": 10},
            {"skip": 0, "limit": 50},
            {"skip": 100, "limit": 25}
        ]
        
        for pagination in pagination_tests:
            start_time = time.time()
            
            reviews_response = await test_client.get(
                f"/api/businesses/{business_id}/reviews?skip={pagination['skip']}&limit={pagination['limit']}",
                headers=headers
            )
            
            response_time = time.time() - start_time
            
            assert reviews_response.status_code == 200
            assert response_time < 0.3  # Each pagination request under 300ms
            
            reviews_data = reviews_response.json()
            assert len(reviews_data) <= pagination["limit"]

    @pytest.mark.asyncio
    async def test_search_and_filter_performance(self, test_client: AsyncClient, performance_test_setup):
        """Test search and filter queries are optimized."""
        # Login
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        business_id = performance_test_setup["businesses"][0].id
        
        # Test various filter combinations
        filter_tests = [
            {"sentiment": "positive"},
            {"sentiment": "negative"},
            {"rating_min": 4},
            {"rating_max": 2},
            {"date_from": "2024-01-01"},
            {"topics": "food_quality,service"},
            {"urgency": "high"}
        ]
        
        for filters in filter_tests:
            query_params = "&".join([f"{k}={v}" for k, v in filters.items()])
            
            start_time = time.time()
            
            filtered_response = await test_client.get(
                f"/api/businesses/{business_id}/reviews?{query_params}",
                headers=headers
            )
            
            response_time = time.time() - start_time
            
            assert filtered_response.status_code == 200
            assert response_time < 0.5  # Filtered queries under 500ms

    @pytest.mark.asyncio
    async def test_aggregation_query_performance(self, test_client: AsyncClient, performance_test_setup):
        """Test aggregation queries for analytics are optimized."""
        # Login
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        org_id = performance_test_setup["organization"].id
        
        # Test consolidated analytics (complex aggregation)
        start_time = time.time()
        
        consolidated_response = await test_client.get(
            f"/api/analytics/organization/{org_id}/consolidated",
            headers=headers
        )
        
        aggregation_time = time.time() - start_time
        
        assert consolidated_response.status_code == 200
        assert aggregation_time < 2.0  # Complex aggregation under 2 seconds
        
        consolidated_data = consolidated_response.json()
        assert "total_businesses" in consolidated_data
        assert "total_reviews" in consolidated_data
        assert "avg_rating_across_businesses" in consolidated_data
        assert "sentiment_distribution" in consolidated_data
        
        # Test trend analysis queries
        business_id = performance_test_setup["businesses"][0].id
        
        start_time = time.time()
        
        trends_response = await test_client.get(
            f"/api/analytics/{business_id}/trends?period=30",
            headers=headers
        )
        
        trends_time = time.time() - start_time
        
        assert trends_response.status_code == 200
        assert trends_time < 1.0  # Trend analysis under 1 second


class TestCachingPerformance:
    """Test caching mechanisms and performance."""

    @pytest.mark.asyncio
    async def test_dashboard_caching_effectiveness(self, test_client: AsyncClient, performance_test_setup):
        """Test that dashboard caching improves performance."""
        # Login
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        business_id = performance_test_setup["businesses"][0].id
        
        # First request (cache miss)
        start_time = time.time()
        first_response = await test_client.get(f"/api/analytics/{business_id}/dashboard", headers=headers)
        first_request_time = time.time() - start_time
        
        assert first_response.status_code == 200
        
        # Second request (should be cached)
        start_time = time.time()
        second_response = await test_client.get(f"/api/analytics/{business_id}/dashboard", headers=headers)
        second_request_time = time.time() - start_time
        
        assert second_response.status_code == 200
        
        # Cached request should be significantly faster
        assert second_request_time < first_request_time * 0.5  # At least 50% faster
        assert second_request_time < 0.1  # Cached response under 100ms
        
        # Data should be identical
        assert first_response.json() == second_response.json()

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, test_client: AsyncClient, performance_test_setup):
        """Test that cache is properly invalidated when data changes."""
        # Login
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        business_id = performance_test_setup["businesses"][0].id
        
        # Get initial dashboard data
        initial_response = await test_client.get(f"/api/analytics/{business_id}/dashboard", headers=headers)
        initial_data = initial_response.json()
        
        # Import new reviews (should invalidate cache)
        with patch('backend.external.google_places.GooglePlacesClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            new_reviews = [
                {
                    "author_name": "Cache Test Customer",
                    "rating": 5,
                    "text": "Excellent food for cache invalidation test!",
                    "time": int(datetime.now().timestamp()),
                    "review_id": "cache_test_review"
                }
            ]
            
            mock_client.get_place_reviews.return_value = new_reviews
            
            import_response = await test_client.post(
                f"/api/businesses/{business_id}/import-reviews",
                json={"max_reviews": 10, "force_refresh": False},
                headers=headers
            )
            assert import_response.status_code == 200
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Get updated dashboard data
        updated_response = await test_client.get(f"/api/analytics/{business_id}/dashboard", headers=headers)
        updated_data = updated_response.json()
        
        # Data should be different (cache was invalidated)
        assert updated_data["total_reviews"] > initial_data["total_reviews"]


class TestScalabilityLimits:
    """Test system behavior at scale limits."""

    @pytest.mark.asyncio
    async def test_maximum_businesses_per_organization(self, test_client: AsyncClient, performance_test_setup):
        """Test system performance with maximum number of businesses."""
        # Login as super admin
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        org_id = performance_test_setup["organization"].id
        
        # Create additional businesses (up to reasonable limit)
        additional_businesses = 40  # Total will be 50 (10 existing + 40 new)
        
        start_time = time.time()
        
        for i in range(additional_businesses):
            business_data = {
                "name": f"Scale Test Restaurant {i+11}",
                "google_place_id": f"ChIJScale{i+11}",
                "category": "restaurant",
                "address": f"Scale Street {i+11}",
                "organization_id": org_id
            }
            
            business_response = await test_client.post("/api/businesses/", json=business_data, headers=headers)
            assert business_response.status_code == 201
        
        creation_time = time.time() - start_time
        
        # Business creation should complete in reasonable time
        assert creation_time < 30.0  # 40 businesses created in under 30 seconds
        
        # Test listing all businesses
        start_time = time.time()
        all_businesses_response = await test_client.get("/api/businesses/", headers=headers)
        listing_time = time.time() - start_time
        
        assert all_businesses_response.status_code == 200
        assert listing_time < 1.0  # List 50 businesses in under 1 second
        
        businesses_data = all_businesses_response.json()
        assert len(businesses_data) == 50  # 10 original + 40 new
        
        # Test consolidated analytics with many businesses
        start_time = time.time()
        consolidated_response = await test_client.get(f"/api/analytics/organization/{org_id}/consolidated", headers=headers)
        consolidated_time = time.time() - start_time
        
        assert consolidated_response.status_code == 200
        assert consolidated_time < 3.0  # Consolidated analytics for 50 businesses in under 3 seconds

    @pytest.mark.asyncio
    async def test_large_review_dataset_performance(self, test_client: AsyncClient, performance_test_setup):
        """Test performance with large review datasets."""
        # This test simulates having thousands of reviews
        # In a real scenario, this would test database performance with large datasets
        
        # Login
        login_response = await test_client.post("/api/auth/login", json={
            "email": performance_test_setup["user"].email,
            "password": performance_test_setup["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        business_id = performance_test_setup["businesses"][0].id
        
        # Test various operations with existing dataset
        operations = [
            ("dashboard", f"/api/analytics/{business_id}/dashboard"),
            ("reviews_list", f"/api/businesses/{business_id}/reviews?limit=50"),
            ("sentiment_analysis", f"/api/analytics/{business_id}/sentiment-trends"),
            ("topic_analysis", f"/api/analytics/{business_id}/topic-analysis")
        ]
        
        performance_results = {}
        
        for operation_name, endpoint in operations:
            response_times = []
            
            # Test each operation multiple times
            for _ in range(5):
                start_time = time.time()
                response = await test_client.get(endpoint, headers=headers)
                response_time = time.time() - start_time
                
                assert response.status_code == 200
                response_times.append(response_time)
            
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            
            performance_results[operation_name] = {
                "avg_time": avg_time,
                "max_time": max_time
            }
            
            # Assert performance requirements for each operation
            if operation_name == "dashboard":
                assert avg_time < 0.5  # Dashboard under 500ms average
                assert max_time < 1.0   # Dashboard under 1s maximum
            elif operation_name == "reviews_list":
                assert avg_time < 0.3  # Review listing under 300ms average
                assert max_time < 0.5   # Review listing under 500ms maximum
            else:
                assert avg_time < 1.0  # Other operations under 1s average
                assert max_time < 2.0   # Other operations under 2s maximum
        
        # Log performance results for monitoring
        print(f"Performance test results: {performance_results}")

    @pytest.mark.asyncio
    async def test_concurrent_write_operations(self, test_client: AsyncClient, performance_test_setup):
        """Test system behavior under concurrent write operations."""
        # Create multiple user sessions for concurrent operations
        user_sessions = []
        
        for i in range(3):
            user_data = {
                "email": f"concurrent_write_{i}@test.com",
                "name": f"Concurrent Writer {i}",
                "role": "admin",
                "password": "password_123",
                "language_preference": "en"
            }
            
            register_response = await test_client.post("/api/auth/register", json=user_data)
            assert register_response.status_code == 201
            
            login_response = await test_client.post("/api/auth/login", json={
                "email": f"concurrent_write_{i}@test.com",
                "password": "password_123"
            })
            token = login_response.json()["access_token"]
            user_sessions.append({"Authorization": f"Bearer {token}"})
        
        org_id = performance_test_setup["organization"].id
        
        async def create_businesses_concurrently(session_headers, start_index):
            """Create businesses concurrently."""
            created_businesses = []
            
            for i in range(5):  # Each session creates 5 businesses
                business_data = {
                    "name": f"Concurrent Business {start_index}_{i}",
                    "google_place_id": f"ChIJConcurrent{start_index}_{i}",
                    "category": "restaurant",
                    "address": f"Concurrent Street {start_index}_{i}",
                    "organization_id": org_id
                }
                
                response = await test_client.post("/api/businesses/", json=business_data, headers=session_headers)
                assert response.status_code == 201
                created_businesses.append(response.json())
            
            return created_businesses
        
        # Execute concurrent business creation
        start_time = time.time()
        
        tasks = [
            create_businesses_concurrently(headers, i)
            for i, headers in enumerate(user_sessions)
        ]
        
        all_created_businesses_lists = await asyncio.gather(*tasks)
        
        concurrent_creation_time = time.time() - start_time
        
        # Flatten results
        all_created_businesses = []
        for businesses in all_created_businesses_lists:
            all_created_businesses.extend(businesses)
        
        # Assert performance and correctness
        assert len(all_created_businesses) == 15  # 3 sessions × 5 businesses each
        assert concurrent_creation_time < 15.0  # All concurrent operations complete in under 15 seconds
        
        # Verify all businesses were created correctly
        all_businesses_response = await test_client.get("/api/businesses/", headers=user_sessions[0])
        all_businesses = all_businesses_response.json()
        
        # Should include original businesses + newly created ones
        assert len(all_businesses) >= 25  # 10 original + 15 new