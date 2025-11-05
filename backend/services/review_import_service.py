"""
Review import service for Google Places integration.

This service handles the complete review import workflow including
duplicate detection, data transformation, and database storage.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from backend.external.google_places import GooglePlacesClient, GoogleReview, ImportResult
from backend.db.repositories.review import ReviewRepository
from backend.db.repositories.business import BusinessRepository
from backend.db.schemas import ReviewCreate
from backend.ai.language_detector import LanguageDetector

logger = logging.getLogger(__name__)


class ReviewImportService:
    """Service for importing reviews from Google Places API."""

    def __init__(
        self,
        google_places_client: GooglePlacesClient,
        review_repository: ReviewRepository,
        business_repository: BusinessRepository,
        language_detector: LanguageDetector,
    ):
        """Initialize review import service.

        Args:
            google_places_client: Google Places API client
            review_repository: Review repository for database operations
            business_repository: Business repository for validation
            language_detector: Language detection service
        """
        self._google_client = google_places_client
        self._review_repo = review_repository
        self._business_repo = business_repository
        self._language_detector = language_detector

    async def import_reviews_for_business(
        self, business_id: UUID, max_reviews: int = 500
    ) -> ImportResult:
        """Import reviews for a specific business.

        Args:
            business_id: Business UUID
            max_reviews: Maximum number of reviews to import

        Returns:
            ImportResult with import statistics

        Raises:
            ValueError: If business not found
            Exception: If import fails
        """
        try:
            logger.info(f"Starting review import for business {business_id}")

            # Validate business exists
            business = await self._business_repo.get(business_id)
            if not business:
                raise ValueError(f"Business {business_id} not found")

            # Import reviews from Google Places
            import_result = await self._google_client.import_reviews(
                business.google_place_id, str(business_id), max_reviews
            )

            if import_result.imported_count == 0 or not import_result.reviews:
                logger.info(f"No new reviews to import for business {business_id}")
                return import_result

            # Convert Google reviews to database format
            review_creates = []
            duplicate_count = 0
            error_count = 0
            errors = []

            for google_review in import_result.reviews:
                try:
                    # Check for duplicates in database (additional check)
                    existing_review = await self._review_repo.get_by_external_id(
                        business_id, google_review.external_id, "google"
                    )

                    if existing_review:
                        duplicate_count += 1
                        logger.debug(f"Skipping duplicate review: {google_review.external_id}")
                        continue

                    # Detect language if not provided or incorrect
                    detected_language = self._language_detector.detect_language(google_review.text)

                    # Create review schema
                    review_create = ReviewCreate(
                        business_id=business_id,
                        author_name=google_review.author_name,
                        rating=google_review.rating,
                        text=google_review.text,
                        language=detected_language,
                        published_at=google_review.time,
                        source="google",
                        external_id=google_review.external_id,
                    )

                    review_creates.append(review_create)

                except Exception as e:
                    error_count += 1
                    error_msg = f"Failed to process Google review {google_review.external_id}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

            # Bulk import reviews to database
            if review_creates:
                try:
                    created_reviews = await self._review_repo.bulk_import_reviews(review_creates)
                    imported_count = len(created_reviews)
                    
                    # Update business statistics
                    await self._update_business_stats(business_id)
                    
                    logger.info(
                        f"Successfully imported {imported_count} reviews for business {business_id}"
                    )
                except Exception as e:
                    error_count += len(review_creates)
                    error_msg = f"Failed to save reviews to database: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    imported_count = 0
            else:
                imported_count = 0

            # Return updated import result
            return ImportResult(
                total_found=import_result.total_found,
                imported_count=imported_count,
                duplicate_count=duplicate_count + import_result.duplicate_count,
                error_count=error_count + import_result.error_count,
                errors=errors + import_result.errors,
                reviews=[]  # Don't return the actual reviews in the result
            )

        except Exception as e:
            logger.error(f"Failed to import reviews for business {business_id}: {e}")
            raise

    async def import_reviews_for_multiple_businesses(
        self, business_ids: List[UUID], max_reviews: int = 500
    ) -> Dict[str, ImportResult]:
        """Import reviews for multiple businesses.

        Args:
            business_ids: List of business UUIDs
            max_reviews: Maximum reviews per business

        Returns:
            Dictionary mapping business_id to ImportResult
        """
        results = {}

        for business_id in business_ids:
            try:
                result = await self.import_reviews_for_business(business_id, max_reviews)
                results[str(business_id)] = result
            except Exception as e:
                logger.error(f"Failed to import reviews for business {business_id}: {e}")
                results[str(business_id)] = ImportResult(
                    total_found=0,
                    imported_count=0,
                    duplicate_count=0,
                    error_count=1,
                    errors=[str(e)],
                    reviews=[]
                )

        return results

    async def import_reviews_with_retry(
        self, business_id: UUID, max_reviews: int = 500, max_retries: int = 3
    ) -> ImportResult:
        """Import reviews with automatic retry logic.

        Args:
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
                return await self.import_reviews_for_business(business_id, max_reviews)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Import attempt {attempt + 1} failed for business {business_id}, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {max_retries + 1} import attempts failed for business {business_id}"
                    )

        raise last_exception

    async def validate_business_place_id(self, business_id: UUID) -> bool:
        """Validate that a business has a valid Google Place ID.

        Args:
            business_id: Business UUID

        Returns:
            True if place ID is valid, False otherwise
        """
        try:
            business = await self._business_repo.get(business_id)
            if not business or not business.google_place_id:
                return False

            return await self._google_client.validate_place_id(business.google_place_id)
        except Exception as e:
            logger.error(f"Failed to validate place ID for business {business_id}: {e}")
            return False

    async def get_import_statistics(self, business_id: UUID) -> Dict[str, Any]:
        """Get import statistics for a business.

        Args:
            business_id: Business UUID

        Returns:
            Dictionary with import statistics
        """
        try:
            # Get review statistics from repository
            stats = await self._review_repo.get_review_statistics(business_id)

            # Get business info
            business = await self._business_repo.get(business_id)

            return {
                "business_id": str(business_id),
                "business_name": business.name if business else "Unknown",
                "google_place_id": business.google_place_id if business else None,
                "total_reviews": stats["total_reviews"],
                "avg_rating": stats["avg_rating"],
                "recent_reviews_30d": stats["recent_reviews_30d"],
                "language_distribution": stats["language_distribution"],
                "first_review": stats["first_review"],
                "latest_review": stats["latest_review"],
            }
        except Exception as e:
            logger.error(f"Failed to get import statistics for business {business_id}: {e}")
            return {
                "business_id": str(business_id),
                "error": str(e),
            }

    async def schedule_daily_import(self) -> Dict[str, Any]:
        """Schedule daily import for all businesses.

        Returns:
            Dictionary with import results for all businesses
        """
        try:
            logger.info("Starting scheduled daily review import")

            # Get all businesses that need analysis
            businesses = await self._business_repo.get_businesses_needing_analysis(limit=1000)

            if not businesses:
                logger.info("No businesses found for daily import")
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "businesses_processed": 0,
                    "total_imported": 0,
                    "total_errors": 0,
                    "results": [],
                }

            # Import reviews for all businesses
            business_ids = [business.id for business in businesses]
            results = await self.import_reviews_for_multiple_businesses(business_ids)

            # Calculate summary statistics
            total_imported = sum(result.imported_count for result in results.values())
            total_errors = sum(result.error_count for result in results.values())

            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "businesses_processed": len(businesses),
                "total_imported": total_imported,
                "total_duplicates": sum(result.duplicate_count for result in results.values()),
                "total_errors": total_errors,
                "results": [
                    {
                        "business_id": business_id,
                        "business_name": next(
                            (b.name for b in businesses if str(b.id) == business_id),
                            "Unknown"
                        ),
                        "imported_count": result.imported_count,
                        "duplicate_count": result.duplicate_count,
                        "error_count": result.error_count,
                        "errors": result.errors,
                    }
                    for business_id, result in results.items()
                ],
            }

            logger.info(
                f"Daily import completed: {total_imported} reviews imported, "
                f"{total_errors} errors across {len(businesses)} businesses"
            )

            return summary

        except Exception as e:
            logger.error(f"Failed to execute daily import: {e}")
            raise

    async def _update_business_stats(self, business_id: UUID) -> None:
        """Update business rating statistics after import.

        Args:
            business_id: Business UUID
        """
        try:
            # Calculate new statistics
            avg_rating, total_reviews = await self._business_repo.calculate_rating_stats(
                business_id
            )

            # Update business record
            await self._business_repo.update_rating_stats(
                business_id, avg_rating, total_reviews
            )

            logger.debug(
                f"Updated business {business_id} stats: "
                f"avg_rating={avg_rating}, total_reviews={total_reviews}"
            )
        except Exception as e:
            logger.error(f"Failed to update business stats for {business_id}: {e}")
            # Don't raise - this is not critical for import success