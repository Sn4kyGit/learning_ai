"""
Pytest configuration and fixtures for Local Business Intelligence Bot tests.

This module provides common test fixtures, database setup, and mock services
for the test suite.
"""

import pytest
import pytest_asyncio
import asyncio
import warnings
from typing import AsyncGenerator, Generator, Any, List
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

from backend.db.database import Base
from backend.db.models import Business, Organization, User, Review, Classification
from backend.ai.base import (
    ReviewClassifierProtocol,
    BusinessAdvisorProtocol,
    CostTracker,
    ClassificationResult,
    AdvisorResponse,
    WeeklyReport,
)
from backend.ai.language_detector import LanguageDetector
from backend.config import Settings

# Suppress specific warnings during test execution
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", message=".*coroutine.*was never awaited.*")

# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class TestConfig:
    """Test-specific configuration."""
    DATABASE_URL = TEST_DATABASE_URL
    REDIS_URL = "redis://localhost:6379/1"
    AI_SERVICES_MOCK = True
    EMAIL_BACKEND = "mock"
    ENVIRONMENT = "test"
    SECRET_KEY = "test-secret-key-for-testing-only"
    OPENAI_API_KEY = "test-openai-key"
    ANTHROPIC_API_KEY = "test-anthropic-key"
    GOOGLE_PLACES_API_KEY = "test-google-key"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create test database engine with proper cleanup."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "isolation_level": None,
        },
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        pass  # Ignore cleanup errors
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with automatic rollback."""
    async_session_maker = async_sessionmaker(
        test_db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            # Rollback any pending transactions
            if session.in_transaction():
                await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def test_client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide test client with database override."""
    from backend.main import app
    from backend.db.database import get_db_session
    from httpx import ASGITransport
    
    async def override_get_db():
        yield test_db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


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
def mock_classifier() -> AsyncMock:
    """Create mock review classifier with proper async behavior."""
    classifier = AsyncMock(spec=ReviewClassifierProtocol)

    # Configure default responses
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
        if isinstance(reviews, list):
            return [await mock_classify_review(getattr(review, 'text', str(review))) for review in reviews]
        return []

    classifier.classify_review.side_effect = mock_classify_review
    classifier.classify_batch.side_effect = mock_classify_batch

    return classifier


