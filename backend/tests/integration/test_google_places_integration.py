"""
Integration tests for Google Places API client.

Tests the GooglePlacesClient with mocked HTTP responses to simulate
real API interactions including error scenarios and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
import json

from backend.external.google_places import GooglePlacesClient, ImportResult
from backend.external.base_client import BaseHTTPClient


class TestGooglePlacesIntegration:
    """Integration test suite for GooglePlacesClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"
        self.client = GooglePlacesClient(self.api_key)
        self.place_id = "ChIJN1t_tDeuEmsRUsoyG83frY4"  # Real-looking place ID
        self.business_id = "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_full_import_workflow_success(self):
        """Test complete import workflow from API call to result processing."""
        # Arrange
        mock_api_response = {
            "status": "OK",
            "result": {
                "name": "Mario's Italian Restaurant",
                "rating": 4.3,
                "user_ratings_total": 127,
                "formatted_address": "123 Main St, Anytown, ST 12345",
                "types": ["restaurant", "food", "establishment"],
                "reviews": [
                    {
                        "author_name": "Alice Johnson",
                        "author_url": "https://www.google.com/maps/contrib/123",
                        "language": "en",
                        "profile_photo_url": "https://lh3.googleusercontent.com/a-/photo.jpg",
                        "rating": 5,
                        "relative_time_description": "2 weeks ago",
                        "text": "Amazing pasta and excellent service! The tiramisu was to die for.",
                        "time": 1640995200
                    },
                    {
                        "author_name": "Bob Smith",
                        "author_url": "https://www.google.com/maps/contrib/456",
                        "language": "en",
                        "profile_photo_url": "https://lh3.googleusercontent.com/a-/photo2.jpg",
                        "rating": 2,
                        "relative_time_description": "1 week ago",
                        "text": "Food was cold when it arrived. Service was slow and inattentive.",
                        "time": 1641081600
                    },
                    {
                        "author_name": "Carol Davis",
                        "author_url": "https://www.google.com/maps/contrib/789",
                        "language": "en",
                        "rating": 4,
                        "relative_time_description": "3 days ago",
                        "text": "Good food, nice atmosphere. A bit pricey but worth it.",
                        "time": 1641340800
                    }
                ]
            }
        }

        # Mock the HTTP client's get method
        with patch.object(self.client, 'get', return_value=mock_api_response):
            with patch.object(self.client, '_check_review_exists', return_value=False):
                # Act
                result = await self.client.import_reviews(self.place_id, self.business_id)

                # Assert
                assert isinstance(result, ImportResult)
                assert result.total_found == 3
                assert result.imported_count == 3
                assert result.duplicate_count == 0
                assert result.error_count == 0
                assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_import_with_api_rate_limiting(self):
        """Test import handling of API rate limiting."""
        # Arrange
        rate_limit_response = {
            "status": "OVER_QUERY_LIMIT",
            "error_message": "You have exceeded your daily request quota for this API."
        }

        with patch.object(self.client, 'get', return_value=rate_limit_response):
            # Act & Assert
            with pytest.raises(Exception, match="OVER_QUERY_LIMIT"):
                await self.client.import_reviews(self.place_id, self.business_id)

    @pytest.mark.asyncio
    async def test_import_with_invalid_place_id(self):
        """Test import with invalid place ID."""
        # Arrange
        invalid_response = {
            "status": "INVALID_REQUEST",
            "error_message": "Invalid place_id"
        }

        with patch.object(self.client, 'get', return_value=invalid_response):
            # Act & Assert
            with pytest.raises(Exception, match="INVALID_REQUEST"):
                await self.client.import_reviews("invalid-place-id", self.business_id)

    @pytest.mark.asyncio
    async def test_import_with_network_timeout(self):
        """Test import handling of network timeouts."""
        # Arrange
        with patch.object(self.client, 'get', side_effect=Exception("Request timeout")):
            # Act & Assert
            with pytest.raises(Exception, match="Request timeout"):
                await self.client.import_reviews(self.place_id, self.business_id)

    @pytest.mark.asyncio
    async def test_import_with_malformed_review_data(self):
        """Test import handling of malformed review data from API."""
        # Arrange
        malformed_response = {
            "status": "OK",
            "result": {
                "name": "Test Restaurant",
                "reviews": [
                    {
                        "author_name": "Valid User",
                        "rating": 5,
                        "text": "Great food!",
                        "time": 1640995200,
                        "language": "en"
                    },
                    {
                        # Malformed review - missing required fields
                        "author_name": "Invalid User",
                        "text": "Some text",
                        # Missing rating and time
                    },
                    {
                        # Another malformed review - invalid data types
                        "author_name": "Another User",
                        "rating": "not-a-number",  # Should be int
                        "time": "not-a-timestamp",  # Should be int
                        "text": "Some review text"
                    }
                ]
            }
        }

        with patch.object(self.client, 'get', return_value=malformed_response):
            with patch.object(self.client, '_check_review_exists', return_value=False):
                # Act
                result = await self.client.import_reviews(self.place_id, self.business_id)

                # Assert
                assert result.total_found == 3
                assert result.imported_count == 1  # Only the valid review
                assert result.duplicate_count == 0
                assert result.error_count == 2  # Two malformed reviews
                assert len(result.errors) == 2

    @pytest.mark.asyncio
    async def test_import_with_duplicate_detection(self):
        """Test import with realistic duplicate detection scenario."""
        # Arrange
        api_response = {
            "status": "OK",
            "result": {
                "name": "Test Restaurant",
                "reviews": [
                    {
                        "author_name": "John Doe",
                        "rating": 5,
                        "text": "Excellent food!",
                        "time": 1640995200,
                        "language": "en"
                    },
                    {
                        "author_name": "Jane Smith",
                        "rating": 4,
                        "text": "Good service.",
                        "time": 1641081600,
                        "language": "en"
                    },
                    {
                        "author_name": "Bob Wilson",
                        "rating": 3,
                        "text": "Average experience.",
                        "time": 1641168000,
                        "language": "en"
                    }
                ]
            }
        }

        # Mock duplicate detection - first and third reviews are duplicates
        def mock_check_exists(business_id, external_id):
            # Generate external IDs for comparison
            review1_id = self.client._generate_external_id(api_response["result"]["reviews"][0])
            review3_id = self.client._generate_external_id(api_response["result"]["reviews"][2])
            return external_id in [review1_id, review3_id]

        with patch.object(self.client, 'get', return_value=api_response):
            with patch.object(self.client, '_check_review_exists', side_effect=mock_check_exists):
                # Act
                result = await self.client.import_reviews(self.place_id, self.business_id)

                # Assert
                assert result.total_found == 3
                assert result.imported_count == 1  # Only middle review is new
                assert result.duplicate_count == 2  # First and third are duplicates
                assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_import_with_retry_logic_success(self):
        """Test retry logic with transient failures followed by success."""
        # Arrange
        success_response = {
            "status": "OK",
            "result": {
                "name": "Test Restaurant",
                "reviews": [
                    {
                        "author_name": "Test User",
                        "rating": 4,
                        "text": "Good food",
                        "time": 1640995200,
                        "language": "en"
                    }
                ]
            }
        }

        # Mock sequence: timeout, server error, then success
        call_count = 0
        def mock_get_with_failures(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Connection timeout")
            elif call_count == 2:
                raise Exception("Server error 500")
            else:
                return success_response

        with patch.object(self.client, 'get', side_effect=mock_get_with_failures):
            with patch.object(self.client, '_check_review_exists', return_value=False):
                with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                    # Act
                    result = await self.client.import_reviews_with_retry(
                        self.place_id, self.business_id, max_retries=3
                    )

                    # Assert
                    assert result.imported_count == 1
                    assert call_count == 3  # Two failures, then success

    @pytest.mark.asyncio
    async def test_import_with_retry_logic_all_fail(self):
        """Test retry logic when all attempts fail."""
        # Arrange
        with patch.object(self.client, 'get', side_effect=Exception("Persistent API error")):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                # Act & Assert
                with pytest.raises(Exception, match="Persistent API error"):
                    await self.client.import_reviews_with_retry(
                        self.place_id, self.business_id, max_retries=2
                    )

    @pytest.mark.asyncio
    async def test_batch_import_multiple_businesses(self):
        """Test batch import for multiple businesses with mixed results."""
        # Arrange
        place_business_pairs = [
            ("place-1", "business-1"),
            ("place-2", "business-2"),
            ("place-3", "business-3"),
        ]

        # Mock responses for different businesses
        def mock_import_with_retry(place_id, business_id, max_reviews):
            if business_id == "business-1":
                return ImportResult(2, 2, 0, 0, [])
            elif business_id == "business-2":
                return ImportResult(1, 0, 1, 0, [])  # All duplicates
            else:  # business-3
                raise Exception("API error for business-3")

        with patch.object(self.client, 'import_reviews_with_retry', side_effect=mock_import_with_retry):
            # Act
            results = await self.client.batch_import_reviews(place_business_pairs)

            # Assert
            assert len(results) == 3
            
            # Business 1: successful import
            assert results["business-1"].imported_count == 2
            assert results["business-1"].error_count == 0
            
            # Business 2: all duplicates
            assert results["business-2"].imported_count == 0
            assert results["business-2"].duplicate_count == 1
            
            # Business 3: error
            assert results["business-3"].error_count == 1
            assert "API error for business-3" in results["business-3"].errors[0]

    @pytest.mark.asyncio
    async def test_place_validation_workflow(self):
        """Test place ID validation workflow."""
        # Arrange
        valid_response = {
            "status": "OK",
            "result": {
                "place_id": self.place_id,
                "name": "Test Restaurant"
            }
        }

        invalid_response = {
            "status": "NOT_FOUND"
        }

        # Test valid place ID
        with patch.object(self.client, 'get', return_value=valid_response):
            result = await self.client.validate_place_id(self.place_id)
            assert result is True

        # Test invalid place ID
        with patch.object(self.client, 'get', return_value=invalid_response):
            result = await self.client.validate_place_id("invalid-place-id")
            assert result is False

    @pytest.mark.asyncio
    async def test_search_places_workflow(self):
        """Test place search workflow."""
        # Arrange
        search_response = {
            "status": "OK",
            "results": [
                {
                    "place_id": "place-1",
                    "name": "Mario's Pizza",
                    "rating": 4.2,
                    "formatted_address": "123 Main St",
                    "types": ["restaurant", "food"]
                },
                {
                    "place_id": "place-2",
                    "name": "Luigi's Pasta",
                    "rating": 4.5,
                    "formatted_address": "456 Oak Ave",
                    "types": ["restaurant", "food"]
                }
            ]
        }

        with patch.object(self.client, 'get', return_value=search_response):
            # Act
            results = await self.client.search_places(
                "Italian restaurant",
                location="40.7128,-74.0060",
                radius=1000
            )

            # Assert
            assert len(results) == 2
            assert results[0]["name"] == "Mario's Pizza"
            assert results[1]["name"] == "Luigi's Pasta"

    @pytest.mark.asyncio
    async def test_get_place_photos_workflow(self):
        """Test place photos retrieval workflow."""
        # Arrange
        photos_response = {
            "status": "OK",
            "result": {
                "photos": [
                    {
                        "height": 1080,
                        "width": 1920,
                        "photo_reference": "CmRaAAAA1234567890abcdef",
                        "html_attributions": ["<a href=\"https://maps.google.com/\">Google</a>"]
                    },
                    {
                        "height": 720,
                        "width": 1280,
                        "photo_reference": "CmRaAAAAabcdef1234567890",
                        "html_attributions": ["<a href=\"https://maps.google.com/\">Google</a>"]
                    }
                ]
            }
        }

        with patch.object(self.client, 'get', return_value=photos_response):
            # Act
            photo_urls = await self.client.get_place_photos(self.place_id)

            # Assert
            assert len(photo_urls) == 2
            assert all("photoreference=" in url for url in photo_urls)
            assert all("maxwidth=400" in url for url in photo_urls)
            assert all(self.api_key in url for url in photo_urls)

    @pytest.mark.asyncio
    async def test_concurrent_import_operations(self):
        """Test handling of concurrent import operations."""
        import asyncio
        
        # Arrange
        success_response = {
            "status": "OK",
            "result": {
                "name": "Test Restaurant",
                "reviews": [
                    {
                        "author_name": "Test User",
                        "rating": 4,
                        "text": "Good food",
                        "time": 1640995200,
                        "language": "en"
                    }
                ]
            }
        }

        with patch.object(self.client, 'get', return_value=success_response):
            with patch.object(self.client, '_check_review_exists', return_value=False):
                # Act - Run multiple imports concurrently
                tasks = [
                    self.client.import_reviews(f"place-{i}", f"business-{i}")
                    for i in range(5)
                ]
                results = await asyncio.gather(*tasks)

                # Assert
                assert len(results) == 5
                assert all(result.imported_count == 1 for result in results)
                assert all(result.error_count == 0 for result in results)

    @pytest.mark.asyncio
    async def test_large_review_batch_handling(self):
        """Test handling of large review batches (up to 500 reviews)."""
        # Arrange
        large_review_set = [
            {
                "author_name": f"User {i}",
                "rating": (i % 5) + 1,  # Ratings 1-5
                "text": f"Review text {i}",
                "time": 1640995200 + i,
                "language": "en"
            }
            for i in range(500)  # Maximum allowed
        ]

        large_response = {
            "status": "OK",
            "result": {
                "name": "Popular Restaurant",
                "reviews": large_review_set
            }
        }

        with patch.object(self.client, 'get', return_value=large_response):
            with patch.object(self.client, '_check_review_exists', return_value=False):
                # Act
                result = await self.client.import_reviews(self.place_id, self.business_id)

                # Assert
                assert result.total_found == 500
                assert result.imported_count == 500
                assert result.duplicate_count == 0
                assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_mixed_language_reviews_handling(self):
        """Test handling of reviews in multiple languages."""
        # Arrange
        multilingual_response = {
            "status": "OK",
            "result": {
                "name": "International Restaurant",
                "reviews": [
                    {
                        "author_name": "John Smith",
                        "rating": 5,
                        "text": "Excellent food and service!",
                        "time": 1640995200,
                        "language": "en"
                    },
                    {
                        "author_name": "Hans Mueller",
                        "rating": 4,
                        "text": "Sehr gutes Essen und freundlicher Service.",
                        "time": 1641081600,
                        "language": "de"
                    },
                    {
                        "author_name": "Mehmet Özkan",
                        "rating": 5,
                        "text": "Harika yemek ve mükemmel hizmet!",
                        "time": 1641168000,
                        "language": "tr"
                    },
                    {
                        "author_name": "Marie Dubois",
                        "rating": 3,
                        "text": "Nourriture correcte, service moyen.",
                        "time": 1641254400,
                        "language": "fr"
                    }
                ]
            }
        }

        with patch.object(self.client, 'get', return_value=multilingual_response):
            with patch.object(self.client, '_check_review_exists', return_value=False):
                # Act
                result = await self.client.import_reviews(self.place_id, self.business_id)

                # Assert
                assert result.total_found == 4
                assert result.imported_count == 4
                assert result.error_count == 0
                
                # All reviews should be processed regardless of language