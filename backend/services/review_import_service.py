"""
Review import service for Google Places integration.

This service handles the complete review import workflow including
duplicate detection, data transformation, database storage, and
import status tracking with history.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta, timezone
import asyncio

from backend.external.google_places import GooglePlacesClient, GoogleReview, ImportResult
from backend.db.repositories.review import ReviewRepository
from backend.db.repositories.business import BusinessRepository
from backend.db.schemas import ReviewCreate
from backend.ai.language_detector import LanguageDetector

logger = logging.getLogger(__name__)


class ImportStatusTracker:
    """Tracks import status and progress for real-time updates."""
    
    def __init__(self):
        self._status_cache: Dict[str, Dict[str, Any]] = {}
        self._progress_callbacks: Dict[str, List[callable]] = {}
    
    def start_import(self, business_id: str, total_expected: int = 0) -> None:
        """Start tracking an import operation."""
        self._status_cache[business_id] = {
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc),
            "total_expected": total_expected,
            "processed": 0,
            "imported": 0,
            "duplicates": 0,
            "errors": [],
            "current_step": "initializing"
        }
    
    def update_progress(self, business_id: str, **updates) -> None:
        """Update import progress."""
        if business_id in self._status_cache:
            self._status_cache[business_id].update(updates)
            # Notify callbacks
            for callback in self._progress_callbacks.get(business_id, []):
                try:
                    callback(self._status_cache[business_id])
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
    
    def complete_import(self, business_id: str, result: ImportResult) -> None:
        """Mark import as complete."""
        if business_id in self._status_cache:
            self._status_cache[business_id].update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "imported": result.imported_count,
                "duplicates": result.duplicate_count,
                "errors": result.errors,
                "current_step": "completed"
            })
    
    def fail_import(self, business_id: str, error: str) -> None:
        """Mark import as failed."""
        if business_id in self._status_cache:
            self._status_cache[business_id].update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
                "current_step": "failed",
                "errors": self._status_cache[business_id].get("errors", []) + [error]
            })
    
    def get_status(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get current import status."""
        return self._status_cache.get(business_id)
    
    def register_progress_callback(self, business_id: str, callback: callable) -> None:
        """Register a callback for progress updates."""
        if business_id not in self._progress_callbacks:
            self._progress_callbacks[business_id] = []
        self._progress_callbacks[business_id].append(callback)
    
    def cleanup_status(self, business_id: str) -> None:
        """Clean up status tracking after completion."""
        self._status_cache.pop(business_id, None)
        self._progress_callbacks.pop(business_id, None)


