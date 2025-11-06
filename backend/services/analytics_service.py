"""
Analytics service for business intelligence metrics and dashboard data.

This service handles calculation of dashboard metrics, trend analysis,
caching, and real-time data updates for the business intelligence platform.
"""

import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal
from dataclasses import dataclass
import asyncio

from backend.db.repositories.review import ReviewRepository
from backend.db.repositories.classification import ClassificationRepository
from backend.db.repositories.business import BusinessRepository
from backend.services.analytics.calculator import AnalyticsCalculator, DashboardData, TrendAnalysis

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with expiration."""
    data: Any
    expires_at: datetime


class AnalyticsService:
    """Handles business intelligence calculations and dashboard data with caching."""

    def __init__(
        self,
        review_repository: ReviewRepository,
        classification_repository: ClassificationRepository,
        business_repository: BusinessRepository,
        cache_ttl_hours: int = 4,
    ):
        """Initialize analytics service.

        Args:
            review_repository: Review data repository
            classification_repository: Classification data repository
            business_repository: Business data repository
            cache_ttl_hours: Cache time-to-live in hours
        """
        self._review_repo = review_repository
        self._classification_repo = classification_repository
        self._business_repo = business_repository
        self._cache_ttl = timedelta(hours=cache_ttl_hours)
        self._cache: Dict[str, CacheEntry] = {}
        
        # Initialize calculator
        self._calculator = AnalyticsCalculator(
            review_repository=review_repository,
            classification_repository=classification_repository,
            business_repository=business_repository,
        )

    async def get_dashboard_data(
        self, 
        business_id: UUID,
        force_refresh: bool = False
    ) -> DashboardData:
        """Get comprehensive dashboard data with caching.

        Args:
            business_id: Business UUID
            force_refresh: Whether to bypass cache and recalculate

        Returns:
            DashboardData with all metrics
        """
        cache_key = f"dashboard_{business_id}"
        
        # Check cache first (unless force refresh)
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            if datetime.now(timezone.utc) < entry.expires_at:
                logger.debug(f"Returning cached dashboard data for business {business_id}")
                return entry.data

        try:
            # Calculate fresh data
            logger.info(f"Calculating fresh dashboard data for business {business_id}")
            dashboard_data = await self._calculator.calculate_dashboard_data(business_id)
            
            # Cache the result
            self._cache[cache_key] = CacheEntry(
                data=dashboard_data,
                expires_at=datetime.now(timezone.utc) + self._cache_ttl
            )
            
            return dashboard_data

        except Exception as e:
            logger.error(f"Failed to get dashboard data for business {business_id}: {e}")
            # Return cached data if available, even if expired
            if cache_key in self._cache:
                logger.warning(f"Returning expired cached data for business {business_id}")
                return self._cache[cache_key].data
            raise

    async def get_trend_analysis(
        self, 
        business_id: UUID, 
        days: int = 30,
        force_refresh: bool = False
    ) -> TrendAnalysis:
        """Get trend analysis with caching.

        Args:
            business_id: Business UUID
            days: Number of days to analyze
            force_refresh: Whether to bypass cache

        Returns:
            TrendAnalysis with trend insights
        """
        cache_key = f"trends_{business_id}_{days}"
        
        # Check cache first
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            if datetime.now(timezone.utc) < entry.expires_at:
                logger.debug(f"Returning cached trend analysis for business {business_id}")
                return entry.data

        try:
            # Calculate fresh trends
            logger.info(f"Calculating trend analysis for business {business_id} ({days} days)")
            trend_analysis = await self._calculator.calculate_trends(business_id, days)
            
            # Cache the result
            self._cache[cache_key] = CacheEntry(
                data=trend_analysis,
                expires_at=datetime.now(timezone.utc) + self._cache_ttl
            )
            
            return trend_analysis

        except Exception as e:
            logger.error(f"Failed to get trend analysis for business {business_id}: {e}")
            # Return cached data if available
            if cache_key in self._cache:
                return self._cache[cache_key].data
            raise

    async def get_business_score(
        self, 
        business_id: UUID,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Get business performance score with caching.

        Args:
            business_id: Business UUID
            force_refresh: Whether to bypass cache

        Returns:
            Dictionary with business score and components
        """
        cache_key = f"score_{business_id}"
        
        # Check cache first
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            if datetime.now(timezone.utc) < entry.expires_at:
                return entry.data

        try:
            # Calculate fresh score
            business_score = await self._calculator.calculate_business_score(business_id)
            
            # Cache the result
            self._cache[cache_key] = CacheEntry(
                data=business_score,
                expires_at=datetime.now(timezone.utc) + self._cache_ttl
            )
            
            return business_score

        except Exception as e:
            logger.error(f"Failed to get business score for business {business_id}: {e}")
            if cache_key in self._cache:
                return self._cache[cache_key].data
            raise

    async def update_business_analytics(self, business_id: UUID) -> None:
        """Update business analytics after processing reviews.

        Args:
            business_id: Business UUID to update analytics for
        """
        try:
            logger.info(f"Updating analytics for business {business_id}")
            
            # Invalidate cache for this business
            await self._invalidate_business_cache(business_id)
            
            # Update business rating statistics
            avg_rating, total_reviews = await self._business_repo.calculate_rating_stats(business_id)
            await self._business_repo.update_rating_stats(business_id, avg_rating, total_reviews)
            
            # Pre-calculate and cache fresh dashboard data
            await self.get_dashboard_data(business_id, force_refresh=True)
            
            logger.info(f"Analytics updated for business {business_id}")

        except Exception as e:
            logger.error(f"Failed to update analytics for business {business_id}: {e}")
            raise

    async def get_multi_business_dashboard(
        self, 
        business_ids: List[UUID],
        force_refresh: bool = False
    ) -> Dict[str, DashboardData]:
        """Get dashboard data for multiple businesses.

        Args:
            business_ids: List of business UUIDs
            force_refresh: Whether to bypass cache

        Returns:
            Dictionary mapping business IDs to dashboard data
        """
        try:
            # Get dashboard data for each business concurrently
            tasks = [
                self.get_dashboard_data(business_id, force_refresh)
                for business_id in business_ids
            ]
            
            dashboard_data_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            result = {}
            for i, business_id in enumerate(business_ids):
                data = dashboard_data_list[i]
                if isinstance(data, Exception):
                    logger.error(f"Failed to get dashboard data for business {business_id}: {data}")
                    # Create empty dashboard data for failed businesses
                    result[str(business_id)] = DashboardData(
                        business_id=str(business_id),
                        avg_rating=Decimal("0.0"),
                        total_reviews=0,
                        sentiment_distribution={},
                        top_topics=[],
                        competitor_mentions=0,
                        response_rate=Decimal("0.0"),
                        avg_response_time_hours=None,
                        trend_data=[],
                        last_updated=datetime.now(timezone.utc),
                    )
                else:
                    result[str(business_id)] = data
            
            return result

        except Exception as e:
            logger.error(f"Failed to get multi-business dashboard data: {e}")
            raise

    async def get_consolidated_metrics(
        self, 
        business_ids: List[UUID]
    ) -> Dict[str, Any]:
        """Get consolidated metrics across multiple businesses.

        Args:
            business_ids: List of business UUIDs

        Returns:
            Dictionary with consolidated metrics
        """
        try:
            # Get dashboard data for all businesses
            multi_dashboard = await self.get_multi_business_dashboard(business_ids)
            
            # Calculate consolidated metrics
            total_reviews = sum(data.total_reviews for data in multi_dashboard.values())
            
            if total_reviews == 0:
                return {
                    "total_businesses": len(business_ids),
                    "total_reviews": 0,
                    "avg_rating": 0.0,
                    "overall_sentiment": {"positive": 0, "neutral": 0, "negative": 0},
                    "top_topics": [],
                    "total_competitor_mentions": 0,
                }
            
            # Weighted average rating
            weighted_rating_sum = sum(
                float(data.avg_rating) * data.total_reviews 
                for data in multi_dashboard.values()
            )
            avg_rating = weighted_rating_sum / total_reviews if total_reviews > 0 else 0.0
            
            # Consolidated sentiment
            overall_sentiment = {"positive": 0, "neutral": 0, "negative": 0}
            for data in multi_dashboard.values():
                for sentiment, percentage in data.sentiment_distribution.items():
                    if sentiment in overall_sentiment:
                        overall_sentiment[sentiment] += percentage * data.total_reviews
            
            # Normalize sentiment percentages
            if total_reviews > 0:
                for sentiment in overall_sentiment:
                    overall_sentiment[sentiment] = overall_sentiment[sentiment] / total_reviews
            
            # Consolidated topics
            topic_counts = {}
            for data in multi_dashboard.values():
                for topic in data.top_topics:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_topics_list = [topic for topic, _ in top_topics]
            
            # Total competitor mentions
            total_competitor_mentions = sum(
                data.competitor_mentions for data in multi_dashboard.values()
            )
            
            return {
                "total_businesses": len(business_ids),
                "total_reviews": total_reviews,
                "avg_rating": round(avg_rating, 2),
                "overall_sentiment": {
                    k: round(v, 1) for k, v in overall_sentiment.items()
                },
                "top_topics": top_topics_list,
                "total_competitor_mentions": total_competitor_mentions,
            }

        except Exception as e:
            logger.error(f"Failed to get consolidated metrics: {e}")
            raise

    async def schedule_cache_refresh(self) -> None:
        """Refresh cached data for all businesses (called by scheduler)."""
        try:
            logger.info("Starting scheduled cache refresh")
            
            # Get all businesses that need cache refresh
            businesses = await self._business_repo.get_businesses_needing_analysis(limit=100)
            
            # Refresh dashboard data for each business
            refresh_tasks = []
            for business in businesses:
                task = self.get_dashboard_data(business.id, force_refresh=True)
                refresh_tasks.append(task)
            
            # Execute refreshes concurrently (in batches to avoid overwhelming the system)
            batch_size = 10
            for i in range(0, len(refresh_tasks), batch_size):
                batch = refresh_tasks[i:i + batch_size]
                await asyncio.gather(*batch, return_exceptions=True)
                
                # Small delay between batches
                if i + batch_size < len(refresh_tasks):
                    await asyncio.sleep(1)
            
            logger.info(f"Completed scheduled cache refresh for {len(businesses)} businesses")

        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")

    async def _invalidate_business_cache(self, business_id: UUID) -> None:
        """Invalidate all cached data for a business.

        Args:
            business_id: Business UUID
        """
        keys_to_remove = []
        for key in self._cache.keys():
            if str(business_id) in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
        
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for business {business_id}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        now = datetime.now(timezone.utc)
        active_entries = sum(1 for entry in self._cache.values() if entry.expires_at > now)
        expired_entries = len(self._cache) - active_entries
        
        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": expired_entries,
            "cache_ttl_hours": self._cache_ttl.total_seconds() / 3600,
        }

    async def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Analytics cache cleared")

    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.expires_at <= now
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        return len(expired_keys)