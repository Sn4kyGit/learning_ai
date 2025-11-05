"""
Pytest configuration and fixtures for Local Business Intelligence Bot tests.

This module provides common test fixtures, database setup, and mock services
for the test suite.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import uuid

from backend.db.database import Base
from backend.db.models import Business, Organization, User, Review, Classification
from backend.ai.base import (
    ReviewClassifierProtocol,
    BusinessAdvisorProtocol,
    CostTracker,
)
from backend.ai.language_detector import LanguageDetector
from backend.config import Settings


# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        environment="test",
        debug=True,
        database_url=TEST_DATABASE_URL,
        secret_key="test-secret-key",
        openai_api_key="test-openai-key",
        anthropic_api_key="test-anthropic-key",
        google_places_api_key="test-google-key",
    )


@pytest.fixture
def mock_classifier() -> Mock:
    """Create mock review classifier."""
    classifier = Mock(spec=ReviewClassifierProtocol)

    # Configure default responses
    from backend.ai.base import ClassificationResult

    async def mock_classify_review(text: str, language: str = "en"):
        return ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.95,
            processing_time_ms=100,
            ai_model="mock-gpt5-nano",
        )

    async def mock_classify_batch(reviews):
        return [await mock_classify_review(review.text) for review in reviews]

    classifier.classify_review = AsyncMock(side_effect=mock_classify_review)
    classifier.classify_batch = AsyncMock(side_effect=mock_classify_batch)

    return classifier


@pytest.fixture
def mock_advisor() -> Mock:
    """Create mock business advisor."""
    advisor = Mock(spec=BusinessAdvisorProtocol)

    from backend.ai.base import AdvisorResponse, WeeklyReport
    from decimal import Decimal
    from datetime import datetime, timedelta

    async def mock_generate_response(message: str, context, language: str = "en"):
        return AdvisorResponse(
            message="Based on your reviews, I recommend focusing on customer service.",
            language=language,
            confidence_score=0.92,
            processing_time_ms=200,
            ai_model="mock-claude-haiku",
            cost_usd=Decimal("0.001"),
        )

    async def mock_generate_report(business_data, language: str = "en"):
        return WeeklyReport(
            business_id=business_data.business_id,
            report_period_start=datetime.now() - timedelta(days=7),
            report_period_end=datetime.now(),
            summary="Your restaurant performed well this week.",
            action_items=["Continue excellent service", "Monitor food quality"],
            sentiment_analysis="Overall positive sentiment trend",
            top_themes=["food_quality", "service"],
            competitor_mentions=0,
            language=language,
            ai_model="mock-claude-haiku",
        )

    advisor.generate_response = AsyncMock(side_effect=mock_generate_response)
    advisor.generate_report = AsyncMock(side_effect=mock_generate_report)

    return advisor


@pytest.fixture
def mock_cost_tracker() -> Mock:
    """Create mock cost tracker."""
    cost_tracker = Mock(spec=CostTracker)

    from decimal import Decimal

    async def mock_log_usage(*args, **kwargs):
        pass

    async def mock_get_monthly_cost(business_id: str):
        return Decimal("25.50")

    async def mock_check_cost_limit(business_id: str):
        return True

    cost_tracker.log_usage = AsyncMock(side_effect=mock_log_usage)
    cost_tracker.get_monthly_cost = AsyncMock(side_effect=mock_get_monthly_cost)
    cost_tracker.check_cost_limit = AsyncMock(side_effect=mock_check_cost_limit)

    return cost_tracker


@pytest.fixture
def mock_language_detector() -> LanguageDetector:
    """Create mock language detector."""
    detector = LanguageDetector()

    # Override detect_language method to return predictable results
    def mock_detect_language(text: str) -> str:
        if "hallo" in text.lower() or "gut" in text.lower():
            return "de"
        elif "merhaba" in text.lower():
            return "tr"
        else:
            return "en"

    detector.detect_language = mock_detect_language

    return detector


@pytest.fixture
async def test_organization(test_db_session: AsyncSession) -> Organization:
    """Create test organization."""
    org = Organization(
        name="Test Restaurant Group",
        subscription_tier="premium",
        cost_limit_monthly=200.00,
    )

    test_db_session.add(org)
    await test_db_session.commit()
    await test_db_session.refresh(org)

    return org


@pytest.fixture
async def test_business(
    test_db_session: AsyncSession, test_organization: Organization
) -> Business:
    """Create test business."""
    business = Business(
        name="Test Restaurant",
        google_place_id="test-place-123",
        category="restaurant",
        address="123 Test Street, Test City",
        organization_id=test_organization.id,
        avg_rating=4.2,
        total_reviews=50,
    )

    test_db_session.add(business)
    await test_db_session.commit()
    await test_db_session.refresh(business)

    return business


@pytest.fixture
async def test_user(
    test_db_session: AsyncSession, test_organization: Organization
) -> User:
    """Create test user."""
    user = User(
        email="test@example.com",
        name="Test User",
        role="admin",
        language_preference="en",
        organization_id=test_organization.id,
        password_hash="hashed_password",
    )

    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    return user


@pytest.fixture
async def test_reviews(
    test_db_session: AsyncSession, test_business: Business
) -> list[Review]:
    """Create test reviews."""
    from datetime import datetime, timedelta

    reviews = [
        Review(
            business_id=test_business.id,
            author_name="John Doe",
            rating=5,
            text="Excellent food and service!",
            language="en",
            published_at=datetime.utcnow() - timedelta(days=1),
            source="google",
            external_id="review-1",
        ),
        Review(
            business_id=test_business.id,
            author_name="Jane Smith",
            rating=2,
            text="Food was cold and service was slow.",
            language="en",
            published_at=datetime.utcnow() - timedelta(days=2),
            source="google",
            external_id="review-2",
        ),
        Review(
            business_id=test_business.id,
            author_name="Bob Wilson",
            rating=4,
            text="Good food, nice atmosphere.",
            language="en",
            published_at=datetime.utcnow() - timedelta(days=3),
            source="google",
            external_id="review-3",
        ),
    ]

    for review in reviews:
        test_db_session.add(review)

    await test_db_session.commit()

    for review in reviews:
        await test_db_session.refresh(review)

    return reviews


@pytest.fixture
async def test_classifications(
    test_db_session: AsyncSession, test_reviews: list[Review]
) -> list[Classification]:
    """Create test classifications."""
    classifications = [
        Classification(
            review_id=test_reviews[0].id,
            sentiment="positive",
            topics=["food_quality", "service"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.95,
            ai_model="test-model",
            processing_time_ms=100,
        ),
        Classification(
            review_id=test_reviews[1].id,
            sentiment="negative",
            topics=["food_quality", "service"],
            urgency="high",
            competitor_mentioned=False,
            confidence_score=0.92,
            ai_model="test-model",
            processing_time_ms=120,
        ),
        Classification(
            review_id=test_reviews[2].id,
            sentiment="positive",
            topics=["food_quality", "ambiance"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.88,
            ai_model="test-model",
            processing_time_ms=90,
        ),
    ]

    for classification in classifications:
        test_db_session.add(classification)

    await test_db_session.commit()

    for classification in classifications:
        await test_db_session.refresh(classification)

    return classifications


# Helper functions for tests
def create_test_uuid() -> str:
    """Create a test UUID string."""
    return str(uuid.uuid4())


async def create_test_business_with_data(
    db_session: AsyncSession, review_count: int = 10
) -> Business:
    """Create a test business with reviews and classifications."""
    # This would be implemented for performance tests
    pass
