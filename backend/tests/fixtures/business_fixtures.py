"""
Business and review fixtures for testing business intelligence features.

This module provides fixtures for creating businesses with comprehensive
review data, analytics, and related entities for testing business logic.
"""

import pytest
import pytest_asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    Business, Organization, Review, Classification, DailyAnalytics,
    AIUsageLog, MonthlyCostSummary, Conversation, ConversationMessage
)
from backend.tests.fixtures.data_factories import TestDataFactory


@pytest_asyncio.fixture
async def business_with_reviews(
    test_db_session: AsyncSession,
    test_organization: Organization
) -> Dict[str, Any]:
    """Create business with comprehensive review data."""
    # Create business
    business = TestDataFactory.create_business(
        name="Comprehensive Test Restaurant",
        organization_id=test_organization.id,
        category="fine_dining",
        avg_rating=4.3,
        total_reviews=150
    )
    test_db_session.add(business)
    await test_db_session.commit()
    await test_db_session.refresh(business)
    
    # Create reviews with varied sentiments and dates
    reviews = TestDataFactory.create_review_batch(
        business_id=business.id,
        count=50,
        sentiment_distribution={"positive": 0.7, "neutral": 0.2, "negative": 0.1},
        date_range_days=60
    )
    
    for review in reviews:
        test_db_session.add(review)
    
    await test_db_session.commit()
    
    for review in reviews:
        await test_db_session.refresh(review)
    
    # Create classifications
    classifications = TestDataFactory.create_classification_batch(
        [review.id for review in reviews]
    )
    
    for classification in classifications:
        test_db_session.add(classification)
    
    await test_db_session.commit()
    
    for classification in classifications:
        await test_db_session.refresh(classification)
    
    return {
        "business": business,
        "reviews": reviews,
        "classifications": classifications
    }


@pytest_asyncio.fixture
async def business_with_analytics(
    test_db_session: AsyncSession,
    business_with_reviews: Dict[str, Any]
) -> Dict[str, Any]:
    """Create business with daily analytics data."""
    business = business_with_reviews["business"]
    
    # Create daily analytics for the last 30 days
    analytics = []
    for i in range(30):
        analytics_date = datetime.now().date() - timedelta(days=i)
        daily_analytics = TestDataFactory.create_daily_analytics(
            business_id=business.id,
            date=analytics_date
        )
        test_db_session.add(daily_analytics)
        analytics.append(daily_analytics)
    
    await test_db_session.commit()
    
    for analytic in analytics:
        await test_db_session.refresh(analytic)
    
    return {
        **business_with_reviews,
        "daily_analytics": analytics
    }


@pytest_asyncio.fixture
async def business_with_ai_usage(
    test_db_session: AsyncSession,
    business_with_analytics: Dict[str, Any]
) -> Dict[str, Any]:
    """Create business with AI usage logs and cost tracking."""
    business = business_with_analytics["business"]
    
    # Create AI usage logs
    ai_logs = []
    
    # Classification logs (one per review)
    for review in business_with_analytics["reviews"]:
        log = TestDataFactory.create_ai_usage_log(
            business_id=business.id,
            ai_service="gpt-5-nano",
            operation="classify"
        )
        test_db_session.add(log)
        ai_logs.append(log)
    
    # Chat logs
    for _ in range(10):
        log = TestDataFactory.create_ai_usage_log(
            business_id=business.id,
            ai_service="claude-haiku",
            operation="chat"
        )
        test_db_session.add(log)
        ai_logs.append(log)
    
    # Report generation logs
    for _ in range(4):  # Weekly reports
        log = TestDataFactory.create_ai_usage_log(
            business_id=business.id,
            ai_service="claude-haiku",
            operation="report"
        )
        test_db_session.add(log)
        ai_logs.append(log)
    
    await test_db_session.commit()
    
    for log in ai_logs:
        await test_db_session.refresh(log)
    
    # Create monthly cost summary
    current_month = datetime.now().replace(day=1).date()
    cost_summary = MonthlyCostSummary(
        business_id=business.id,
        month=current_month,
        classification_cost=Decimal("15.50"),
        chat_cost=Decimal("8.25"),
        report_cost=Decimal("3.75"),
        total_cost=Decimal("27.50"),
        cost_limit=Decimal("100.00"),
        usage_percentage=Decimal("27.50")
    )
    test_db_session.add(cost_summary)
    await test_db_session.commit()
    await test_db_session.refresh(cost_summary)
    
    return {
        **business_with_analytics,
        "ai_usage_logs": ai_logs,
        "monthly_cost_summary": cost_summary
    }


