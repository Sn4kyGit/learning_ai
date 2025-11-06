"""
Unit tests for basic review import functionality.

This module tests core review import operations including
successful imports, error handling, and business validation.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from backend.external.google_places import ImportResult
from backend.db.models import Business, Review
from backend.db.schemas import ReviewCreate


class TestBasicReviewImport:
    """Test suite for basic review import operations."""

    @pytest.mark.asyncio
    async def test_import_reviews_for_business_success(
        self, review_import_service, mock_google_client, mock_review_repo, 
        mock_business_repo, test_business, sample_reviews
    ):
        """Test successful review import for a business."""
        # Arrange
        mock_business_repo.get.return_value = test_business
        mock_business_repo.calculate_rating_stats.return_value = (4.5, 10)  # avg_rating, total_reviews
        mock_business_repo.update_rating_stats.return_value = None
        mock_google_client.import_reviews.return_value = ImportResult(
            reviews=sample_reviews,
            total_found=2,
            imported_count=2,
            duplicate_count=0,
            error_count=0,
            errors=[]
        )
        mock_review_repo.get_by_external_id.return_value = None  # No duplicates
        mock_review_repo.bulk_import_reviews.return_value = [Mock(), Mock()]  # Return 2 created reviews
        
        # Act
        result = await review_import_service.import_reviews_for_business(test_business.id)
        
        # Assert
        assert result.imported_count == 2
        assert result.total_found == 2
        assert mock_review_repo.bulk_import_reviews.call_count == 1

    @pytest.mark.asyncio
    async def test_import_reviews_business_not_found(
        self, review_import_service, mock_business_repo
    ):
        """Test import when business doesn't exist."""
        # Arrange
        business_id = uuid4()
        mock_business_repo.get.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Business .* not found"):
            await review_import_service.import_reviews_for_business(business_id)

    @pytest.mark.asyncio
    async def test_import_reviews_no_new_reviews(
        self, review_import_service, mock_google_client, mock_business_repo, test_business
    ):
        """Test import when no new reviews are found."""
        # Arrange
        mock_business_repo.get.return_value = test_business
        mock_google_client.import_reviews.return_value = ImportResult(
            reviews=[],
            total_found=0,
            imported_count=0,
            duplicate_count=0,
            error_count=0,
            errors=[]
        )
        
        # Act
        result = await review_import_service.import_reviews_for_business(test_business.id)
        
        # Assert
        assert result.imported_count == 0
        assert result.total_found == 0

    @pytest.mark.asyncio
    async def test_import_reviews_database_error(
        self, review_import_service, mock_google_client, mock_review_repo,
        mock_business_repo, test_business, sample_reviews
    ):
        """Test import with database save error."""
        # Arrange
        mock_business_repo.get.return_value = test_business
        mock_google_client.import_reviews.return_value = ImportResult(
            reviews=sample_reviews,
            total_found=2,
            imported_count=2,
            duplicate_count=0,
            error_count=0,
            errors=[]
        )
        mock_review_repo.get_by_external_id.return_value = None
        mock_review_repo.bulk_import_reviews.side_effect = Exception("Database error")
        
        # Act
        result = await review_import_service.import_reviews_for_business(test_business.id)
        
        # Assert
        assert result.imported_count == 0  # No reviews imported due to error
        assert result.error_count == 2  # 2 reviews failed to import
        assert len(result.errors) == 1  # One error message
        assert "Database error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_business_place_id_valid(
        self, review_import_service, mock_business_repo, test_business
    ):
        """Test business place ID validation for valid place."""
        # Arrange
        mock_business_repo.get.return_value = test_business
        # Need to mock the Google client's validate_place_id method
        mock_google_client = review_import_service._google_client
        mock_google_client.validate_place_id.return_value = True
        
        # Act
        result = await review_import_service.validate_business_place_id(test_business.id)
        
        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_business_place_id_business_not_found(
        self, review_import_service, mock_business_repo
    ):
        """Test place ID validation when business doesn't exist."""
        # Arrange
        business_id = uuid4()
        mock_business_repo.get.return_value = None
        
        # Act
        result = await review_import_service.validate_business_place_id(business_id)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_business_place_id_no_place_id(
        self, review_import_service, mock_business_repo
    ):
        """Test place ID validation when business has no place ID."""
        # Arrange
        business = Mock()
        business.id = uuid4()
        business.google_place_id = None
        mock_business_repo.get.return_value = business
        
        # Act
        result = await review_import_service.validate_business_place_id(business.id)
        
        # Assert
        assert result is False