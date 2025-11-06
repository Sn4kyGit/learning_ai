"""
Unit tests for duplicate detection in review import.

This module tests duplicate review detection and handling
during the import process.
"""

import pytest
from unittest.mock import Mock
from uuid import uuid4
from datetime import datetime

from backend.external.google_places import ImportResult
from backend.db.models import Review


class TestDuplicateDetection:
    """Test suite for duplicate review detection."""

    @pytest.mark.asyncio
    async def test_import_reviews_with_duplicates(
        self, review_import_service, mock_google_client, mock_review_repo,
        mock_business_repo, test_business
    ):
        """Test import with duplicate detection."""
        # Arrange
        existing_review = Mock()
        existing_review.external_id = "review-1"
        
        new_reviews = [
            Mock(external_id="review-1", text="Existing review", author_name="John", rating=5, time=datetime.now(), language="en", profile_photo_url=None, relative_time_description="2 days ago"),
            Mock(external_id="review-2", text="New review", author_name="Jane", rating=4, time=datetime.now(), language="en", profile_photo_url=None, relative_time_description="1 day ago"),
        ]
        
        mock_business_repo.get.return_value = test_business
        mock_business_repo.calculate_rating_stats.return_value = (4.5, 10)
        mock_business_repo.update_rating_stats.return_value = None
        mock_google_client.import_reviews.return_value = ImportResult(
            reviews=new_reviews,
            total_found=2,
            imported_count=1,  # One is duplicate
            duplicate_count=1,
            error_count=0,
            errors=[]
        )
        
        # Mock duplicate detection - first review exists, second doesn't
        def mock_get_by_external_id(business_id, external_id, source):
            if external_id == "review-1":
                return existing_review
            return None
        
        mock_review_repo.get_by_external_id.side_effect = mock_get_by_external_id
        mock_review_repo.bulk_import_reviews.return_value = [Mock()]  # Return 1 created review (second one)
        
        # Act
        result = await review_import_service.import_reviews_for_business(test_business.id)
        
        # Assert
        assert result.imported_count == 1  # Only one new review saved
        assert result.total_found == 2
        assert mock_review_repo.bulk_import_reviews.call_count == 1  # Only called once with new reviews

    @pytest.mark.asyncio
    async def test_import_reviews_all_duplicates(
        self, review_import_service, mock_google_client, mock_review_repo,
        mock_business_repo, test_business
    ):
        """Test import when all reviews are duplicates."""
        # Arrange
        existing_reviews = [
            Mock(external_id="review-1"),
            Mock(external_id="review-2"),
        ]
        
        new_reviews = [
            Mock(external_id="review-1", text="Existing review 1", author_name="John", rating=5, time=datetime.now()),
            Mock(external_id="review-2", text="Existing review 2", author_name="Jane", rating=4, time=datetime.now()),
        ]
        
        mock_business_repo.get.return_value = test_business
        mock_google_client.import_reviews.return_value = ImportResult(
            reviews=new_reviews,
            total_found=2,
            imported_count=0,  # All are duplicates
            duplicate_count=2,
            error_count=0,
            errors=[]
        )
        
        # All reviews are duplicates
        mock_review_repo.get_by_external_id.side_effect = lambda business_id, external_id, source: existing_reviews[0] if external_id in ["review-1", "review-2"] else None
        
        # Act
        result = await review_import_service.import_reviews_for_business(test_business.id)
        
        # Assert
        assert result.imported_count == 0
        assert result.total_found == 2
        assert mock_review_repo.create.call_count == 0  # No new reviews created

    # Note: Duplicate detection is tested through the main import methods above
    # The logic is integrated into the import workflow and doesn't need separate testing