@pytest_asyncio.fixture
async def multiple_businesses_dataset(
    test_db_session: AsyncSession,
    test_organization: Organization
) -> Dict[str, Any]:
    """Create multiple businesses with varied data for comprehensive testing."""
    businesses_data = []
    
    # Create 3 different businesses with different characteristics
    business_configs = [
        {
            "name": "High Performance Restaurant",
            "category": "fine_dining",
            "review_count": 100,
            "sentiment_dist": {"positive": 0.8, "neutral": 0.15, "negative": 0.05}
        },
        {
            "name": "Average Performance Cafe",
            "category": "cafe",
            "review_count": 50,
            "sentiment_dist": {"positive": 0.5, "neutral": 0.3, "negative": 0.2}
        },
        {
            "name": "Struggling Fast Food",
            "category": "fast_food",
            "review_count": 75,
            "sentiment_dist": {"positive": 0.3, "neutral": 0.3, "negative": 0.4}
        }
    ]
    
    for config in business_configs:
        # Create business
        business = TestDataFactory.create_business(
            name=config["name"],
            category=config["category"],
            organization_id=test_organization.id
        )
        test_db_session.add(business)
        await test_db_session.commit()
        await test_db_session.refresh(business)
        
        # Create reviews
        reviews = TestDataFactory.create_review_batch(
            business_id=business.id,
            count=config["review_count"],
            sentiment_distribution=config["sentiment_dist"]
        )
        
        for review in reviews:
            test_db_session.add(review)
        
        await test_db_session.commit()
        
        for review in reviews:
            await test_db_session.refresh(review)
        
        # Create classifications
        classifications = TestDataFactory.create_classification_batch(
            [review.id for review in reviews]
        )
        
        for classification in classifications:
            test_db_session.add(classification)
        
        await test_db_session.commit()
        
        for classification in classifications:
            await test_db_session.refresh(classification)
        
        businesses_data.append({
            "business": business,
            "reviews": reviews,
            "classifications": classifications
        })
    
    return {
        "businesses": businesses_data,
        "high_performance": businesses_data[0],
        "average_performance": businesses_data[1],
        "struggling": businesses_data[2]
    }


@pytest_asyncio.fixture
async def business_with_conversations(
    test_db_session: AsyncSession,
    business_with_reviews: Dict[str, Any],
    test_admin_user
) -> Dict[str, Any]:
    """Create business with conversation history."""
    business = business_with_reviews["business"]
    
    # Create conversation
    conversation = TestDataFactory.create_conversation(
        business_id=business.id,
        user_id=test_admin_user.id,
        language="en"
    )
    test_db_session.add(conversation)
    await test_db_session.commit()
    await test_db_session.refresh(conversation)
    
    # Create conversation messages
    messages = []
    
    # User asks about performance
    user_msg1 = TestDataFactory.create_conversation_message(
        conversation_id=conversation.id,
        role="user",
        content="How is my restaurant performing this week?"
    )
    test_db_session.add(user_msg1)
    messages.append(user_msg1)
    
    # Assistant responds
    assistant_msg1 = TestDataFactory.create_conversation_message(
        conversation_id=conversation.id,
        role="assistant",
        content="Based on your recent reviews, your restaurant is performing well with 85% positive sentiment this week.",
        ai_model="claude-haiku"
    )
    test_db_session.add(assistant_msg1)
    messages.append(assistant_msg1)
    
    # User asks for specific advice
    user_msg2 = TestDataFactory.create_conversation_message(
        conversation_id=conversation.id,
        role="user",
        content="What should I focus on to improve customer satisfaction?"
    )
    test_db_session.add(user_msg2)
    messages.append(user_msg2)
    
    # Assistant provides advice
    assistant_msg2 = TestDataFactory.create_conversation_message(
        conversation_id=conversation.id,
        role="assistant",
        content="I recommend focusing on service speed during peak hours, as several recent reviews mentioned longer wait times.",
        ai_model="claude-haiku"
    )
    test_db_session.add(assistant_msg2)
    messages.append(assistant_msg2)
    
    await test_db_session.commit()
    
    for message in messages:
        await test_db_session.refresh(message)
    
    return {
        **business_with_reviews,
        "conversation": conversation,
        "messages": messages
    }


