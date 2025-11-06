"""
Business repository for database operations.

This module provides business-specific database operations
including CRUD operations and business queries.
"""

from typing import List, Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from backend.db.models import Business, Review, Organization
from backend.db.repositories.base import BaseRepository, RepositoryError
from backend.db.schemas import BusinessCreate, BusinessUpdate

logger = logging.getLogger(__name__)


class BusinessRepository(BaseRepository[Business, BusinessCreate, BusinessUpdate]):
    """Repository for business entity operations."""

    def __init__(self, session: AsyncSession):
        """Initialize business repository.

        Args:
            session: Async database session
        """
        super().__init__(Business, session)

    async def get_by_google_place_id(self, google_place_id: str) -> Optional[Business]:
        """Get business by Google Place ID.

        Args:
            google_place_id: Google Places API identifier

        Returns:
            Business instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(Business)
                .options(selectinload(Business.organization))
                .where(Business.google_place_id == google_place_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting business by Google Place ID {google_place_id}: {e}")
            raise RepositoryError(f"Failed to get business: {str(e)}")

    async def get_by_organization(
        self, 
        organization_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Business]:
        """Get businesses by organization ID.

        Args:
            organization_id: Organization UUID
            skip: Number of businesses to skip
            limit: Maximum number of businesses to return

        Returns:
            List of business instances
        """
        try:
            result = await self.session.execute(
                select(Business)
                .options(selectinload(Business.organization))
                .where(Business.organization_id == organization_id)
                .order_by(Business.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting businesses for organization {organization_id}: {e}")
            raise RepositoryError(f"Failed to get businesses: {str(e)}")

    async def get_by_id(self, business_id: UUID) -> Optional[Business]:
        """Get business by ID (alias for get method).

        Args:
            business_id: Business UUID

        Returns:
            Business instance or None if not found
        """
        return await self.get(business_id)

    async def get_with_reviews(self, business_id: UUID) -> Optional[Business]:
        """Get business with its reviews loaded.

        Args:
            business_id: Business UUID

        Returns:
            Business instance with reviews or None if not found
        """
        try:
            result = await self.session.execute(
                select(Business)
                .options(
                    selectinload(Business.reviews),
                    selectinload(Business.organization)
                )
                .where(Business.id == business_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting business with reviews {business_id}: {e}")
            raise RepositoryError(f"Failed to get business with reviews: {str(e)}")

    async def update_rating_stats(
        self, 
        business_id: UUID, 
        avg_rating: float, 
        total_reviews: int
    ) -> Optional[Business]:
        """Update business rating statistics.

        Args:
            business_id: Business UUID
            avg_rating: New average rating
            total_reviews: New total review count

        Returns:
            Updated business instance or None if not found
        """
        try:
            business = await self.get(business_id)
            if not business:
                return None

            business.avg_rating = avg_rating
            business.total_reviews = total_reviews

            await self.session.commit()
            await self.session.refresh(business)
            
            logger.debug(f"Updated rating stats for business {business_id}: {avg_rating} ({total_reviews} reviews)")
            return business
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating rating stats for business {business_id}: {e}")
            raise RepositoryError(f"Failed to update rating stats: {str(e)}")

    async def calculate_rating_stats(self, business_id: UUID) -> tuple[float, int]:
        """Calculate current rating statistics from reviews.

        Args:
            business_id: Business UUID

        Returns:
            Tuple of (average_rating, total_reviews)
        """
        try:
            result = await self.session.execute(
                select(
                    func.avg(Review.rating).label('avg_rating'),
                    func.count(Review.id).label('total_reviews')
                )
                .where(
                    and_(
                        Review.business_id == business_id,
                        Review.rating.isnot(None)
                    )
                )
            )
            
            row = result.first()
            avg_rating = float(row.avg_rating) if row.avg_rating else 0.0
            total_reviews = int(row.total_reviews) if row.total_reviews else 0
            
            return avg_rating, total_reviews
        except Exception as e:
            logger.error(f"Error calculating rating stats for business {business_id}: {e}")
            raise RepositoryError(f"Failed to calculate rating stats: {str(e)}")

    async def get_businesses_needing_analysis(self, limit: int = 50) -> List[Business]:
        """Get businesses that have unanalyzed reviews.

        Args:
            limit: Maximum number of businesses to return

        Returns:
            List of businesses with unanalyzed reviews
        """
        try:
            # This is a simplified version - in a real implementation,
            # you'd join with reviews and classifications to find unanalyzed reviews
            result = await self.session.execute(
                select(Business)
                .options(selectinload(Business.reviews))
                .order_by(Business.updated_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting businesses needing analysis: {e}")
            raise RepositoryError(f"Failed to get businesses needing analysis: {str(e)}")

    async def search_businesses(
        self, 
        query: str, 
        organization_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Business]:
        """Search businesses by name or address.

        Args:
            query: Search query string
            organization_id: Optional organization filter
            skip: Number of results to skip
            limit: Maximum number of results

        Returns:
            List of matching businesses
        """
        try:
            search_filter = or_(
                Business.name.ilike(f"%{query}%"),
                Business.address.ilike(f"%{query}%")
            )
            
            if organization_id:
                search_filter = and_(
                    search_filter,
                    Business.organization_id == organization_id
                )

            result = await self.session.execute(
                select(Business)
                .options(selectinload(Business.organization))
                .where(search_filter)
                .order_by(Business.name)
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching businesses with query '{query}': {e}")
            raise RepositoryError(f"Failed to search businesses: {str(e)}")

    async def get_business_summary(self, business_id: UUID) -> Optional[dict]:
        """Get business summary with key metrics.

        Args:
            business_id: Business UUID

        Returns:
            Dictionary with business summary or None if not found
        """
        try:
            business = await self.get_with_reviews(business_id)
            if not business:
                return None

            # Calculate basic metrics
            avg_rating, total_reviews = await self.calculate_rating_stats(business_id)
            
            # Get recent review count (last 30 days)
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            
            recent_reviews_result = await self.session.execute(
                select(func.count(Review.id))
                .where(
                    and_(
                        Review.business_id == business_id,
                        Review.published_at >= thirty_days_ago
                    )
                )
            )
            recent_reviews = recent_reviews_result.scalar() or 0

            return {
                "id": str(business.id),
                "name": business.name,
                "category": business.category,
                "avg_rating": avg_rating,
                "total_reviews": total_reviews,
                "recent_reviews_30d": recent_reviews,
                "google_place_id": business.google_place_id,
                "created_at": business.created_at,
                "updated_at": business.updated_at
            }
        except Exception as e:
            logger.error(f"Error getting business summary for {business_id}: {e}")
            raise RepositoryError(f"Failed to get business summary: {str(e)}")