@pytest.fixture
def mock_advisor() -> AsyncMock:
    """Create mock business advisor with proper async behavior."""
    advisor = AsyncMock(spec=BusinessAdvisorProtocol)

    async def mock_generate_response(message: str, context=None, language: str = "en"):
        return AdvisorResponse(
            message="Based on your reviews, I recommend focusing on customer service.",
            language=language,
            confidence_score=0.92,
            processing_time_ms=200,
            ai_model="mock-claude-haiku",
            cost_usd=Decimal("0.001"),
        )

    async def mock_generate_report(business_data=None, language: str = "en"):
        business_id = getattr(business_data, 'business_id', 'test-business-id') if business_data else 'test-business-id'
        return WeeklyReport(
            business_id=business_id,
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

    advisor.generate_response.side_effect = mock_generate_response
    advisor.generate_report.side_effect = mock_generate_report

    return advisor


@pytest.fixture
def mock_cost_tracker() -> AsyncMock:
    """Create mock cost tracker with proper async behavior."""
    cost_tracker = AsyncMock(spec=CostTracker)

    async def mock_log_usage(*args, **kwargs):
        return None

    async def mock_get_monthly_cost(business_id: str = None):
        return Decimal("25.50")

    async def mock_check_cost_limit(business_id: str = None):
        return True

    async def mock_get_cost_summary(business_id: str = None):
        return {
            "total_cost": Decimal("25.50"),
            "classification_cost": Decimal("15.30"),
            "chat_cost": Decimal("8.20"),
            "report_cost": Decimal("2.00"),
            "usage_percentage": 25.5
        }

    cost_tracker.log_usage.side_effect = mock_log_usage
    cost_tracker.get_monthly_cost.side_effect = mock_get_monthly_cost
    cost_tracker.check_cost_limit.side_effect = mock_check_cost_limit
    cost_tracker.get_cost_summary.side_effect = mock_get_cost_summary

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


@pytest_asyncio.fixture
async def test_organization(test_db_session: AsyncSession) -> Organization:
    """Create test organization."""
    org = Organization(
        name="Test Restaurant Group",
        subscription_tier="premium",
        cost_limit_monthly=Decimal("200.00"),
    )

    test_db_session.add(org)
    await test_db_session.commit()
    await test_db_session.refresh(org)

    return org


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
async def test_reviews(
    test_db_session: AsyncSession, test_business: Business
) -> List[Review]:
    """Create test reviews."""
    reviews = [
        Review(
            business_id=test_business.id,
            author_name="John Doe",
            rating=5,
            text="Excellent food and service!",
            language="en",
            published_at=datetime.now() - timedelta(days=1),
            source="google",
            external_id="review-1",
        ),
        Review(
            business_id=test_business.id,
            author_name="Jane Smith",
            rating=2,
            text="Food was cold and service was slow.",
            language="en",
            published_at=datetime.now() - timedelta(days=2),
            source="google",
            external_id="review-2",
        ),
        Review(
            business_id=test_business.id,
            author_name="Bob Wilson",
            rating=4,
            text="Good food, nice atmosphere.",
            language="en",
            published_at=datetime.now() - timedelta(days=3),
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


@pytest_asyncio.fixture
async def test_classifications(
    test_db_session: AsyncSession, test_reviews: List[Review]
) -> List[Classification]:
    """Create test classifications."""
    classifications = [
        Classification(
            review_id=test_reviews[0].id,
            sentiment="positive",
            topics=["food_quality", "service"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=Decimal("0.95"),
            ai_model="test-model",
            processing_time_ms=100,
        ),
        Classification(
            review_id=test_reviews[1].id,
            sentiment="negative",
            topics=["food_quality", "service"],
            urgency="high",
            competitor_mentioned=False,
            confidence_score=Decimal("0.92"),
            ai_model="test-model",
            processing_time_ms=120,
        ),
        Classification(
            review_id=test_reviews[2].id,
            sentiment="positive",
            topics=["food_quality", "ambiance"],
            urgency="low",
            competitor_mentioned=False,
            confidence_score=Decimal("0.88"),
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


# Import additional fixtures
from backend.tests.fixtures.user_fixtures import *
from backend.tests.fixtures.business_fixtures import *
from backend.tests.fixtures.mock_responses import *
from backend.tests.fixtures.database_seeding import DatabaseSeeder, SeedingPresets


# Helper functions for tests
def create_test_uuid() -> str:
    """Create a test UUID string."""
    return str(uuid.uuid4())


@pytest_asyncio.fixture
async def database_seeder(test_db_session: AsyncSession) -> DatabaseSeeder:
    """Provide database seeder for integration tests."""
    seeder = DatabaseSeeder(test_db_session)
    yield seeder
    # Cleanup after test
    await seeder.cleanup_all()


@pytest_asyncio.fixture
async def minimal_test_data(test_db_session: AsyncSession) -> Dict[str, Any]:
    """Provide minimal test dataset for unit tests."""
    return await SeedingPresets.minimal_dataset(test_db_session)


@pytest_asyncio.fixture
async def integration_test_data(test_db_session: AsyncSession) -> Dict[str, Any]:
    """Provide comprehensive test dataset for integration tests."""
    return await SeedingPresets.integration_dataset(test_db_session)


@pytest_asyncio.fixture
async def performance_test_data(test_db_session: AsyncSession) -> Dict[str, Any]:
    """Provide large test dataset for performance tests."""
    return await SeedingPresets.performance_dataset(test_db_session, review_count=100)


@pytest_asyncio.fixture
async def e2e_test_data(test_db_session: AsyncSession) -> Dict[str, Any]:
    """Provide complete test dataset for E2E tests."""
    return await SeedingPresets.e2e_dataset(test_db_session)