@pytest_asyncio.fixture
async def performance_test_business(
    test_db_session: AsyncSession,
    test_organization: Organization
) -> Dict[str, Any]:
    """Create business with large dataset for performance testing."""
    # Create business
    business = TestDataFactory.create_business(
        name="Performance Test Restaurant",
        organization_id=test_organization.id
    )
    test_db_session.add(business)
    await test_db_session.commit()
    await test_db_session.refresh(business)
    
    # Create large batch of reviews (500 for performance testing)
    reviews = TestDataFactory.create_review_batch(
        business_id=business.id,
        count=500,
        date_range_days=365  # Full year of data
    )
    
    # Add reviews in batches to avoid memory issues
    batch_size = 50
    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i + batch_size]
        for review in batch:
            test_db_session.add(review)
        await test_db_session.commit()
        
        # Refresh the batch
        for review in batch:
            await test_db_session.refresh(review)
    
    # Create classifications in batches
    review_ids = [review.id for review in reviews]
    classifications = TestDataFactory.create_classification_batch(review_ids)
    
    for i in range(0, len(classifications), batch_size):
        batch = classifications[i:i + batch_size]
        for classification in batch:
            test_db_session.add(classification)
        await test_db_session.commit()
        
        for classification in batch:
            await test_db_session.refresh(classification)
    
    return {
        "business": business,
        "reviews": reviews,
        "classifications": classifications,
        "total_reviews": len(reviews)
    }


class BusinessTestHelpers:
    """Helper methods for business-related testing."""
    
    @staticmethod
    def calculate_sentiment_distribution(classifications: List[Classification]) -> Dict[str, float]:
        """Calculate sentiment distribution from classifications."""
        if not classifications:
            return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
        
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        
        for classification in classifications:
            sentiment_counts[classification.sentiment] += 1
        
        total = len(classifications)
        return {
            sentiment: (count / total) * 100
            for sentiment, count in sentiment_counts.items()
        }
    
    @staticmethod
    def get_recent_reviews(reviews: List[Review], days: int = 7) -> List[Review]:
        """Get reviews from the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        return [
            review for review in reviews
            if review.published_at >= cutoff_date
        ]
    
    @staticmethod
    def get_reviews_by_rating(reviews: List[Review], rating: int) -> List[Review]:
        """Get reviews with specific rating."""
        return [review for review in reviews if review.rating == rating]
    
    @staticmethod
    def assert_business_metrics(business_data: Dict[str, Any], expected_metrics: Dict[str, Any]):
        """Assert business metrics match expected values."""
        business = business_data["business"]
        reviews = business_data["reviews"]
        classifications = business_data["classifications"]
        
        # Check review count
        if "review_count" in expected_metrics:
            assert len(reviews) == expected_metrics["review_count"]
        
        # Check sentiment distribution
        if "sentiment_distribution" in expected_metrics:
            actual_dist = BusinessTestHelpers.calculate_sentiment_distribution(classifications)
            expected_dist = expected_metrics["sentiment_distribution"]
            
            for sentiment, expected_pct in expected_dist.items():
                actual_pct = actual_dist[sentiment]
                # Allow 10% tolerance
                assert abs(actual_pct - expected_pct) <= 10, f"Sentiment {sentiment}: expected {expected_pct}%, got {actual_pct}%"
    
    @staticmethod
    async def create_test_review_with_classification(
        db_session: AsyncSession,
        business_id: str,
        sentiment: str = "positive",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a single review with classification for testing."""
        review = TestDataFactory.create_review(
            business_id=business_id,
            sentiment=sentiment,
            **kwargs
        )
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)
        
        classification = TestDataFactory.create_classification(
            review_id=review.id,
            sentiment=sentiment
        )
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)
        
        return {
            "review": review,
            "classification": classification
        }