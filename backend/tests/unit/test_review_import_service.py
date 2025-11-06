"""
Unit tests for Review Import Service.

This module serves as the main entry point for review import tests.
The actual test classes have been moved to specialized modules
for better organization and maintainability.

Test modules:
- review_import/test_basic_import.py - Core import functionality
- review_import/test_duplicate_detection.py - Duplicate handling
- review_import/test_language_detection.py - Language detection (can be added)
- review_import/test_retry_logic.py - Retry mechanisms (can be added)
- review_import/test_statistics.py - Import statistics (can be added)
- review_import/test_scheduling.py - Scheduled imports (can be added)
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime

from backend.services.review_import_service import ReviewImportService
from backend.external.google_places import ImportResult
from backend.db.models import Business, Review
from backend.db.schemas import ReviewCreate


# Import fixtures from the review_import conftest
@pytest.fixture
def mock_google_client():
    """Create mock Google Places client."""
    return AsyncMock()


@pytest.fixture
def mock_review_repo():
    """Create mock review repository."""
    return AsyncMock()


@pytest.fixture
def mock_business_repo():
    """Create mock business repository."""
    return AsyncMock()


@pytest.fixture
def mock_language_detector():
    """Create mock language detector."""
    mock = Mock()
    mock.detect_language.return_value = "en"  # Return a string instead of Mock
    return mock


@pytest.fixture
def review_import_service(mock_google_client, mock_review_repo, mock_business_repo, mock_language_detector):
    """Create ReviewImportService with mocked dependencies."""
    return ReviewImportService(
        google_places_client=mock_google_client,
        review_repository=mock_review_repo,
        business_repository=mock_business_repo,
        language_detector=mock_language_detector,
    )


@pytest.fixture
def test_business():
    """Create test business mock."""
    business = Mock()
    business.id = uuid4()
    business.name = "Test Restaurant"
    business.google_place_id = "test-place-123"
    return business


@pytest.fixture
def sample_reviews():
    """Create sample review data."""
    return [
        Mock(
            external_id="review-1",
            text="Great food!",
            author_name="John",
            rating=5,
            time=datetime.now(),
            language="en",
            profile_photo_url=None,
            relative_time_description="2 days ago"
        ),
        Mock(
            external_id="review-2",
            text="Good service",
            author_name="Jane",
            rating=4,
            time=datetime.now(),
            language="en",
            profile_photo_url=None,
            relative_time_description="1 day ago"
        ),
    ]


# Import test classes from specialized modules for backward compatibility
from .review_import.test_basic_import import TestBasicReviewImport
from .review_import.test_duplicate_detection import TestDuplicateDetection

# Maintain backward compatibility by re-exporting the main test class
TestReviewImportService = TestBasicReviewImport

__all__ = [
    'TestReviewImportService',
    'TestBasicReviewImport',
    'TestDuplicateDetection'
]