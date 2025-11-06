"""
Unit tests for database models and connections.

This module tests the database models, relationships, and basic CRUD operations
to ensure the database layer is working correctly.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from datetime import datetime, timezone

from backend.db.models import Organization, Business, User, Review, Classification


class TestDatabaseModels:
    """Test database models and relationships."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_organization_creation(self, test_db_session: AsyncSession):
        """Test creating an organization."""
        org = Organization(
            name="Test Restaurant Group",
            subscription_tier="premium",
            cost_limit_monthly=200.00,
        )

        test_db_session.add(org)
        await test_db_session.commit()
        await test_db_session.refresh(org)

        assert org.id is not None
        assert org.name == "Test Restaurant Group"
        assert org.subscription_tier == "premium"
        assert org.cost_limit_monthly == 200.00

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_business_creation(
        self, test_db_session: AsyncSession, test_organization: Organization
    ):
        """Test creating a business."""
        business = Business(
            name="Test Restaurant",
            google_place_id="test-place-123",
            category="restaurant",
            address="123 Test Street",
            organization_id=test_organization.id,
        )

        test_db_session.add(business)
        await test_db_session.commit()
        await test_db_session.refresh(business)

        assert business.id is not None
        assert business.name == "Test Restaurant"
        assert business.google_place_id == "test-place-123"
        assert business.organization_id == test_organization.id

    @pytest.mark.asyncio
    async def test_user_creation(
        self, test_db_session: AsyncSession, test_organization: Organization
    ):
        """Test creating a user."""
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

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.role == "admin"
        assert user.organization_id == test_organization.id

    @pytest.mark.asyncio
    async def test_review_creation(
        self, test_db_session: AsyncSession, test_business: Business
    ):
        """Test creating a review."""
        from datetime import datetime

        review = Review(
            business_id=test_business.id,
            author_name="John Doe",
            rating=5,
            text="Great food and service!",
            language="en",
            published_at=datetime.now(timezone.utc),
            source="google",
            external_id="review-123",
        )

        test_db_session.add(review)
        await test_db_session.commit()
        await test_db_session.refresh(review)

        assert review.id is not None
        assert review.business_id == test_business.id
        assert review.rating == 5
        assert review.text == "Great food and service!"

    @pytest.mark.asyncio
    async def test_classification_creation(
        self, test_db_session: AsyncSession, test_reviews: list
    ):
        """Test creating a classification."""
        review = test_reviews[0]

        classification = Classification(
            review_id=review.id,
            sentiment="positive",
            topics=["food_quality", "service"],  # JSON array
            urgency="low",
            competitor_mentioned=False,
            confidence_score=0.95,
            ai_model="test-model",
            processing_time_ms=100,
        )

        test_db_session.add(classification)
        await test_db_session.commit()
        await test_db_session.refresh(classification)

        assert classification.id is not None
        assert classification.review_id == review.id
        assert classification.sentiment == "positive"
        assert classification.topics == ["food_quality", "service"]
        assert float(classification.confidence_score) == 0.95

    @pytest.mark.asyncio
    async def test_business_organization_relationship(
        self, test_db_session: AsyncSession, test_business: Business
    ):
        """Test the relationship between business and organization."""
        # Load the business with its organization
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await test_db_session.execute(
            select(Business)
            .options(selectinload(Business.organization))
            .where(Business.id == test_business.id)
        )
        business = result.scalar_one()

        assert business.organization is not None
        assert business.organization.name == "Test Restaurant Group"

    @pytest.mark.asyncio
    async def test_review_business_relationship(
        self, test_db_session: AsyncSession, test_reviews: list
    ):
        """Test the relationship between review and business."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        review = test_reviews[0]

        result = await test_db_session.execute(
            select(Review)
            .options(selectinload(Review.business))
            .where(Review.id == review.id)
        )
        loaded_review = result.scalar_one()

        assert loaded_review.business is not None
        assert loaded_review.business.name == "Test Restaurant"

    @pytest.mark.asyncio
    async def test_unique_constraints(
        self, test_db_session: AsyncSession, test_business: Business
    ):
        """Test unique constraints work correctly."""
        from sqlalchemy.exc import IntegrityError

        # Try to create a review with the same external_id
        review1 = Review(
            business_id=test_business.id,
            text="First review",
            published_at=datetime.now(timezone.utc),
            source="google",
            external_id="duplicate-id",
        )

        review2 = Review(
            business_id=test_business.id,
            text="Second review",
            published_at=datetime.now(timezone.utc),
            source="google",
            external_id="duplicate-id",
        )

        test_db_session.add(review1)
        await test_db_session.commit()

        test_db_session.add(review2)

        with pytest.raises(IntegrityError):
            await test_db_session.commit()


class TestDatabaseConnection:
    """Test database connection and session management."""

    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test database initialization."""
        from backend.db.database import init_database

        # This should not raise any exceptions
        await init_database()

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test database session creation."""
        from backend.db.database import get_db_session

        session_created = False
        async for session in get_db_session():
            assert session is not None
            session_created = True
            break

        assert session_created

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, test_db_session: AsyncSession):
        """Test that sessions rollback properly on errors."""
        # Create an invalid operation that will cause an error
        try:
            # This should cause an error due to missing required fields
            invalid_org = Organization()
            test_db_session.add(invalid_org)
            await test_db_session.commit()
        except Exception:
            # Explicitly rollback the session
            await test_db_session.rollback()

        # Session should still be usable after the error
        valid_org = Organization(name="Valid Org")
        test_db_session.add(valid_org)
        await test_db_session.commit()
        await test_db_session.refresh(valid_org)

        assert valid_org.id is not None