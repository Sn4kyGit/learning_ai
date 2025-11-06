"""
Classification repository for database operations.

This module provides classification-specific database operations
including CRUD operations and classification analysis queries.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from backend.db.models import Classification, Review
from backend.db.repositories.base import BaseRepository, RepositoryError
from backend.db.schemas import ClassificationCreate, ClassificationResponse

logger = logging.getLogger(__name__)


class ClassificationRepository(BaseRepository[Classification, ClassificationCreate, ClassificationResponse]):
    """Repository for classification entity operations."""

    def __init__(self, session: AsyncSession):
        """Initialize classification repository.

        Args:
            session: Async database session
        """
        super().__init__(Classification, session)

    async def get_by_review_id(self, review_id: UUID) -> Optional[Classification]:
        """Get classification by review ID.

        Args:
            review_id: Review UUID

        Returns:
            Classification instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(Classification).where(Classification.review_id == review_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting classification for review {review_id}: {e}")
            raise RepositoryError(f"Failed to get classification: {str(e)}")

    async def get_by_business_id(self, business_id: UUID) -> List[Classification]:
        """Get all classifications for a business.

        Args:
            business_id: Business UUID

        Returns:
            List of classification instances
        """
        try:
            result = await self.session.execute(
                select(Classification)
                .options(selectinload(Classification.review))
                .join(Review)
                .where(Review.business_id == business_id)
                .order_by(desc(Classification.created_at))
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting classifications for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get classifications: {str(e)}")

    async def get_sentiment_distribution(self, business_id: UUID) -> Dict[str, int]:
        """Get sentiment distribution for a business.

        Args:
            business_id: Business UUID

        Returns:
            Dictionary with sentiment counts
        """
        try:
            result = await self.session.execute(
                select(
                    Classification.sentiment,
                    func.count(Classification.id).label('count')
                )
                .join(Review)
                .where(Review.business_id == business_id)
                .group_by(Classification.sentiment)
            )
            
            return {row.sentiment: row.count for row in result}
        except Exception as e:
            logger.error(f"Error getting sentiment distribution for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get sentiment distribution: {str(e)}")

    async def get_topic_analysis(self, business_id: UUID) -> Dict[str, int]:
        """Get topic frequency analysis for a business.

        Args:
            business_id: Business UUID

        Returns:
            Dictionary with topic counts
        """
        try:
            # This is a simplified implementation
            # In a real scenario, you'd use PostgreSQL array functions
            result = await self.session.execute(
                select(Classification.topics)
                .join(Review)
                .where(Review.business_id == business_id)
            )
            
            topic_counts = {}
            for row in result:
                if row.topics:
                    for topic in row.topics:
                        topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            return topic_counts
        except Exception as e:
            logger.error(f"Error getting topic analysis for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get topic analysis: {str(e)}")

    async def get_urgent_classifications(
        self, 
        business_id: UUID, 
        urgency_levels: List[str] = ["high", "medium"],
        limit: int = 50
    ) -> List[Classification]:
        """Get urgent classifications for a business.

        Args:
            business_id: Business UUID
            urgency_levels: List of urgency levels to include
            limit: Maximum number of classifications to return

        Returns:
            List of urgent classifications
        """
        try:
            result = await self.session.execute(
                select(Classification)
                .options(selectinload(Classification.review))
                .join(Review)
                .where(
                    and_(
                        Review.business_id == business_id,
                        Classification.urgency.in_(urgency_levels)
                    )
                )
                .order_by(
                    Classification.urgency == "high",  # High urgency first
                    desc(Classification.created_at)
                )
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting urgent classifications for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get urgent classifications: {str(e)}")

    async def get_competitor_mentions(
        self, 
        business_id: UUID, 
        days: int = 30
    ) -> List[Classification]:
        """Get classifications with competitor mentions.

        Args:
            business_id: Business UUID
            days: Number of days to look back

        Returns:
            List of classifications with competitor mentions
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            result = await self.session.execute(
                select(Classification)
                .options(selectinload(Classification.review))
                .join(Review)
                .where(
                    and_(
                        Review.business_id == business_id,
                        Classification.competitor_mentioned == True,
                        Classification.created_at >= cutoff_date
                    )
                )
                .order_by(desc(Classification.created_at))
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting competitor mentions for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get competitor mentions: {str(e)}")

    async def get_classification_statistics(self, business_id: UUID) -> Dict[str, Any]:
        """Get comprehensive classification statistics for a business.

        Args:
            business_id: Business UUID

        Returns:
            Dictionary with classification statistics
        """
        try:
            # Basic stats
            basic_stats = await self.session.execute(
                select(
                    func.count(Classification.id).label('total_classifications'),
                    func.avg(Classification.confidence_score).label('avg_confidence'),
                    func.min(Classification.created_at).label('first_classification'),
                    func.max(Classification.created_at).label('latest_classification')
                )
                .join(Review)
                .where(Review.business_id == business_id)
            )
            basic_row = basic_stats.first()

            # Sentiment distribution
            sentiment_dist = await self.get_sentiment_distribution(business_id)

            # Urgency distribution
            urgency_dist = await self.session.execute(
                select(
                    Classification.urgency,
                    func.count(Classification.id).label('count')
                )
                .join(Review)
                .where(Review.business_id == business_id)
                .group_by(Classification.urgency)
            )
            urgency_distribution = {row.urgency: row.count for row in urgency_dist}

            # Topic analysis
            topic_analysis = await self.get_topic_analysis(business_id)

            # Competitor mentions count
            competitor_count = await self.session.execute(
                select(func.count(Classification.id))
                .join(Review)
                .where(
                    and_(
                        Review.business_id == business_id,
                        Classification.competitor_mentioned == True
                    )
                )
            )

            return {
                "total_classifications": basic_row.total_classifications or 0,
                "avg_confidence": float(basic_row.avg_confidence) if basic_row.avg_confidence else 0.0,
                "first_classification": basic_row.first_classification,
                "latest_classification": basic_row.latest_classification,
                "sentiment_distribution": sentiment_dist,
                "urgency_distribution": urgency_distribution,
                "topic_analysis": topic_analysis,
                "competitor_mentions": competitor_count.scalar() or 0
            }
        except Exception as e:
            logger.error(f"Error getting classification statistics for business {business_id}: {e}")
            raise RepositoryError(f"Failed to get classification statistics: {str(e)}")

    async def bulk_create_classifications(
        self, 
        classifications: List[ClassificationCreate]
    ) -> List[Classification]:
        """Create multiple classifications in a single transaction.

        Args:
            classifications: List of classification creation schemas

        Returns:
            List of created classification instances
        """
        try:
            created_classifications = []
            
            for classification_data in classifications:
                obj_data = classification_data.model_dump()
                db_obj = Classification(**obj_data)
                self.session.add(db_obj)
                created_classifications.append(db_obj)

            if created_classifications:
                await self.session.commit()
                
                # Refresh all objects
                for classification in created_classifications:
                    await self.session.refresh(classification)
                
                logger.info(f"Bulk created {len(created_classifications)} classifications")
            
            return created_classifications
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error bulk creating classifications: {e}")
            raise RepositoryError(f"Failed to bulk create classifications: {str(e)}")