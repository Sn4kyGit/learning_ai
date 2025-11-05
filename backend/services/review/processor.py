"""
Review processing service for orchestrating the complete review analysis pipeline.

This service coordinates review import, language detection, AI classification,
and alert generation for comprehensive review processing.
"""

import logging
from typing import List
from uuid import UUID
from dataclasses import dataclass

from backend.ai.base import ReviewClassifierProtocol, ReviewText, CostTracker
from backend.ai.language_detector import LanguageDetector
from backend.db.repositories.review import ReviewRepository
from backend.db.repositories.classification import ClassificationRepository
from backend.services.notification.alert_service import AlertService

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of review processing operation."""

    processed_count: int
    success_count: int
    error_count: int
    critical_reviews_found: int
    processing_time_ms: int
    errors: List[str]


class ReviewProcessingService:
    """Orchestrates the complete review processing pipeline."""

    def __init__(
        self,
        classifier: ReviewClassifierProtocol,
        language_detector: LanguageDetector,
        review_repository: ReviewRepository,
        classification_repository: ClassificationRepository,
        cost_tracker: CostTracker,
        alert_service: AlertService,
    ):
        """Initialize review processing service.

        Args:
            classifier: AI review classification service
            language_detector: Language detection service
            review_repository: Review data repository
            classification_repository: Classification data repository
            cost_tracker: AI cost tracking service
            alert_service: Alert and notification service
        """
        self._classifier = classifier
        self._language_detector = language_detector
        self._review_repo = review_repository
        self._classification_repo = classification_repository
        self._cost_tracker = cost_tracker
        self._alert_service = alert_service

    async def process_new_reviews(self, business_id: UUID) -> ProcessingResult:  # noqa: C901
        """Process all new reviews for a business through the complete pipeline.

        Args:
            business_id: Business UUID to process reviews for

        Returns:
            ProcessingResult with processing statistics
        """
        import time

        start_time = time.time()

        errors = []
        critical_reviews_found = 0

        try:
            # 1. Get unprocessed reviews
            unprocessed_reviews = await self._review_repo.get_unclassified_reviews(
                business_id
            )

            if not unprocessed_reviews:
                logger.info(f"No unprocessed reviews found for business {business_id}")
                return ProcessingResult(
                    processed_count=0,
                    success_count=0,
                    error_count=0,
                    critical_reviews_found=0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    errors=[],
                )

            logger.info(
                f"Processing {len(unprocessed_reviews)} reviews for business {business_id}"
            )

            # 2. Detect languages and prepare for batch processing
            review_texts = []
            for review in unprocessed_reviews:
                detected_language = self._language_detector.detect_language(review.text)

                # Update review language if different
                if review.language != detected_language:
                    await self._review_repo.update(
                        review.id, language=detected_language
                    )

                review_texts.append(
                    ReviewText(
                        id=str(review.id),
                        text=review.text,
                        language=detected_language,
                        business_id=str(business_id),
                    )
                )

            # 3. Batch classify reviews
            try:
                classifications = await self._classifier.classify_batch(review_texts)
                logger.info(f"Successfully classified {len(classifications)} reviews")
            except Exception as e:
                logger.error(f"Batch classification failed: {e}")
                errors.append(f"Classification failed: {str(e)}")
                return ProcessingResult(
                    processed_count=len(unprocessed_reviews),
                    success_count=0,
                    error_count=len(unprocessed_reviews),
                    critical_reviews_found=0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    errors=errors,
                )

            # 4. Save classifications and check for alerts
            success_count = 0
            for i, classification in enumerate(classifications):
                try:
                    review = unprocessed_reviews[i]

                    # Save classification
                    from backend.db.schemas import ClassificationCreate
                    classification_data = ClassificationCreate(
                        review_id=review.id,
                        sentiment=classification.sentiment,
                        topics=classification.topics,
                        urgency=classification.urgency,
                        competitor_mentioned=classification.competitor_mentioned,
                        confidence_score=classification.confidence_score,
                        ai_model=classification.ai_model,
                        processing_time_ms=classification.processing_time_ms,
                    )
                    await self._classification_repo.create(classification_data)

                    # Check for critical reviews
                    if classification.urgency == "high":
                        critical_reviews_found += 1
                        await self._alert_service.handle_critical_review(
                            review, classification
                        )

                    # Check for competitor mentions
                    if classification.competitor_mentioned:
                        await self._alert_service.handle_competitor_mention(
                            review, classification
                        )

                    success_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to save classification for review {review.id}: {e}"
                    )
                    errors.append(f"Failed to save classification: {str(e)}")

            # 5. Update analytics (placeholder for now)
            await self._update_business_analytics(business_id)

            processing_time = int((time.time() - start_time) * 1000)

            logger.info(
                f"Review processing completed - Business: {business_id}, "
                f"Processed: {len(unprocessed_reviews)}, Success: {success_count}, "
                f"Errors: {len(errors)}, Critical: {critical_reviews_found}, "
                f"Time: {processing_time}ms"
            )

            return ProcessingResult(
                processed_count=len(unprocessed_reviews),
                success_count=success_count,
                error_count=len(errors),
                critical_reviews_found=critical_reviews_found,
                processing_time_ms=processing_time,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"Review processing failed for business {business_id}: {e}")
            return ProcessingResult(
                processed_count=0,
                success_count=0,
                error_count=1,
                critical_reviews_found=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                errors=[f"Processing failed: {str(e)}"],
            )

    async def process_single_review(self, review_id: UUID) -> bool:
        """Process a single review through the classification pipeline.

        Args:
            review_id: Review UUID to process

        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Get review
            review = await self._review_repo.get_by_id(review_id)
            if not review:
                logger.error(f"Review {review_id} not found")
                return False

            # Detect language
            detected_language = self._language_detector.detect_language(review.text)
            if review.language != detected_language:
                await self._review_repo.update(review.id, language=detected_language)

            # Classify review
            classification = await self._classifier.classify_review(
                review.text, detected_language
            )

            # Save classification
            from backend.db.schemas import ClassificationCreate
            classification_data = ClassificationCreate(
                review_id=review.id,
                sentiment=classification.sentiment,
                topics=classification.topics,
                urgency=classification.urgency,
                competitor_mentioned=classification.competitor_mentioned,
                confidence_score=classification.confidence_score,
                ai_model=classification.ai_model,
                processing_time_ms=classification.processing_time_ms,
            )
            await self._classification_repo.create(classification_data)

            # Handle alerts if needed
            if classification.urgency == "high":
                await self._alert_service.handle_critical_review(review, classification)

            if classification.competitor_mentioned:
                await self._alert_service.handle_competitor_mention(
                    review, classification
                )

            logger.info(f"Successfully processed review {review_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to process review {review_id}: {e}")
            return False

    async def _update_business_analytics(self, business_id: UUID) -> None:
        """Update business analytics after processing reviews.

        Args:
            business_id: Business UUID to update analytics for
        """
        try:
            # TODO: Implement analytics update logic
            # This would typically:
            # 1. Calculate new sentiment distributions
            # 2. Update topic frequencies
            # 3. Recalculate average ratings
            # 4. Update trend data

            logger.info(f"Analytics updated for business {business_id}")

        except Exception as e:
            logger.error(f"Failed to update analytics for business {business_id}: {e}")
