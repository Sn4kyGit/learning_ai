"""
Unit tests for Review Import Service.

Tests the ReviewImportService including Google Places integration,
duplicate detection, and database operations.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime

from backend.services.review_import_service import ReviewImportService
from backend.external.google_places import ImportResult
from backend.db.models import Business, Review
from backend.db.schemas import ReviewCreate


class TestReviewImportService:
    """Test suite for ReviewImportService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.google_client = Mock()
        self.review_repo = Mock()
        self.business_repo = Mock()
        self.language_detector = Mock()
        
        self.service = ReviewImportService(
            google_places_client=self.google_client,
            review_repository=self.review_repo,
            business_repository=self.business_repo,
            language_detector=self.language_detector,
        )
        
        # Test data
        self.business_id = uuid4()
        self.business = Mock()
        self.business.id = self.business_id
        self.business.name = "Test Restaurant"
        self.business.google_place_id = "test-place-123"

    @pytest.mark.asyncio
    async def test_import_reviews_for_business_success(self):
        """Test successful review import for a business."""
        # Arrange
        mock_reviews = [
            Mock(external_id="review-1", text="Great food!", author_name="John", rating=5, time=datetime.now()),
            Mock(external_id="review-2", text="Good service", author_name="Jane", rating=4, time=datetime.now()),
        ]
        
        google_import_result = ImportResult(
            total_found=2,
            imported_count=2,
            duplicate_count=0,
            error_count=0,
            errors=[],
            reviews=mock_reviews
        )
        
        self.business_repo.get = AsyncMock(return_value=self.business)
        self.google_client.import_reviews = AsyncMock(return_value=google_import_result)
        self.review_repo.get_by_external_id = AsyncMock(return_value=None)  # No duplicates
        self.language_detector.detect_language.return_value = "en"
        
        # Mock bulk import
        created_reviews = [Mock(), Mock()]
        self.review_repo.bulk_import_reviews = AsyncMock(return_value=created_reviews)
        self.business_repo.calculate_rating_stats = AsyncMock(return_value=(4.2, 50))
        self.business_repo.update_rating_stats = AsyncMock()

        # Act
        result = await self.service.import_reviews_for_business(self.business_id)

        # Assert
        assert result.total_found == 2
        assert result.imported_count == 2
        assert result.duplicate_count == 0
        assert result.error_count == 0
        
        # Verify Google client was called correctly
        self.google_client.import_reviews.assert_called_once_with(
            "test-place-123", str(self.business_id), 500
        )
        
        # Verify business stats were updated
        self.business_repo.update_rating_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_reviews_business_not_found(self):
        """Test import when business doesn't exist."""
        # Arrange
        self.business_repo.get = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="Business .* not found"):
            await self.service.import_reviews_for_business(self.business_id)

    @pytest.mark.asyncio
    async def test_import_reviews_no_new_reviews(self):
        """Test import when no new reviews are found."""
        # Arrange
        google_import_result = ImportResult(
            total_found=0,
            imported_count=0,
            duplicate_count=0,
            error_count=0,
            errors=[],
            reviews=[]
        )
        
        self.business_repo.get = AsyncMock(return_value=self.business)
        self.google_client.import_reviews = AsyncMock(return_value=google_import_result)

        # Act
        result = await self.service.import_reviews_for_business(self.business_id)

        # Assert
        assert result.imported_count == 0
        assert result.total_found == 0
        
        # Verify no database operations were performed
        self.review_repo.bulk_import_reviews.assert_not_called()

    @pytest.mark.asyncio
    async def test_import_reviews_with_duplicates(self):
        """Test import with duplicate detection."""
        # Arrange
        google_import_result = ImportResult(
            total_found=3,
            imported_count=3,
            duplicate_count=0,
            error_count=0,
            errors=[]
        )
        
        # Mock Google reviews
        mock_google_reviews = [
            Mock(external_id="review-1", text="Great food!", author_name="John", rating=5, time=datetime.now()),
            Mock(external_id="review-2", text="Good service", author_name="Jane", rating=4, time=datetime.now()),
            Mock(external_id="review-3", text="Average", author_name="Bob", rating=3, time=datetime.now()),
        ]
        
        google_import_result = ImportResult(
            total_found=3,
            imported_count=3,
            duplicate_count=0,
            error_count=0,
            errors=[],
            reviews=mock_google_reviews
        )
        
        self.business_repo.get = AsyncMock(return_value=self.business)
        self.google_client.import_reviews = AsyncMock(return_value=google_import_result)
        
        # Mock first review as duplicate, others as new
        def mock_get_by_external_id(business_id, external_id, source):
            if external_id == "review-1":
                return Mock()  # Existing review
            return None  # New review
        
        self.review_repo.get_by_external_id = AsyncMock(side_effect=mock_get_by_external_id)
        self.language_detector.detect_language.return_value = "en"
        
        # Mock bulk import for 2 new reviews
        created_reviews = [Mock(), Mock()]
        self.review_repo.bulk_import_reviews = AsyncMock(return_value=created_reviews)
        self.business_repo.calculate_rating_stats = AsyncMock(return_value=(4.0, 45))
        self.business_repo.update_rating_stats = AsyncMock()

        # Act
        result = await self.service.import_reviews_for_business(self.business_id)

        # Assert
        assert result.total_found == 3
        assert result.imported_count == 2  # Only 2 new reviews
        assert result.duplicate_count == 1  # 1 duplicate found
        
        # Verify bulk import was called with 2 reviews
        self.review_repo.bulk_import_reviews.assert_called_once()
        call_args = self.review_repo.bulk_import_reviews.call_args[0][0]
        assert len(call_args) == 2

    @pytest.mark.asyncio
    async def test_import_reviews_with_language_detection(self):
        """Test import with language detection."""
        # Arrange
        google_import_result = ImportResult(
            total_found=2,
            imported_count=2,
            duplicate_count=0,
            error_count=0,
            errors=[]
        )
        
        mock_google_reviews = [
            Mock(external_id="review-1", text="Great food!", author_name="John", rating=5, time=datetime.now()),
            Mock(external_id="review-2", text="Sehr gut!", author_name="Hans", rating=4, time=datetime.now()),
        ]
        
        google_import_result = ImportResult(
            total_found=2,
            imported_count=2,
            duplicate_count=0,
            error_count=0,
            errors=[],
            reviews=mock_google_reviews
        )
        
        self.business_repo.get = AsyncMock(return_value=self.business)
        self.google_client.import_reviews = AsyncMock(return_value=google_import_result)
        self.review_repo.get_by_external_id = AsyncMock(return_value=None)
        
        # Mock language detection
        def mock_detect_language(text):
            if "Sehr gut" in text:
                return "de"
            return "en"
        
        self.language_detector.detect_language.side_effect = mock_detect_language
        
        created_reviews = [Mock(), Mock()]
        self.review_repo.bulk_import_reviews = AsyncMock(return_value=created_reviews)
        self.business_repo.calculate_rating_stats = AsyncMock(return_value=(4.5, 25))
        self.business_repo.update_rating_stats = AsyncMock()

        # Act
        result = await self.service.import_reviews_for_business(self.business_id)

        # Assert
        assert result.imported_count == 2
        
        # Verify language detection was called for each review
        assert self.language_detector.detect_language.call_count == 2
        
        # Verify bulk import was called with correct language assignments
        call_args = self.review_repo.bulk_import_reviews.call_args[0][0]
        assert len(call_args) == 2
        # First review should be English, second German
        languages = [review.language for review in call_args]
        assert "en" in languages
        assert "de" in languages

    @pytest.mark.asyncio
    async def test_import_reviews_database_error(self):
        """Test import with database save error."""
        # Arrange
        google_import_result = ImportResult(
            total_found=1,
            imported_count=1,
            duplicate_count=0,
            error_count=0,
            errors=[]
        )
        
        mock_google_reviews = [
            Mock(external_id="review-1", text="Great food!", author_name="John", rating=5, time=datetime.now())
        ]
        
        google_import_result = ImportResult(
            total_found=1,
            imported_count=1,
            duplicate_count=0,
            error_count=0,
            errors=[],
            reviews=mock_google_reviews
        )
        
        self.business_repo.get = AsyncMock(return_value=self.business)
        self.google_client.import_reviews = AsyncMock(return_value=google_import_result)
        self.review_repo.get_by_external_id = AsyncMock(return_value=None)
        self.language_detector.detect_language.return_value = "en"
        
        # Mock database error
        self.review_repo.bulk_import_reviews = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        # Act
        result = await self.service.import_reviews_for_business(self.business_id)

        # Assert
        assert result.imported_count == 0
        assert result.error_count == 1
        assert "Failed to save reviews to database" in result.errors[0]

    @pytest.mark.asyncio
    async def test_import_reviews_for_multiple_businesses(self):
        """Test importing reviews for multiple businesses."""
        # Arrange
        business_ids = [uuid4(), uuid4(), uuid4()]
        
        # Mock successful import for first two, error for third
        async def mock_import_for_business(business_id, max_reviews):
            if business_id == business_ids[0]:
                return ImportResult(2, 2, 0, 0, [], [])
            elif business_id == business_ids[1]:
                return ImportResult(1, 1, 0, 0, [], [])
            else:
                raise Exception("Import failed for business 3")
        
        self.service.import_reviews_for_business = AsyncMock(side_effect=mock_import_for_business)

        # Act
        results = await self.service.import_reviews_for_multiple_businesses(business_ids)

        # Assert
        assert len(results) == 3
        
        # First business: successful
        assert results[str(business_ids[0])].imported_count == 2
        assert results[str(business_ids[0])].error_count == 0
        
        # Second business: successful
        assert results[str(business_ids[1])].imported_count == 1
        assert results[str(business_ids[1])].error_count == 0
        
        # Third business: error
        assert results[str(business_ids[2])].imported_count == 0
        assert results[str(business_ids[2])].error_count == 1

    @pytest.mark.asyncio
    async def test_import_reviews_with_retry_success_first_attempt(self):
        """Test retry logic succeeds on first attempt."""
        # Arrange
        expected_result = ImportResult(1, 1, 0, 0, [], [])
        self.service.import_reviews_for_business = AsyncMock(return_value=expected_result)

        # Act
        result = await self.service.import_reviews_with_retry(self.business_id)

        # Assert
        assert result == expected_result
        assert self.service.import_reviews_for_business.call_count == 1

    @pytest.mark.asyncio
    async def test_import_reviews_with_retry_success_after_failures(self):
        """Test retry logic succeeds after initial failures."""
        # Arrange
        expected_result = ImportResult(1, 1, 0, 0, [], [])
        
        # Mock to fail twice, then succeed
        side_effects = [
            Exception("API error 1"),
            Exception("API error 2"),
            expected_result
        ]
        
        self.service.import_reviews_for_business = AsyncMock(side_effect=side_effects)
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Act
            result = await self.service.import_reviews_with_retry(
                self.business_id, max_retries=3
            )
            
            # Assert
            assert result == expected_result
            assert self.service.import_reviews_for_business.call_count == 3
            assert mock_sleep.call_count == 2  # Two retries

    @pytest.mark.asyncio
    async def test_import_reviews_with_retry_all_attempts_fail(self):
        """Test retry logic when all attempts fail."""
        # Arrange
        error_message = "Persistent import error"
        self.service.import_reviews_for_business = AsyncMock(
            side_effect=Exception(error_message)
        )
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            # Act & Assert
            with pytest.raises(Exception, match=error_message):
                await self.service.import_reviews_with_retry(
                    self.business_id, max_retries=2
                )

    @pytest.mark.asyncio
    async def test_validate_business_place_id_valid(self):
        """Test business place ID validation for valid place."""
        # Arrange
        self.business_repo.get = AsyncMock(return_value=self.business)
        self.google_client.validate_place_id = AsyncMock(return_value=True)

        # Act
        result = await self.service.validate_business_place_id(self.business_id)

        # Assert
        assert result is True
        self.google_client.validate_place_id.assert_called_once_with("test-place-123")

    @pytest.mark.asyncio
    async def test_validate_business_place_id_business_not_found(self):
        """Test place ID validation when business doesn't exist."""
        # Arrange
        self.business_repo.get = AsyncMock(return_value=None)

        # Act
        result = await self.service.validate_business_place_id(self.business_id)

        # Assert
        assert result is False
        self.google_client.validate_place_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_business_place_id_no_place_id(self):
        """Test place ID validation when business has no place ID."""
        # Arrange
        business_without_place_id = Mock()
        business_without_place_id.google_place_id = None
        self.business_repo.get = AsyncMock(return_value=business_without_place_id)

        # Act
        result = await self.service.validate_business_place_id(self.business_id)

        # Assert
        assert result is False
        self.google_client.validate_place_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_import_statistics_success(self):
        """Test getting import statistics for a business."""
        # Arrange
        mock_stats = {
            "total_reviews": 150,
            "avg_rating": 4.2,
            "recent_reviews_30d": 25,
            "language_distribution": {"en": 100, "de": 30, "tr": 20},
            "first_review": datetime(2023, 1, 1),
            "latest_review": datetime(2024, 1, 1),
        }
        
        self.business_repo.get = AsyncMock(return_value=self.business)
        self.review_repo.get_review_statistics = AsyncMock(return_value=mock_stats)

        # Act
        result = await self.service.get_import_statistics(self.business_id)

        # Assert
        assert result["business_id"] == str(self.business_id)
        assert result["business_name"] == "Test Restaurant"
        assert result["google_place_id"] == "test-place-123"
        assert result["total_reviews"] == 150
        assert result["avg_rating"] == 4.2
        assert result["recent_reviews_30d"] == 25

    @pytest.mark.asyncio
    async def test_get_import_statistics_error(self):
        """Test getting import statistics with error."""
        # Arrange
        self.review_repo.get_review_statistics = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Act
        result = await self.service.get_import_statistics(self.business_id)

        # Assert
        assert result["business_id"] == str(self.business_id)
        assert "error" in result
        assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_schedule_daily_import_success(self):
        """Test scheduled daily import for all businesses."""
        # Arrange
        businesses = [
            Mock(id=uuid4(), name="Restaurant 1"),
            Mock(id=uuid4(), name="Restaurant 2"),
        ]
        
        self.business_repo.get_businesses_needing_analysis = AsyncMock(return_value=businesses)
        
        # Mock import results
        import_results = {
            str(businesses[0].id): ImportResult(2, 2, 0, 0, [], []),
            str(businesses[1].id): ImportResult(1, 1, 0, 0, [], []),
        }
        
        self.service.import_reviews_for_multiple_businesses = AsyncMock(return_value=import_results)

        # Act
        result = await self.service.schedule_daily_import()

        # Assert
        assert result["businesses_processed"] == 2
        assert result["total_imported"] == 3
        assert result["total_errors"] == 0
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_schedule_daily_import_no_businesses(self):
        """Test scheduled daily import when no businesses need analysis."""
        # Arrange
        self.business_repo.get_businesses_needing_analysis = AsyncMock(return_value=[])

        # Act
        result = await self.service.schedule_daily_import()

        # Assert
        assert result["businesses_processed"] == 0
        assert result["total_imported"] == 0
        assert result["total_errors"] == 0
        assert len(result["results"]) == 0