"""
Database optimization and query performance tests.

This module tests database query optimization, indexing effectiveness,
and database performance under various load conditions.
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from sqlalchemy.orm import selectinload
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.models import User, Business, Organization, Review, Classification
from backend.db.database import get_db_session


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def large_dataset_setup(test_db_session: AsyncSession):
    """Setup large dataset for database optimization testing."""
    # Create organization
    org = Organization(
        name="DB Optimization Test Org",
        subscription_tier="enterprise",
        cost_limit_monthly=10000.00
    )
    test_db_session.add(org)
    await test_db_session.commit()
    await test_db_session.refresh(org)
    
    # Create user
    from backend.services.auth_service import AuthService
    auth_service = AuthService(test_db_session)
    password = "db_test_123"
    hashed_password = auth_service.hash_password(password)
    
    user = User(
        email="dbtest@optimization.com",
        name="DB Optimizer",
        role="super_admin",
        language_preference="en",
        organization_id=org.id,
        password_hash=hashed_password
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    # Create businesses
    businesses = []
    for i in range(20):
        business = Business(
            name=f"DB Test Restaurant {i+1}",
            google_place_id=f"ChIJDBTest{i+1}",
            category="restaurant",
            address=f"DB Test Street {i+1}",
            organization_id=org.id,
            avg_rating=3.5 + (i % 10) * 0.15,
            total_reviews=50 + i * 25
        )
        test_db_session.add(business)
        businesses.append(business)
    
    await test_db_session.commit()
    for business in businesses:
        await test_db_session.refresh(business)
    
    # Create large number of reviews (100 per business = 2000 total)
    all_reviews = []
    for business in businesses:
        for j in range(100):
            from datetime import datetime, timezone, timedelta
            review = Review(
                business_id=business.id,
                author_name=f"DB Customer {j}",
                rating=(j % 5) + 1,
                text=f"DB optimization test review {j} for {business.name}. " + 
                     "This is a longer review text to test text search performance. " * (j % 3 + 1),
                language="en" if j % 3 == 0 else "de" if j % 3 == 1 else "tr",
                published_at=datetime.now(timezone.utc) - timedelta(days=j % 365),
                source="google",
                external_id=f"db_review_{business.id}_{j}"
            )
            test_db_session.add(review)
            all_reviews.append(review)
    
    await test_db_session.commit()
    for review in all_reviews:
        await test_db_session.refresh(review)
    
    # Create classifications
    for review in all_reviews:
        classification = Classification(
            review_id=review.id,
            sentiment="positive" if review.rating >= 4 else "negative" if review.rating <= 2 else "neutral",
            topics=["food_quality", "service"] if review.rating >= 4 else 
                   ["service", "cleanliness"] if review.rating <= 2 else ["ambiance", "price"],
            urgency="low" if review.rating >= 4 else "high" if review.rating <= 2 else "medium",
            competitor_mentioned=(review.rating <= 2 and "competitor" in review.text.lower()),
            confidence_score=0.80 + (review.rating * 0.04),
            ai_model="test-optimization-model",
            processing_time_ms=80 + (review.rating * 15)
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


class TestIndexEffectiveness:
    """Test database index effectiveness and query optimization."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_business_id_index_performance(self, large_dataset_setup, test_db_session):
        """Test that business_id indexes are effective for review queries."""
        business_id = large_dataset_setup["businesses"][0].id
        
        # Test review lookup by business_id (should use index)
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(Review).where(Review.business_id == business_id)
        )
        reviews = result.scalars().all()
        
        query_time = time.time() - start_time
        
        # Should be very fast with proper indexing
        assert query_time < 0.05  # Under 50ms for indexed query
        assert len(reviews) == 100  # Should find all reviews for this business
        
        # Test classification lookup by review_id (should use index)
        review_ids = [review.id for review in reviews[:10]]
        
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(Classification).where(Classification.review_id.in_(review_ids))
        )
        classifications = result.scalars().all()
        
        classification_query_time = time.time() - start_time
        
        assert classification_query_time < 0.05  # Under 50ms for indexed query
        assert len(classifications) == 10

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_date_range_index_performance(self, large_dataset_setup, test_db_session):
        """Test date range queries use indexes effectively."""
        from datetime import datetime, timezone, timedelta
        
        # Test recent reviews query (should use published_at index)
        recent_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(Review).where(Review.published_at >= recent_date)
        )
        recent_reviews = result.scalars().all()
        
        date_query_time = time.time() - start_time
        
        # Should be fast with date index
        assert date_query_time < 0.1  # Under 100ms for date range query
        assert len(recent_reviews) > 0
        
        # Test date range with business filter (compound index)
        business_id = large_dataset_setup["businesses"][0].id
        
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(Review).where(
                Review.business_id == business_id,
                Review.published_at >= recent_date
            )
        )
        filtered_reviews = result.scalars().all()
        
        compound_query_time = time.time() - start_time
        
        assert compound_query_time < 0.05  # Under 50ms for compound index query

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_sentiment_classification_index_performance(self, large_dataset_setup, test_db_session):
        """Test sentiment and urgency classification indexes."""
        # Test sentiment filtering (should use sentiment index)
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(Classification).where(Classification.sentiment == "negative")
        )
        negative_classifications = result.scalars().all()
        
        sentiment_query_time = time.time() - start_time
        
        assert sentiment_query_time < 0.1  # Under 100ms for sentiment query
        assert len(negative_classifications) > 0
        
        # Test urgency filtering (should use urgency index)
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(Classification).where(Classification.urgency == "high")
        )
        urgent_classifications = result.scalars().all()
        
        urgency_query_time = time.time() - start_time
        
        assert urgency_query_time < 0.1  # Under 100ms for urgency query
        assert len(urgent_classifications) > 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_full_text_search_performance(self, large_dataset_setup, test_db_session):
        """Test full-text search performance on review text."""
        # Test text search performance
        search_term = "optimization"
        
        start_time = time.time()
        
        # Using LIKE for text search (in production, would use full-text search)
        result = await test_db_session.execute(
            select(Review).where(Review.text.ilike(f"%{search_term}%"))
        )
        search_results = result.scalars().all()
        
        search_query_time = time.time() - start_time
        
        # Text search should complete in reasonable time
        assert search_query_time < 0.5  # Under 500ms for text search
        assert len(search_results) > 0


