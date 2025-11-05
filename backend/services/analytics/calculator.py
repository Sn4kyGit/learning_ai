"""
Analytics calculation service for business intelligence metrics.

This service handles calculation of dashboard metrics, trend analysis,
and business performance indicators.
"""

import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta, date
from decimal import Decimal
from dataclasses import dataclass

from backend.db.repositories.review import ReviewRepository
from backend.db.repositories.classification import ClassificationRepository
from backend.db.repositories.business import BusinessRepository

logger = logging.getLogger(__name__)


@dataclass
class DashboardData:
    """Dashboard data structure."""

    business_id: str
    avg_rating: Decimal
    total_reviews: int
    sentiment_distribution: Dict[str, float]
    top_topics: List[str]
    competitor_mentions: int
    response_rate: Decimal
    avg_response_time_hours: Optional[Decimal]
    trend_data: List[Dict[str, Any]]
    last_updated: datetime


@dataclass
class TrendAnalysis:
    """Trend analysis data structure."""

    period_start: date
    period_end: date
    sentiment_trend: str  # improving, declining, stable
    rating_trend: str  # improving, declining, stable
    review_volume_trend: str  # increasing, decreasing, stable
    key_insights: List[str]


class AnalyticsCalculator:
    """Handles business intelligence calculations and dashboard data."""

    def __init__(
        self,
        review_repository: ReviewRepository,
        classification_repository: ClassificationRepository,
        business_repository: BusinessRepository,
    ):
        """Initialize analytics calculator.

        Args:
            review_repository: Review data repository
            classification_repository: Classification data repository
            business_repository: Business data repository
        """
        self._review_repo = review_repository
        self._classification_repo = classification_repository
        self._business_repo = business_repository

    async def calculate_dashboard_data(self, business_id: UUID) -> DashboardData:
        """Calculate comprehensive dashboard data for a business.

        Args:
            business_id: Business UUID

        Returns:
            DashboardData with all metrics
        """
        try:
            # Get basic business info
            business = await self._business_repo.get(business_id)
            if not business:
                raise ValueError(f"Business {business_id} not found")

            # Get review statistics
            review_stats = await self._review_repo.get_review_statistics(business_id)

            # Get sentiment distribution
            sentiment_dist = await self._classification_repo.get_sentiment_distribution(
                business_id
            )
            total_classified = sum(sentiment_dist.values())

            sentiment_percentages = {}
            if total_classified > 0:
                sentiment_percentages = {
                    sentiment: (count / total_classified) * 100
                    for sentiment, count in sentiment_dist.items()
                }

            # Get topic analysis
            topic_analysis = await self._classification_repo.get_topic_analysis(
                business_id
            )
            top_topics = sorted(
                topic_analysis.items(), key=lambda x: x[1], reverse=True
            )[:5]
            top_topics_list = [topic for topic, _ in top_topics]

            # Get competitor mentions (placeholder)
            competitor_mentions = 0  # TODO: Implement actual competitor mention count

            # Get trend data for the last 30 days
            trend_data = await self._calculate_trend_data(business_id, days=30)

            return DashboardData(
                business_id=str(business_id),
                avg_rating=Decimal(str(review_stats.get("avg_rating", 0.0))),
                total_reviews=review_stats.get("total_reviews", 0),
                sentiment_distribution=sentiment_percentages,
                top_topics=top_topics_list,
                competitor_mentions=competitor_mentions,
                response_rate=Decimal(
                    "0.0"
                ),  # TODO: Implement response rate calculation
                avg_response_time_hours=None,  # TODO: Implement response time calculation
                trend_data=trend_data,
                last_updated=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(
                f"Failed to calculate dashboard data for business {business_id}: {e}"
            )
            # Return empty dashboard data
            return DashboardData(
                business_id=str(business_id),
                avg_rating=Decimal("0.0"),
                total_reviews=0,
                sentiment_distribution={},
                top_topics=[],
                competitor_mentions=0,
                response_rate=Decimal("0.0"),
                avg_response_time_hours=None,
                trend_data=[],
                last_updated=datetime.utcnow(),
            )

    async def calculate_trends(
        self, business_id: UUID, days: int = 30
    ) -> TrendAnalysis:
        """Calculate sentiment and topic trends over time.

        Args:
            business_id: Business UUID
            days: Number of days to analyze

        Returns:
            TrendAnalysis with trend insights
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # Get reviews from the period
            recent_reviews = await self._review_repo.get_recent_reviews(
                business_id, days
            )

            if len(recent_reviews) < 5:  # Not enough data for trend analysis
                return TrendAnalysis(
                    period_start=start_date,
                    period_end=end_date,
                    sentiment_trend="stable",
                    rating_trend="stable",
                    review_volume_trend="stable",
                    key_insights=["Insufficient data for trend analysis"],
                )

            # Calculate trends (simplified implementation)
            # TODO: Implement proper trend analysis algorithms

            # For now, return placeholder trends
            return TrendAnalysis(
                period_start=start_date,
                period_end=end_date,
                sentiment_trend="improving",
                rating_trend="stable",
                review_volume_trend="increasing",
                key_insights=[
                    "Customer sentiment has improved over the last 30 days",
                    "Review volume is increasing, indicating growing customer engagement",
                    "Food quality remains the most mentioned positive topic",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to calculate trends for business {business_id}: {e}")
            return TrendAnalysis(
                period_start=date.today() - timedelta(days=days),
                period_end=date.today(),
                sentiment_trend="stable",
                rating_trend="stable",
                review_volume_trend="stable",
                key_insights=["Trend analysis unavailable"],
            )

    async def _calculate_trend_data(
        self, business_id: UUID, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Calculate daily trend data for charts.

        Args:
            business_id: Business UUID
            days: Number of days to include

        Returns:
            List of daily trend data points
        """
        try:
            # TODO: Implement actual daily aggregation from database
            # For now, return placeholder data

            trend_data = []
            end_date = date.today()

            for i in range(days):
                current_date = end_date - timedelta(days=i)

                # Placeholder data - would come from daily_analytics table
                trend_data.append(
                    {
                        "date": current_date.isoformat(),
                        "avg_rating": 4.2 + (i % 3) * 0.1,  # Simulated data
                        "review_count": max(0, 5 - (i % 7)),  # Simulated data
                        "sentiment_positive": 65.0 + (i % 5) * 2,  # Simulated data
                        "sentiment_neutral": 25.0,
                        "sentiment_negative": 10.0 - (i % 3),
                    }
                )

            return list(reversed(trend_data))  # Chronological order

        except Exception as e:
            logger.error(
                f"Failed to calculate trend data for business {business_id}: {e}"
            )
            return []

    async def calculate_business_score(self, business_id: UUID) -> Dict[str, Any]:
        """Calculate overall business performance score.

        Args:
            business_id: Business UUID

        Returns:
            Dictionary with business score and components
        """
        try:
            dashboard_data = await self.calculate_dashboard_data(business_id)

            # Calculate weighted score (simplified algorithm)
            rating_score = float(dashboard_data.avg_rating) * 20  # Max 100 points

            # Sentiment score
            sentiment_dist = dashboard_data.sentiment_distribution
            positive_pct = sentiment_dist.get("positive", 0)
            negative_pct = sentiment_dist.get("negative", 0)
            sentiment_score = max(0, positive_pct - negative_pct)

            # Volume score (reviews per month)
            volume_score = min(100, dashboard_data.total_reviews * 2)  # Cap at 100

            # Overall score (weighted average)
            overall_score = (
                rating_score * 0.4 + sentiment_score * 0.4 + volume_score * 0.2
            )

            return {
                "overall_score": round(overall_score, 1),
                "rating_score": round(rating_score, 1),
                "sentiment_score": round(sentiment_score, 1),
                "volume_score": round(volume_score, 1),
                "grade": self._score_to_grade(overall_score),
                "recommendations": self._generate_recommendations(dashboard_data),
            }

        except Exception as e:
            logger.error(f"Failed to calculate business score for {business_id}: {e}")
            return {
                "overall_score": 0.0,
                "rating_score": 0.0,
                "sentiment_score": 0.0,
                "volume_score": 0.0,
                "grade": "F",
                "recommendations": ["Unable to calculate score"],
            }

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade.

        Args:
            score: Numeric score (0-100)

        Returns:
            Letter grade (A-F)
        """
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_recommendations(self, dashboard_data: DashboardData) -> List[str]:
        """Generate recommendations based on dashboard data.

        Args:
            dashboard_data: Dashboard metrics

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        # Rating-based recommendations
        if dashboard_data.avg_rating < 3.5:
            recommendations.append("Focus on improving overall customer satisfaction")

        # Sentiment-based recommendations
        sentiment_dist = dashboard_data.sentiment_distribution
        negative_pct = sentiment_dist.get("negative", 0)

        if negative_pct > 30:
            recommendations.append(
                "Address negative feedback patterns to improve sentiment"
            )

        # Topic-based recommendations
        if "service" in dashboard_data.top_topics[:2]:
            recommendations.append(
                "Service quality is frequently mentioned - maintain high standards"
            )

        if "cleanliness" in dashboard_data.top_topics:
            recommendations.append(
                "Monitor cleanliness standards based on customer feedback"
            )

        # Volume-based recommendations
        if dashboard_data.total_reviews < 10:
            recommendations.append("Encourage more customers to leave reviews")

        return recommendations[:5]  # Limit to top 5 recommendations