class ReviewImportService:
    """Service for importing reviews from Google Places API with status tracking."""

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
        self._status_tracker = ImportStatusTracker()

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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
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

    async def get_import_status(self, business_id: UUID) -> Dict[str, Any]:
        """Get comprehensive import status for a business.

        Args:
            business_id: Business UUID

        Returns:
            Dictionary with import status information
        """
        try:
            business_id_str = str(business_id)
            
            # Check if import is currently in progress
            current_status = self._status_tracker.get_status(business_id_str)
            if current_status:
                return {
                    "business_id": business_id_str,
                    "status": current_status["status"],
                    "current_step": current_status.get("current_step"),
                    "progress": {
                        "processed": current_status.get("processed", 0),
                        "imported": current_status.get("imported", 0),
                        "duplicates": current_status.get("duplicates", 0),
                        "total_expected": current_status.get("total_expected", 0)
                    },
                    "started_at": current_status.get("started_at"),
                    "errors": current_status.get("errors", []),
                    "is_active": True
                }
            
            # Get historical import data
            import_history = await self._get_import_history(business_id)
            last_import = import_history[0] if import_history else None
            
            # Get business statistics
            business = await self._business_repo.get(business_id)
            if not business:
                raise ValueError(f"Business {business_id} not found")
            
            # Calculate next scheduled import (daily at midnight)
            next_import = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            if next_import <= datetime.now(timezone.utc):
                next_import += timedelta(days=1)
            
            return {
                "business_id": business_id_str,
                "status": "idle",
                "last_import": last_import["timestamp"] if last_import else None,
                "last_import_count": last_import["imported_count"] if last_import else 0,
                "total_imported": business.total_reviews,
                "next_scheduled_import": next_import.isoformat(),
                "import_errors": last_import["errors"] if last_import and last_import["errors"] else [],
                "import_history": import_history[:5],  # Last 5 imports
                "is_active": False
            }
            
        except Exception as e:
            logger.error(f"Failed to get import status for business {business_id}: {e}")
            return {
                "business_id": str(business_id),
                "status": "error",
                "error": str(e),
                "is_active": False
            }

    async def get_import_history(self, business_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Get import history for a business.

        Args:
            business_id: Business UUID
            limit: Maximum number of history entries to return

        Returns:
            List of import history entries
        """
        try:
            return await self._get_import_history(business_id, limit)
        except Exception as e:
            logger.error(f"Failed to get import history for business {business_id}: {e}")
            return []

    async def start_manual_import(
        self, 
        business_id: UUID, 
        max_reviews: int = 500,
        progress_callback: Optional[callable] = None
    ) -> ImportResult:
        """Start manual import with real-time progress tracking.

        Args:
            business_id: Business UUID
            max_reviews: Maximum number of reviews to import
            progress_callback: Optional callback for progress updates

        Returns:
            ImportResult with import statistics
        """
        business_id_str = str(business_id)
        
        try:
            # Check if import is already in progress
            current_status = self._status_tracker.get_status(business_id_str)
            if current_status and current_status["status"] == "in_progress":
                raise ValueError("Import already in progress for this business")
            
            # Register progress callback if provided
            if progress_callback:
                self._status_tracker.register_progress_callback(business_id_str, progress_callback)
            
            # Start tracking
            self._status_tracker.start_import(business_id_str, max_reviews)
            
            # Update progress
            self._status_tracker.update_progress(
                business_id_str,
                current_step="validating_business"
            )
            
            # Validate business exists
            business = await self._business_repo.get(business_id)
            if not business:
                self._status_tracker.fail_import(business_id_str, f"Business {business_id} not found")
                raise ValueError(f"Business {business_id} not found")

            # Update progress
            self._status_tracker.update_progress(
                business_id_str,
                current_step="fetching_reviews"
            )

            # Import reviews from Google Places
            import_result = await self._google_client.import_reviews(
                business.google_place_id, business_id_str, max_reviews
            )

            # Update progress
            self._status_tracker.update_progress(
                business_id_str,
                current_step="processing_reviews",
                total_expected=len(import_result.reviews) if import_result.reviews else 0
            )

            if import_result.imported_count == 0 or not import_result.reviews:
                logger.info(f"No new reviews to import for business {business_id}")
                self._status_tracker.complete_import(business_id_str, import_result)
                await self._record_import_history(business_id, import_result)
                return import_result

            # Process reviews with progress tracking
            result = await self._process_reviews_with_progress(
                business_id, import_result.reviews, business_id_str
            )
            
            # Update business statistics
            await self._update_business_stats(business_id)
            
            # Record import history
            await self._record_import_history(business_id, result)
            
            # Complete tracking
            self._status_tracker.complete_import(business_id_str, result)
            
            logger.info(f"Manual import completed for business {business_id}: {result.imported_count} reviews imported")
            
            return result

        except Exception as e:
            self._status_tracker.fail_import(business_id_str, str(e))
            logger.error(f"Manual import failed for business {business_id}: {e}")
            raise
        finally:
            # Cleanup after a delay to allow final status check
            asyncio.create_task(self._cleanup_status_after_delay(business_id_str, 30))

    async def get_real_time_status(self, business_id: UUID) -> Dict[str, Any]:
        """Get real-time import status for active imports.

        Args:
            business_id: Business UUID

        Returns:
            Real-time status information
        """
        business_id_str = str(business_id)
        status = self._status_tracker.get_status(business_id_str)
        
        if not status:
            return {"is_active": False, "status": "idle"}
        
        # Calculate progress percentage
        progress_percent = 0
        if status.get("total_expected", 0) > 0:
            progress_percent = (status.get("processed", 0) / status["total_expected"]) * 100
        
        return {
            "is_active": True,
            "status": status["status"],
            "current_step": status.get("current_step", "unknown"),
            "progress_percent": min(100, max(0, progress_percent)),
            "processed": status.get("processed", 0),
            "imported": status.get("imported", 0),
            "duplicates": status.get("duplicates", 0),
            "total_expected": status.get("total_expected", 0),
            "started_at": status.get("started_at"),
            "errors": status.get("errors", []),
            "estimated_completion": self._estimate_completion_time(status)
        }

    async def _process_reviews_with_progress(
        self, 
        business_id: UUID, 
        google_reviews: List[GoogleReview],
        business_id_str: str
    ) -> ImportResult:
        """Process reviews with progress tracking."""
        review_creates = []
        duplicate_count = 0
        error_count = 0
        errors = []
        processed_count = 0

        for google_review in google_reviews:
            try:
                processed_count += 1
                
                # Update progress
                self._status_tracker.update_progress(
                    business_id_str,
                    processed=processed_count,
                    current_step=f"processing_review_{processed_count}"
                )

                # Check for duplicates
                existing_review = await self._review_repo.get_by_external_id(
                    business_id, google_review.external_id, "google"
                )

                if existing_review:
                    duplicate_count += 1
                    self._status_tracker.update_progress(business_id_str, duplicates=duplicate_count)
                    continue

                # Detect language
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
                error_msg = f"Failed to process review {google_review.external_id}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # Bulk import reviews
        imported_count = 0
        if review_creates:
            try:
                self._status_tracker.update_progress(
                    business_id_str,
                    current_step="saving_to_database"
                )
                
                created_reviews = await self._review_repo.bulk_import_reviews(review_creates)
                imported_count = len(created_reviews)
                
                self._status_tracker.update_progress(business_id_str, imported=imported_count)
                
            except Exception as e:
                error_count += len(review_creates)
                error_msg = f"Failed to save reviews to database: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        return ImportResult(
            total_found=len(google_reviews),
            imported_count=imported_count,
            duplicate_count=duplicate_count,
            error_count=error_count,
            errors=errors,
            reviews=[]
        )

    async def _get_import_history(self, business_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Get import history from database."""
        # This would typically query an import_history table
        # For now, we'll simulate with review creation timestamps
        try:
            # Get recent review batches as proxy for import history
            reviews = await self._review_repo.get_recent_imports(business_id, limit)
            
            history = []
            current_date = None
            current_batch = {"count": 0, "reviews": []}
            
            for review in reviews:
                review_date = review.created_at.date()
                
                if current_date != review_date:
                    if current_batch["count"] > 0:
                        history.append({
                            "timestamp": current_batch["reviews"][-1].created_at.isoformat(),
                            "imported_count": current_batch["count"],
                            "source": "google",
                            "errors": [],
                            "status": "completed"
                        })
                    
                    current_date = review_date
                    current_batch = {"count": 1, "reviews": [review]}
                else:
                    current_batch["count"] += 1
                    current_batch["reviews"].append(review)
            
            # Add the last batch
            if current_batch["count"] > 0:
                history.append({
                    "timestamp": current_batch["reviews"][-1].created_at.isoformat(),
                    "imported_count": current_batch["count"],
                    "source": "google",
                    "errors": [],
                    "status": "completed"
                })
            
            return history[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get import history: {e}")
            return []

    async def _record_import_history(self, business_id: UUID, result: ImportResult) -> None:
        """Record import operation in history."""
        # This would typically insert into an import_history table
        # For now, we'll log the operation
        logger.info(
            f"Import completed for business {business_id}: "
            f"imported={result.imported_count}, duplicates={result.duplicate_count}, "
            f"errors={result.error_count}"
        )

    def _estimate_completion_time(self, status: Dict[str, Any]) -> Optional[str]:
        """Estimate completion time based on current progress."""
        if status.get("status") != "in_progress":
            return None
        
        started_at = status.get("started_at")
        processed = status.get("processed", 0)
        total_expected = status.get("total_expected", 0)
        
        if not started_at or processed == 0 or total_expected == 0:
            return None
        
        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        rate = processed / elapsed  # reviews per second
        
        remaining = total_expected - processed
        if remaining <= 0:
            return "completing"
        
        estimated_seconds = remaining / rate
        estimated_completion = datetime.now(timezone.utc) + timedelta(seconds=estimated_seconds)
        
        return estimated_completion.isoformat()

    async def _cleanup_status_after_delay(self, business_id_str: str, delay_seconds: int) -> None:
        """Clean up status tracking after a delay."""
        await asyncio.sleep(delay_seconds)
        self._status_tracker.cleanup_status(business_id_str)

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