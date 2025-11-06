"""
Review repository for database operations.

This module provides review-specific database operations
including CRUD operations and review analysis queries.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from backend.db.models import Review, Classification, Business
from backend.db.repositories.base import BaseRepository, RepositoryError
from backend.db.schemas import ReviewCreate, ReviewResponse

logger = logging.getLogger(__name__)


class ReviewRepository(BaseRepository[Review, ReviewCreate, ReviewResponse]):
    """Repository for review entity operations."""

    def __init__(self, session: AsyncSession):
        """Initialize review repository.

        Args:
            session: Async database session
        """
        super().__init__(Review, session)

    async def get_by_business(
        self, 
        business_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        include_classifications: bool = False
    ) -> List[Review]:
        """Get reviews for a specific business.

        Args:
            business_id: Business UUID
            skip: Number of reviews to skip
            limit: Maximum number of reviews to return
            include_classifications: Whether to load classification data

        Returns:
            List of review instances
        """
        try:
            query = select(Review).where(Review.business_id == business_id)
            
            if include_classifications:
                query = query.options(selectinload(Review.classifications))
            
            query = query.order_by(desc(Review.published_at)).offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting reviews for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get reviews: {str(e)}")

    async def get_by_external_id(
        self, 
        business_id: UUID, 
        external_id: str, 
        source: str = "google"
    ) -> Optional[Review]:
        """Get review by external ID to prevent duplicates.

        Args:
            business_id: Business UUID
            external_id: External review ID
            source: Review source (default: google)

        Returns:
            Review instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(Review).where(
                    and_(
                        Review.business_id == business_id,
                        Review.external_id == external_id,
                        Review.source == source
                    )
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting review by external ID {external_id}: {e}")
            raise RepositoryError(f"Failed to get review: {str(e)}")

    async def get_unclassified_reviews(
        self, 
        business_id: Optional[UUID] = None, 
        limit: int = 500
    ) -> List[Review]:
        """Get reviews that haven't been classified yet.

        Args:
            business_id: Optional business filter
            limit: Maximum number of reviews to return

        Returns:
            List of unclassified reviews
        """
        try:
            # Subquery to find reviews without classifications
            classified_review_ids = select(Classification.review_id).distinct()
            
            query = select(Review).where(
                Review.id.notin_(classified_review_ids)
            )
            
            if business_id:
                query = query.where(Review.business_id == business_id)
            
            query = query.order_by(desc(Review.published_at)).limit(limit)
            
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting unclassified reviews: {e}")
            raise RepositoryError(f"Failed to get unclassified reviews: {str(e)}")

    async def get_recent_reviews(
        self, 
        business_id: UUID, 
        days: int = 7, 
        limit: int = 100
    ) -> List[Review]:
        """Get recent reviews for a business.

        Args:
            business_id: Business UUID
            days: Number of days to look back
            limit: Maximum number of reviews to return

        Returns:
            List of recent reviews
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            result = await self.session.execute(
                select(Review)
                .options(selectinload(Review.classifications))
                .where(
                    and_(
                        Review.business_id == business_id,
                        Review.published_at >= cutoff_date
                    )
                )
                .order_by(desc(Review.published_at))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting recent reviews for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get recent reviews: {str(e)}")

    async def get_reviews_by_rating(
        self, 
        business_id: UUID, 
        min_rating: int = 1, 
        max_rating: int = 5,
        limit: int = 100
    ) -> List[Review]:
        """Get reviews filtered by rating range.

        Args:
            business_id: Business UUID
            min_rating: Minimum rating (1-5)
            max_rating: Maximum rating (1-5)
            limit: Maximum number of reviews to return

        Returns:
            List of reviews in rating range
        """
        try:
            result = await self.session.execute(
                select(Review)
                .options(selectinload(Review.classifications))
                .where(
                    and_(
                        Review.business_id == business_id,
                        Review.rating >= min_rating,
                        Review.rating <= max_rating,
                        Review.rating.isnot(None)
                    )
                )
                .order_by(desc(Review.published_at))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting reviews by rating for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get reviews by rating: {str(e)}")

    async def get_reviews_by_language(
        self, 
        business_id: UUID, 
        language: str, 
        limit: int = 100
    ) -> List[Review]:
        """Get reviews in a specific language.

        Args:
            business_id: Business UUID
            language: Language code (e.g., 'en', 'de', 'tr')
            limit: Maximum number of reviews to return

        Returns:
            List of reviews in specified language
        """
        try:
            result = await self.session.execute(
                select(Review)
                .options(selectinload(Review.classifications))
                .where(
                    and_(
                        Review.business_id == business_id,
                        Review.language == language
                    )
                )
                .order_by(desc(Review.published_at))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting reviews by language {language}: {e}")
            raise RepositoryError(f"Failed to get reviews by language: {str(e)}")

    async def search_reviews(
        self, 
        business_id: UUID, 
        search_text: str, 
        limit: int = 100
    ) -> List[Review]:
        """Search reviews by text content.

        Args:
            business_id: Business UUID
            search_text: Text to search for
            limit: Maximum number of reviews to return

        Returns:
            List of matching reviews
        """
        try:
            result = await self.session.execute(
                select(Review)
                .options(selectinload(Review.classifications))
                .where(
                    and_(
                        Review.business_id == business_id,
                        Review.text.ilike(f"%{search_text}%")
                    )
                )
                .order_by(desc(Review.published_at))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching reviews with text '{search_text}': {e}")
            raise RepositoryError(f"Failed to search reviews: {str(e)}")

    async def get_review_statistics(self, business_id: UUID) -> Dict[str, Any]:
        """Get comprehensive review statistics for a business.

        Args:
            business_id: Business UUID

        Returns:
            Dictionary with review statistics
        """
        try:
            # Basic stats
            basic_stats = await self.session.execute(
                select(
                    func.count(Review.id).label('total_reviews'),
                    func.avg(Review.rating).label('avg_rating'),
                    func.min(Review.published_at).label('first_review'),
                    func.max(Review.published_at).label('latest_review')
                )
                .where(Review.business_id == business_id)
            )
            basic_row = basic_stats.first()

            # Rating distribution
            rating_dist = await self.session.execute(
                select(
                    Review.rating,
                    func.count(Review.id).label('count')
                )
                .where(
                    and_(
                        Review.business_id == business_id,
                        Review.rating.isnot(None)
                    )
                )
                .group_by(Review.rating)
                .order_by(Review.rating)
            )
            rating_distribution = {row.rating: row.count for row in rating_dist}

            # Language distribution
            lang_dist = await self.session.execute(
                select(
                    Review.language,
                    func.count(Review.id).label('count')
                )
                .where(Review.business_id == business_id)
                .group_by(Review.language)
                .order_by(func.count(Review.id).desc())
            )
            language_distribution = {row.language: row.count for row in lang_dist}

            # Recent activity (last 30 days)
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            recent_count = await self.session.execute(
                select(func.count(Review.id))
                .where(
                    and_(
                        Review.business_id == business_id,
                        Review.published_at >= thirty_days_ago
                    )
                )
            )

            return {
                "total_reviews": basic_row.total_reviews or 0,
                "avg_rating": float(basic_row.avg_rating) if basic_row.avg_rating else 0.0,
                "first_review": basic_row.first_review,
                "latest_review": basic_row.latest_review,
                "recent_reviews_30d": recent_count.scalar() or 0,
                "rating_distribution": rating_distribution,
                "language_distribution": language_distribution
            }
        except Exception as e:
            logger.error(f"Error getting review statistics for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get review statistics: {str(e)}")

    async def bulk_import_reviews(self, reviews: List[ReviewCreate]) -> List[Review]:
        """Import multiple reviews in a single transaction.

        Args:
            reviews: List of review creation schemas

        Returns:
            List of created review instances
        """
        try:
            created_reviews = []
            
            for review_data in reviews:
                # Check for duplicates
                existing = await self.get_by_external_id(
                    review_data.business_id,
                    review_data.external_id,
                    review_data.source
                )
                
                if existing:
                    logger.debug(f"Skipping duplicate review: {review_data.external_id}")
                    continue
                
                # Create new review
                obj_data = review_data.model_dump()
                db_obj = Review(**obj_data)
                self.session.add(db_obj)
                created_reviews.append(db_obj)

            if created_reviews:
                await self.session.commit()
                
                # Refresh all objects
                for review in created_reviews:
                    await self.session.refresh(review)
                
                logger.info(f"Bulk imported {len(created_reviews)} reviews")
            
            return created_reviews
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error bulk importing reviews: {e}")
            raise RepositoryError(f"Failed to bulk import reviews: {str(e)}")

    async def get_reviews_needing_response(
        self, 
        business_id: UUID, 
        urgency_levels: List[str] = ["high", "medium"],
        limit: int = 50
    ) -> List[Review]:
        """Get reviews that need responses based on urgency.

        Args:
            business_id: Business UUID
            urgency_levels: List of urgency levels to include
            limit: Maximum number of reviews to return

        Returns:
            List of reviews needing responses
        """
        try:
            result = await self.session.execute(
                select(Review)
                .join(Classification)
                .options(selectinload(Review.classifications))
                .where(
                    and_(
                        Review.business_id == business_id,
                        Classification.urgency.in_(urgency_levels)
                    )
                )
                .order_by(
                    Classification.urgency == "high",  # High urgency first
                    desc(Review.published_at)
                )
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting reviews needing response: {e}")
            raise RepositoryError(f"Failed to get reviews needing response: {str(e)}")

    async def get_recent_imports(
        self, 
        business_id: UUID, 
        limit: int = 10
    ) -> List[Review]:
        """Get recently imported reviews for import history tracking.

        Args:
            business_id: Business UUID
            limit: Maximum number of reviews to return

        Returns:
            List of recently imported reviews
        """
        try:
            result = await self.session.execute(
                select(Review)
                .where(Review.business_id == business_id)
                .order_by(desc(Review.created_at))
                .limit(limit * 10)  # Get more to group by import batches
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting recent imports for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get recent imports: {str(e)}")