"""
Unit tests for Google Places API client.

Tests the GooglePlacesClient including review import, duplicate detection,
retry logic, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import hashlib

from backend.external.google_places import (
    GooglePlacesClient,
    GoogleReview,
    ImportResult,
)


class TestGooglePlacesClient:
    """Test suite for GooglePlacesClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"
        self.client = GooglePlacesClient(self.api_key)
        
        # Test data
        self.place_id = "test-place-123"
        self.business_id = "business-456"

    @pytest.mark.asyncio
    async def test_get_place_details_success(self):
        """Test successful place details retrieval."""
        # Arrange
        mock_response = {
            "status": "OK",
            "result": {
                "name": "Test Restaurant",
                "rating": 4.2,
                "user_ratings_total": 150,
                "reviews": [
                    {
                        "author_name": "John Doe",
                        "rating": 5,
                        "text": "Great food!",
                        "time": 1640995200,  # 2022-01-01
                        "language": "en"
                    }
                ]
            }
        }
        
        with patch.object(self.client, 'get', return_value=mock_response):
            # Act
            result = await self.client.get_place_details(self.place_id)
            
            # Assert
            assert result["name"] == "Test Restaurant"
            assert result["rating"] == 4.2
            assert len(result["reviews"]) == 1

    @pytest.mark.asyncio
    async def test_get_place_details_api_error(self):
        """Test place details retrieval with API error."""
        # Arrange
        mock_response = {
            "status": "NOT_FOUND",
            "error_message": "Place not found"
        }
        
        with patch.object(self.client, 'get', return_value=mock_response):
            # Act & Assert
            with pytest.raises(Exception, match="Google Places API error: NOT_FOUND"):
                await self.client.get_place_details(self.place_id)

    @pytest.mark.asyncio
    async def test_import_reviews_success(self):
        """Test successful review import."""
        # Arrange
        mock_place_details = {
            "reviews": [
                {
                    "author_name": "John Doe",
                    "rating": 5,
                    "text": "Excellent food and service!",
                    "time": 1640995200,
                    "language": "en"
                },
                {
                    "author_name": "Jane Smith",
                    "rating": 2,
                    "text": "Food was cold.",
                    "time": 1640995300,
                    "language": "en"
                }
            ]
        }
        
        with patch.object(self.client, 'get_place_details', return_value=mock_place_details):
            with patch.object(self.client, '_check_review_exists', return_value=False):
                # Act
                result = await self.client.import_reviews(self.place_id, self.business_id)
                
                # Assert
                assert isinstance(result, ImportResult)
                assert result.total_found == 2
                assert result.imported_count == 2
                assert result.duplicate_count == 0
                assert result.error_count == 0
                assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_import_reviews_no_reviews(self):
        """Test import when no reviews are found."""
        # Arrange
        mock_place_details = {"reviews": []}
        
        with patch.object(self.client, 'get_place_details', return_value=mock_place_details):
            # Act
            result = await self.client.import_reviews(self.place_id, self.business_id)
            
            # Assert
            assert result.total_found == 0
            assert result.imported_count == 0
            assert result.duplicate_count == 0
            assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_import_reviews_with_duplicates(self):
        """Test import with duplicate detection."""
        # Arrange
        mock_place_details = {
            "reviews": [
                {
                    "author_name": "John Doe",
                    "rating": 5,
                    "text": "Great food!",
                    "time": 1640995200,
                    "language": "en"
                },
                {
                    "author_name": "Jane Smith",
                    "rating": 4,
                    "text": "Good service.",
                    "time": 1640995300,
                    "language": "en"
                }
            ]
        }
        
        # Mock first review as duplicate, second as new
        def mock_check_exists(business_id, external_id):
            # First review is duplicate
            return external_id == self.client._generate_external_id(mock_place_details["reviews"][0])
        
        with patch.object(self.client, 'get_place_details', return_value=mock_place_details):
            with patch.object(self.client, '_check_review_exists', side_effect=mock_check_exists):
                # Act
                result = await self.client.import_reviews(self.place_id, self.business_id)
                
                # Assert
                assert result.total_found == 2
                assert result.imported_count == 1
                assert result.duplicate_count == 1
                assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_import_reviews_with_parsing_errors(self):
        """Test import with review parsing errors."""
        # Arrange
        mock_place_details = {
            "reviews": [
                {
                    "author_name": "John Doe",
                    "rating": 5,
                    "text": "Great food!",
                    "time": 1640995200,
                    "language": "en"
                },
                {
                    # Missing required fields
                    "author_name": "Jane Smith",
                    "text": "Good service.",
                    # Missing rating and time
                }
            ]
        }
        
        with patch.object(self.client, 'get_place_details', return_value=mock_place_details):
            with patch.object(self.client, '_check_review_exists', return_value=False):
                # Act
                result = await self.client.import_reviews(self.place_id, self.business_id)
                
                # Assert
                assert result.total_found == 2
                assert result.imported_count == 1
                assert result.duplicate_count == 0
                assert result.error_count == 1
                assert len(result.errors) == 1
                assert "Failed to parse review" in result.errors[0]

    @pytest.mark.asyncio
    async def test_import_reviews_max_limit(self):
        """Test import respects max_reviews limit."""
        # Arrange
        mock_reviews = [
            {
                "author_name": f"User {i}",
                "rating": 4,
                "text": f"Review {i}",
                "time": 1640995200 + i,
                "language": "en"
            }
            for i in range(10)
        ]
        mock_place_details = {"reviews": mock_reviews}
        
        with patch.object(self.client, 'get_place_details', return_value=mock_place_details):
            with patch.object(self.client, '_check_review_exists', return_value=False):
                # Act
                result = await self.client.import_reviews(self.place_id, self.business_id, max_reviews=5)
                
                # Assert
                assert result.total_found == 10
                assert result.imported_count == 5  # Limited to max_reviews

    def test_parse_google_review_success(self):
        """Test successful Google review parsing."""
        # Arrange
        raw_review = {
            "author_name": "John Doe",
            "rating": 5,
            "text": "Excellent food and service!",
            "time": 1640995200,
            "language": "en",
            "profile_photo_url": "https://example.com/photo.jpg",
            "relative_time_description": "2 weeks ago"
        }
        
        # Act
        review = self.client._parse_google_review(raw_review)
        
        # Assert
        assert isinstance(review, GoogleReview)
        assert review.author_name == "John Doe"
        assert review.rating == 5
        assert review.text == "Excellent food and service!"
        assert review.language == "en"
        assert review.profile_photo_url == "https://example.com/photo.jpg"
        assert review.relative_time_description == "2 weeks ago"
        assert isinstance(review.time, datetime)

    def test_parse_google_review_missing_required_fields(self):
        """Test review parsing with missing required fields."""
        # Arrange
        raw_review = {
            "author_name": "John Doe",
            "text": "Good food",
            # Missing rating and time
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Missing required fields"):
            self.client._parse_google_review(raw_review)

    def test_parse_google_review_defaults(self):
        """Test review parsing with default values."""
        # Arrange
        raw_review = {
            "rating": 4,
            "time": 1640995200,
            # Missing optional fields
        }
        
        # Act
        review = self.client._parse_google_review(raw_review)
        
        # Assert
        assert review.author_name == "Anonymous"
        assert review.text == ""
        assert review.language == "en"
        assert review.profile_photo_url is None

    def test_generate_external_id_consistency(self):
        """Test external ID generation is consistent."""
        # Arrange
        raw_review = {
            "author_name": "John Doe",
            "time": 1640995200,
            "text": "Great food!"
        }
        
        # Act
        id1 = self.client._generate_external_id(raw_review)
        id2 = self.client._generate_external_id(raw_review)
        
        # Assert
        assert id1 == id2
        assert len(id1) == 32  # MD5 hash length

    def test_generate_external_id_uniqueness(self):
        """Test external ID generation creates unique IDs for different reviews."""
        # Arrange
        review1 = {
            "author_name": "John Doe",
            "time": 1640995200,
            "text": "Great food!"
        }
        review2 = {
            "author_name": "Jane Smith",
            "time": 1640995200,
            "text": "Great food!"
        }
        
        # Act
        id1 = self.client._generate_external_id(review1)
        id2 = self.client._generate_external_id(review2)
        
        # Assert
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_validate_place_id_valid(self):
        """Test place ID validation for valid place."""
        # Arrange
        mock_response = {"status": "OK", "result": {"place_id": self.place_id}}
        
        with patch.object(self.client, 'get', return_value=mock_response):
            # Act
            result = await self.client.validate_place_id(self.place_id)
            
            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_place_id_invalid(self):
        """Test place ID validation for invalid place."""
        # Arrange
        mock_response = {"status": "NOT_FOUND"}
        
        with patch.object(self.client, 'get', return_value=mock_response):
            # Act
            result = await self.client.validate_place_id(self.place_id)
            
            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_validate_place_id_api_error(self):
        """Test place ID validation with API error."""
        # Arrange
        with patch.object(self.client, 'get', side_effect=Exception("API error")):
            # Act
            result = await self.client.validate_place_id(self.place_id)
            
            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_import_reviews_with_retry_success_first_attempt(self):
        """Test retry logic succeeds on first attempt."""
        # Arrange
        expected_result = ImportResult(
            total_found=1,
            imported_count=1,
            duplicate_count=0,
            error_count=0,
            errors=[]
        )
        
        with patch.object(self.client, 'import_reviews', return_value=expected_result) as mock_import:
            # Act
            result = await self.client.import_reviews_with_retry(self.place_id, self.business_id)
            
            # Assert
            assert result == expected_result
            assert mock_import.call_count == 1

    @pytest.mark.asyncio
    async def test_import_reviews_with_retry_success_after_failures(self):
        """Test retry logic succeeds after initial failures."""
        # Arrange
        expected_result = ImportResult(
            total_found=1,
            imported_count=1,
            duplicate_count=0,
            error_count=0,
            errors=[]
        )
        
        # Mock to fail twice, then succeed
        side_effects = [
            Exception("API error 1"),
            Exception("API error 2"),
            expected_result
        ]
        
        with patch.object(self.client, 'import_reviews', side_effect=side_effects) as mock_import:
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                # Act
                result = await self.client.import_reviews_with_retry(
                    self.place_id, self.business_id, max_retries=3
                )
                
                # Assert
                assert result == expected_result
                assert mock_import.call_count == 3
                assert mock_sleep.call_count == 2  # Two retries

    @pytest.mark.asyncio
    async def test_import_reviews_with_retry_all_attempts_fail(self):
        """Test retry logic when all attempts fail."""
        # Arrange
        error_message = "Persistent API error"
        
        with patch.object(self.client, 'import_reviews', side_effect=Exception(error_message)):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                # Act & Assert
                with pytest.raises(Exception, match=error_message):
                    await self.client.import_reviews_with_retry(
                        self.place_id, self.business_id, max_retries=2
                    )

    @pytest.mark.asyncio
    async def test_batch_import_reviews_success(self):
        """Test successful batch import for multiple businesses."""
        # Arrange
        place_business_pairs = [
            ("place-1", "business-1"),
            ("place-2", "business-2"),
        ]
        
        expected_results = {
            "business-1": ImportResult(1, 1, 0, 0, []),
            "business-2": ImportResult(2, 2, 0, 0, []),
        }
        
        def mock_import_with_retry(place_id, business_id, max_reviews):
            return expected_results[business_id]
        
        with patch.object(self.client, 'import_reviews_with_retry', side_effect=mock_import_with_retry):
            # Act
            results = await self.client.batch_import_reviews(place_business_pairs)
            
            # Assert
            assert len(results) == 2
            assert results["business-1"].imported_count == 1
            assert results["business-2"].imported_count == 2

    @pytest.mark.asyncio
    async def test_batch_import_reviews_partial_failure(self):
        """Test batch import with some businesses failing."""
        # Arrange
        place_business_pairs = [
            ("place-1", "business-1"),
            ("place-2", "business-2"),
        ]
        
        def mock_import_with_retry(place_id, business_id, max_reviews):
            if business_id == "business-1":
                return ImportResult(1, 1, 0, 0, [])
            else:
                raise Exception("API error for business-2")
        
        with patch.object(self.client, 'import_reviews_with_retry', side_effect=mock_import_with_retry):
            # Act
            results = await self.client.batch_import_reviews(place_business_pairs)
            
            # Assert
            assert len(results) == 2
            assert results["business-1"].imported_count == 1
            assert results["business-2"].error_count == 1
            assert "API error for business-2" in results["business-2"].errors[0]

    @pytest.mark.asyncio
    async def test_search_places_success(self):
        """Test successful place search."""
        # Arrange
        mock_response = {
            "status": "OK",
            "results": [
                {
                    "place_id": "place-1",
                    "name": "Restaurant 1",
                    "rating": 4.2
                },
                {
                    "place_id": "place-2",
                    "name": "Restaurant 2",
                    "rating": 4.5
                }
            ]
        }
        
        with patch.object(self.client, 'get', return_value=mock_response):
            # Act
            results = await self.client.search_places("Italian restaurant")
            
            # Assert
            assert len(results) == 2
            assert results[0]["name"] == "Restaurant 1"
            assert results[1]["name"] == "Restaurant 2"

    @pytest.mark.asyncio
    async def test_search_places_no_results(self):
        """Test place search with no results."""
        # Arrange
        mock_response = {
            "status": "ZERO_RESULTS",
            "results": []
        }
        
        with patch.object(self.client, 'get', return_value=mock_response):
            # Act
            results = await self.client.search_places("Nonexistent restaurant")
            
            # Assert
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_place_photos_success(self):
        """Test successful photo retrieval."""
        # Arrange
        mock_response = {
            "status": "OK",
            "result": {
                "photos": [
                    {"photo_reference": "ref1"},
                    {"photo_reference": "ref2"}
                ]
            }
        }
        
        with patch.object(self.client, 'get', return_value=mock_response):
            # Act
            photos = await self.client.get_place_photos(self.place_id)
            
            # Assert
            assert len(photos) == 2
            assert "ref1" in photos[0]
            assert "ref2" in photos[1]
            assert all("photoreference=" in url for url in photos)

    @pytest.mark.asyncio
    async def test_get_place_photos_no_photos(self):
        """Test photo retrieval when no photos exist."""
        # Arrange
        mock_response = {
            "status": "OK",
            "result": {}
        }
        
        with patch.object(self.client, 'get', return_value=mock_response):
            # Act
            photos = await self.client.get_place_photos(self.place_id)
            
            # Assert
            assert len(photos) == 0