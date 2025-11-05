"""
Google Places API client for review import functionality.

This module provides integration with Google Places API for importing
customer reviews with duplicate detection and error handling.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from backend.external.base_client import BaseHTTPClient

logger = logging.getLogger(__name__)


@dataclass
class GoogleReview:
    """Google Places review data structure."""

    author_name: str
    rating: int
    text: str
    time: datetime
    language: str
    profile_photo_url: Optional[str] = None
    relative_time_description: Optional[str] = None
    external_id: Optional[str] = None


@dataclass
class ImportResult:
    """Result of review import operation."""

    total_found: int
    imported_count: int
    duplicate_count: int
    error_count: int
    errors: List[str]
    reviews: List['GoogleReview'] = None  # Actual imported reviews


class GooglePlacesClient(BaseHTTPClient):
    """Google Places API client for review import."""

    def __init__(self, api_key: str):
        """Initialize Google Places client.

        Args:
            api_key: Google Places API key
        """
        super().__init__(
            base_url="https://maps.googleapis.com/maps/api/place",
            api_key=api_key,
            timeout=30,
            max_retries=3,
            retry_delay=1.0,
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Google Places API requests.

        Returns:
            Dictionary of default headers
        """
        return {
            "Content-Type": "application/json",
            "User-Agent": "LocalBusinessBot/1.0",
        }

    async def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """Get place details from Google Places API.

        Args:
            place_id: Google Place ID

        Returns:
            Place details dictionary

        Raises:
            Exception: If API request fails
        """
        try:
            params = {
                "place_id": place_id,
                "fields": "name,rating,user_ratings_total,formatted_address,types,reviews",
                "key": self._api_key,
            }

            response = await self.get("/details/json", params=params)

            if response.get("status") != "OK":
                raise Exception(f"Google Places API error: {response.get('status')}")

            return response.get("result", {})

        except Exception as e:
            logger.error(f"Failed to get place details for {place_id}: {e}")
            raise

    async def import_reviews(
        self, place_id: str, business_id: str, max_reviews: int = 500
    ) -> ImportResult:
        """Import reviews from Google Places API with duplicate detection.

        Args:
            place_id: Google Place ID
            business_id: Business UUID for duplicate detection
            max_reviews: Maximum number of reviews to import

        Returns:
            ImportResult with import statistics

        Raises:
            Exception: If import fails
        """
        try:
            logger.info(f"Importing reviews for place {place_id}, business {business_id}")

            # Get place details with reviews
            place_details = await self.get_place_details(place_id)

            raw_reviews = place_details.get("reviews", [])

            if not raw_reviews:
                logger.info(f"No reviews found for place {place_id}")
                return ImportResult(
                    total_found=0,
                    imported_count=0,
                    duplicate_count=0,
                    error_count=0,
                    errors=[],
                    reviews=[]
                )

            # Convert to GoogleReview objects with duplicate detection
            reviews = []
            duplicate_count = 0
            error_count = 0
            errors = []

            for raw_review in raw_reviews[:max_reviews]:
                try:
                    review = self._parse_google_review(raw_review)
                    
                    # Check for duplicates using external_id (timestamp + author combination)
                    external_id = self._generate_external_id(raw_review)
                    
                    # In a real implementation, you'd check against the database here
                    # For now, we'll assume no duplicates in the same batch
                    review_exists = await self._check_review_exists(business_id, external_id)
                    
                    if review_exists:
                        duplicate_count += 1
                        logger.debug(f"Skipping duplicate review: {external_id}")
                        continue
                    
                    # Add external_id to review for database storage
                    review.external_id = external_id
                    reviews.append(review)
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"Failed to parse review: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    continue

            result = ImportResult(
                total_found=len(raw_reviews),
                imported_count=len(reviews),
                duplicate_count=duplicate_count,
                error_count=error_count,
                errors=errors,
                reviews=reviews
            )

            logger.info(
                f"Import completed for place {place_id}: "
                f"{result.imported_count} imported, "
                f"{result.duplicate_count} duplicates, "
                f"{result.error_count} errors"
            )
            
            return result

        except Exception as e:
            logger.error(f"Failed to import reviews for place {place_id}: {e}")
            raise

    def _parse_google_review(self, raw_review: Dict[str, Any]) -> GoogleReview:
        """Parse raw Google review data into GoogleReview object.

        Args:
            raw_review: Raw review data from Google Places API

        Returns:
            GoogleReview object

        Raises:
            ValueError: If required fields are missing
        """
        try:
            # Extract required fields
            author_name = raw_review.get("author_name", "Anonymous")
            rating = raw_review.get("rating")
            text = raw_review.get("text", "")
            time_timestamp = raw_review.get("time")

            if rating is None or time_timestamp is None:
                raise ValueError("Missing required fields: rating or time")

            # Convert timestamp to datetime
            review_time = datetime.fromtimestamp(time_timestamp)

            # Detect language (simplified - Google API may provide this)
            language = raw_review.get("language", "en")

            return GoogleReview(
                author_name=author_name,
                rating=int(rating),
                text=text,
                time=review_time,
                language=language,
                profile_photo_url=raw_review.get("profile_photo_url"),
                relative_time_description=raw_review.get("relative_time_description"),
            )

        except Exception as e:
            logger.error(f"Failed to parse Google review: {e}")
            raise ValueError(f"Invalid review data: {e}")

    async def validate_place_id(self, place_id: str) -> bool:
        """Validate that a Google Place ID exists and is accessible.

        Args:
            place_id: Google Place ID to validate

        Returns:
            True if place ID is valid, False otherwise
        """
        try:
            params = {
                "place_id": place_id,
                "fields": "place_id,name",
                "key": self._api_key,
            }

            response = await self.get("/details/json", params=params)

            return response.get("status") == "OK"

        except Exception as e:
            logger.error(f"Failed to validate place ID {place_id}: {e}")
            return False

    async def search_places(
        self, query: str, location: Optional[str] = None, radius: int = 5000
    ) -> List[Dict[str, Any]]:
        """Search for places using text query.

        Args:
            query: Search query (e.g., "Italian restaurant")
            location: Location bias (lat,lng format)
            radius: Search radius in meters

        Returns:
            List of place results
        """
        try:
            params = {"query": query, "key": self._api_key}

            if location:
                params["location"] = location
                params["radius"] = radius

            response = await self.get("/textsearch/json", params=params)

            if response.get("status") != "OK":
                logger.warning(
                    f"Places search returned status: {response.get('status')}"
                )
                return []

            return response.get("results", [])

        except Exception as e:
            logger.error(f"Failed to search places: {e}")
            return []

    async def get_place_photos(self, place_id: str) -> List[str]:
        """Get photo URLs for a place.

        Args:
            place_id: Google Place ID

        Returns:
            List of photo URLs
        """
        try:
            params = {"place_id": place_id, "fields": "photos", "key": self._api_key}

            response = await self.get("/details/json", params=params)

            if response.get("status") != "OK":
                return []

            photos = response.get("result", {}).get("photos", [])

            # Convert photo references to URLs
            photo_urls = []
            for photo in photos:
                photo_reference = photo.get("photo_reference")
                if photo_reference:
                    photo_url = (
                        f"https://maps.googleapis.com/maps/api/place/photo"
                        f"?maxwidth=400&photoreference={photo_reference}&key={self._api_key}"
                    )
                    photo_urls.append(photo_url)

            return photo_urls

        except Exception as e:
            logger.error(f"Failed to get photos for place {place_id}: {e}")
            return []

    def _generate_external_id(self, raw_review: Dict[str, Any]) -> str:
        """Generate unique external ID for review deduplication.

        Args:
            raw_review: Raw review data from Google Places API

        Returns:
            Unique external ID string
        """
        # Combine timestamp and author name for unique ID
        timestamp = raw_review.get("time", 0)
        author = raw_review.get("author_name", "anonymous")
        
        # Create a hash-like ID from timestamp and author
        import hashlib
        unique_string = f"{timestamp}_{author}_{raw_review.get('text', '')[:50]}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    async def _check_review_exists(self, business_id: str, external_id: str) -> bool:
        """Check if review already exists in database.

        Args:
            business_id: Business UUID
            external_id: External review ID

        Returns:
            True if review exists, False otherwise
        """
        # This is a placeholder - in real implementation, this would query the database
        # For now, we'll assume no duplicates exist
        # In the actual implementation, you'd inject a review repository here
        return False

    async def import_reviews_with_retry(
        self, place_id: str, business_id: str, max_reviews: int = 500, max_retries: int = 3
    ) -> ImportResult:
        """Import reviews with automatic retry logic.

        Args:
            place_id: Google Place ID
            business_id: Business UUID
            max_reviews: Maximum number of reviews to import
            max_retries: Maximum number of retry attempts

        Returns:
            ImportResult with import statistics

        Raises:
            Exception: If all retries fail
        """
        import asyncio
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self.import_reviews(place_id, business_id, max_reviews)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Import attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {max_retries + 1} import attempts failed")
        
        raise last_exception

    async def batch_import_reviews(
        self, place_business_pairs: List[tuple[str, str]], max_reviews: int = 500
    ) -> Dict[str, ImportResult]:
        """Import reviews for multiple businesses in batch.

        Args:
            place_business_pairs: List of (place_id, business_id) tuples
            max_reviews: Maximum reviews per business

        Returns:
            Dictionary mapping business_id to ImportResult
        """
        results = {}
        
        for place_id, business_id in place_business_pairs:
            try:
                result = await self.import_reviews_with_retry(
                    place_id, business_id, max_reviews
                )
                results[business_id] = result
            except Exception as e:
                logger.error(f"Failed to import reviews for business {business_id}: {e}")
                results[business_id] = ImportResult(
                    total_found=0,
                    imported_count=0,
                    duplicate_count=0,
                    error_count=1,
                    errors=[str(e)]
                )
        
        return results