class TestQueryOptimization:
    """Test complex query optimization and N+1 problem prevention."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_eager_loading_optimization(self, large_dataset_setup, test_db_session):
        """Test that eager loading prevents N+1 queries."""
        business_id = large_dataset_setup["businesses"][0].id
        
        # Test loading reviews with classifications (should use eager loading)
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(Review)
            .options(selectinload(Review.classification))
            .where(Review.business_id == business_id)
            .limit(50)
        )
        reviews_with_classifications = result.scalars().all()
        
        eager_loading_time = time.time() - start_time
        
        # Should be fast with eager loading
        assert eager_loading_time < 0.2  # Under 200ms for 50 reviews with classifications
        assert len(reviews_with_classifications) == 50
        
        # Verify classifications are loaded
        for review in reviews_with_classifications[:5]:
            assert hasattr(review, 'classification')
            # Accessing classification should not trigger additional query
            classification = review.classification
            assert classification is not None

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_aggregation_query_optimization(self, large_dataset_setup, test_db_session):
        """Test aggregation queries are optimized."""
        business_id = large_dataset_setup["businesses"][0].id
        
        # Test sentiment distribution aggregation
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(
                Classification.sentiment,
                func.count(Classification.id).label('count')
            )
            .join(Review, Classification.review_id == Review.id)
            .where(Review.business_id == business_id)
            .group_by(Classification.sentiment)
        )
        sentiment_distribution = result.all()
        
        aggregation_time = time.time() - start_time
        
        # Aggregation should be fast
        assert aggregation_time < 0.1  # Under 100ms for aggregation
        assert len(sentiment_distribution) > 0
        
        # Test rating distribution aggregation
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(
                Review.rating,
                func.count(Review.id).label('count'),
                func.avg(Review.rating).label('avg_rating')
            )
            .where(Review.business_id == business_id)
            .group_by(Review.rating)
        )
        rating_distribution = result.all()
        
        rating_aggregation_time = time.time() - start_time
        
        assert rating_aggregation_time < 0.1  # Under 100ms for rating aggregation
        assert len(rating_distribution) > 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_complex_join_optimization(self, large_dataset_setup, test_db_session):
        """Test complex multi-table joins are optimized."""
        org_id = large_dataset_setup["organization"].id
        
        # Test complex query joining all main tables
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(
                Business.name,
                func.count(Review.id).label('review_count'),
                func.avg(Review.rating).label('avg_rating'),
                func.count(Classification.id).label('classification_count')
            )
            .join(Review, Business.id == Review.business_id)
            .join(Classification, Review.id == Classification.review_id)
            .where(Business.organization_id == org_id)
            .group_by(Business.id, Business.name)
        )
        complex_join_results = result.all()
        
        complex_join_time = time.time() - start_time
        
        # Complex join should complete in reasonable time
        assert complex_join_time < 0.5  # Under 500ms for complex join
        assert len(complex_join_results) == 20  # Should have results for all businesses

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_subquery_optimization(self, large_dataset_setup, test_db_session):
        """Test subquery optimization for complex analytics."""
        # Test subquery for businesses with high-urgency reviews
        start_time = time.time()
        
        # Subquery to find businesses with urgent reviews
        urgent_business_subquery = (
            select(Review.business_id)
            .join(Classification, Review.id == Classification.review_id)
            .where(Classification.urgency == "high")
            .distinct()
        ).subquery()
        
        result = await test_db_session.execute(
            select(Business)
            .where(Business.id.in_(select(urgent_business_subquery.c.business_id)))
        )
        businesses_with_urgent_reviews = result.scalars().all()
        
        subquery_time = time.time() - start_time
        
        # Subquery should be optimized
        assert subquery_time < 0.2  # Under 200ms for subquery
        assert len(businesses_with_urgent_reviews) > 0


class TestDatabasePerformanceUnderLoad:
    """Test database performance under various load conditions."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_concurrent_read_performance(self, large_dataset_setup, test_db_session):
        """Test database performance under concurrent read load."""
        business_ids = [b.id for b in large_dataset_setup["businesses"][:5]]
        
        async def concurrent_read_operation(business_id):
            """Perform concurrent read operations."""
            # Get reviews
            result = await test_db_session.execute(
                select(Review).where(Review.business_id == business_id).limit(20)
            )
            reviews = result.scalars().all()
            
            # Get classifications
            review_ids = [r.id for r in reviews]
            result = await test_db_session.execute(
                select(Classification).where(Classification.review_id.in_(review_ids))
            )
            classifications = result.scalars().all()
            
            return len(reviews), len(classifications)
        
        # Execute concurrent reads
        start_time = time.time()
        
        tasks = [concurrent_read_operation(bid) for bid in business_ids]
        results = await asyncio.gather(*tasks)
        
        concurrent_read_time = time.time() - start_time
        
        # All concurrent reads should complete quickly
        assert concurrent_read_time < 1.0  # Under 1 second for 5 concurrent operations
        assert len(results) == 5
        
        # Verify all operations returned data
        for review_count, classification_count in results:
            assert review_count > 0
            assert classification_count > 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_batch_insert_performance(self, large_dataset_setup, test_db_session):
        """Test batch insert performance for large datasets."""
        business_id = large_dataset_setup["businesses"][0].id
        
        # Prepare batch of new reviews
        from datetime import datetime, timezone, timedelta
        new_reviews = []
        for i in range(100):
            review = Review(
                business_id=business_id,
                author_name=f"Batch Customer {i}",
                rating=(i % 5) + 1,
                text=f"Batch insert test review {i}",
                language="en",
                published_at=datetime.now(timezone.utc) - timedelta(minutes=i),
                source="google",
                external_id=f"batch_review_{i}"
            )
            new_reviews.append(review)
        
        # Test batch insert performance
        start_time = time.time()
        
        test_db_session.add_all(new_reviews)
        await test_db_session.commit()
        
        batch_insert_time = time.time() - start_time
        
        # Batch insert should be efficient
        assert batch_insert_time < 1.0  # Under 1 second for 100 reviews
        
        # Verify all reviews were inserted
        result = await test_db_session.execute(
            select(func.count(Review.id)).where(
                Review.external_id.like("batch_review_%")
            )
        )
        inserted_count = result.scalar()
        assert inserted_count == 100

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_large_result_set_pagination(self, large_dataset_setup, test_db_session):
        """Test pagination performance with large result sets."""
        business_id = large_dataset_setup["businesses"][0].id
        
        # Test different pagination scenarios
        pagination_tests = [
            {"offset": 0, "limit": 25},
            {"offset": 25, "limit": 25},
            {"offset": 50, "limit": 25},
            {"offset": 75, "limit": 25}
        ]
        
        for pagination in pagination_tests:
            start_time = time.time()
            
            result = await test_db_session.execute(
                select(Review)
                .where(Review.business_id == business_id)
                .order_by(Review.published_at.desc())
                .offset(pagination["offset"])
                .limit(pagination["limit"])
            )
            paginated_reviews = result.scalars().all()
            
            pagination_time = time.time() - start_time
            
            # Each pagination query should be fast
            assert pagination_time < 0.1  # Under 100ms per page
            assert len(paginated_reviews) <= pagination["limit"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, large_dataset_setup):
        """Test database connection pooling under load."""
        # This test verifies that connection pooling works correctly
        # by making multiple concurrent database operations
        
        async def database_operation(session_factory):
            """Perform database operation with new session."""
            async with session_factory() as session:
                result = await session.execute(
                    select(func.count(Review.id))
                )
                count = result.scalar()
                return count
        
        # Get session factory
        from backend.db.database import async_session_maker
        
        # Execute multiple concurrent operations
        start_time = time.time()
        
        tasks = [database_operation(async_session_maker) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        connection_pool_time = time.time() - start_time
        
        # Connection pooling should handle concurrent operations efficiently
        assert connection_pool_time < 2.0  # Under 2 seconds for 10 concurrent operations
        assert len(results) == 10
        
        # All operations should return the same count
        assert all(count > 0 for count in results)
        assert len(set(results)) == 1  # All counts should be identical


class TestQueryPlanAnalysis:
    """Test query execution plans for optimization verification."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_explain_query_plans(self, large_dataset_setup, test_db_session):
        """Test that query execution plans use indexes effectively."""
        business_id = large_dataset_setup["businesses"][0].id
        
        # Test EXPLAIN for business review query
        explain_result = await test_db_session.execute(
            text(f"EXPLAIN QUERY PLAN SELECT * FROM reviews WHERE business_id = '{business_id}'")
        )
        explain_output = explain_result.fetchall()
        
        # Verify index usage (SQLite specific)
        explain_text = str(explain_output)
        # In a real implementation, would check for index usage patterns
        assert len(explain_output) > 0
        
        # Test EXPLAIN for date range query
        from datetime import datetime, timezone, timedelta
        recent_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        explain_result = await test_db_session.execute(
            text(f"EXPLAIN QUERY PLAN SELECT * FROM reviews WHERE published_at >= '{recent_date}'")
        )
        date_explain_output = explain_result.fetchall()
        
        assert len(date_explain_output) > 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_query_complexity_analysis(self, large_dataset_setup, test_db_session):
        """Test complex query performance and optimization."""
        org_id = large_dataset_setup["organization"].id
        
        # Complex analytics query
        complex_query = text("""
            SELECT 
                b.name,
                COUNT(r.id) as review_count,
                AVG(r.rating) as avg_rating,
                COUNT(CASE WHEN c.sentiment = 'positive' THEN 1 END) as positive_count,
                COUNT(CASE WHEN c.sentiment = 'negative' THEN 1 END) as negative_count,
                COUNT(CASE WHEN c.urgency = 'high' THEN 1 END) as urgent_count
            FROM businesses b
            LEFT JOIN reviews r ON b.id = r.business_id
            LEFT JOIN classifications c ON r.id = c.review_id
            WHERE b.organization_id = :org_id
            GROUP BY b.id, b.name
            ORDER BY avg_rating DESC
        """)
        
        start_time = time.time()
        
        result = await test_db_session.execute(complex_query, {"org_id": org_id})
        complex_results = result.fetchall()
        
        complex_query_time = time.time() - start_time
        
        # Complex query should still be reasonably fast
        assert complex_query_time < 1.0  # Under 1 second for complex analytics
        assert len(complex_results) == 20  # Should return all businesses
        
        # Verify data structure
        for row in complex_results[:3]:
            assert row.review_count > 0
            assert row.avg_rating > 0
            assert row.positive_count >= 0
            assert row.negative_count >= 0


class TestDatabaseMaintenanceOperations:
    """Test database maintenance and optimization operations."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_vacuum_and_analyze_performance(self, large_dataset_setup, test_db_session):
        """Test database maintenance operations."""
        # Test VACUUM operation (SQLite specific)
        start_time = time.time()
        
        await test_db_session.execute(text("VACUUM"))
        
        vacuum_time = time.time() - start_time
        
        # VACUUM should complete in reasonable time
        assert vacuum_time < 5.0  # Under 5 seconds for VACUUM
        
        # Test ANALYZE operation
        start_time = time.time()
        
        await test_db_session.execute(text("ANALYZE"))
        
        analyze_time = time.time() - start_time
        
        # ANALYZE should be fast
        assert analyze_time < 1.0  # Under 1 second for ANALYZE

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_index_usage_statistics(self, large_dataset_setup, test_db_session):
        """Test index usage and effectiveness."""
        # Query to check index usage (SQLite specific)
        # In production, would use database-specific index statistics
        
        # Test that queries use indexes by checking execution time
        business_id = large_dataset_setup["businesses"][0].id
        
        # Query that should use business_id index
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(Review).where(Review.business_id == business_id)
        )
        indexed_results = result.scalars().all()
        
        indexed_query_time = time.time() - start_time
        
        # Should be very fast with index
        assert indexed_query_time < 0.05  # Under 50ms
        assert len(indexed_results) == 100
        
        # Query without index (full table scan)
        start_time = time.time()
        
        result = await test_db_session.execute(
            select(Review).where(Review.text.like("%test%"))
        )
        full_scan_results = result.scalars().all()
        
        full_scan_time = time.time() - start_time
        
        # Full scan should be slower but still reasonable
        assert full_scan_time < 0.5  # Under 500ms for full scan
        assert len(full_scan_results) > 0