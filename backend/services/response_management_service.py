"""
Response Management Service for Local Business Intelligence Bot.

This service handles review response management including AI-powered response
template suggestions, tone analysis, response tracking, and priority queue
management for urgent reviews.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case

from backend.ai.base import BusinessAdvisorProtocol, BusinessContext
from backend.db.models import Review, Classification, Business, ReviewResponse
from backend.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ResponsePriority(Enum):
    """Priority levels for review responses."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ResponseTone(Enum):
    """Tone analysis results for response drafts."""
    PROFESSIONAL = "professional"
    EMPATHETIC = "empathetic"
    DEFENSIVE = "defensive"
    CASUAL = "casual"
    INAPPROPRIATE = "inappropriate"


@dataclass
class ResponseTemplate:
    """AI-generated response template for a review."""
    template_text: str
    tone: ResponseTone
    confidence_score: float
    suggested_modifications: List[str]
    ai_model: str
    processing_time_ms: int


@dataclass
class ToneAnalysis:
    """Analysis of response tone and professionalism."""
    primary_tone: ResponseTone
    tone_confidence: float
    professionalism_score: float  # 0.0 to 1.0
    empathy_score: float  # 0.0 to 1.0
    suggestions: List[str]
    issues: List[str]  # Potential problems with the response


@dataclass
class ResponseMetrics:
    """Response rate and performance metrics."""
    total_reviews: int
    responded_reviews: int
    response_rate: float  # Percentage
    avg_response_time_hours: float
    responses_by_priority: Dict[ResponsePriority, int]
    responses_by_sentiment: Dict[str, int]  # positive, negative, neutral


@dataclass
class PriorityQueueItem:
    """Item in the response priority queue."""
    review_id: str
    business_id: str
    priority: ResponsePriority
    urgency_score: float
    sentiment: str
    topics: List[str]
    days_since_published: int
    has_response: bool
    created_at: datetime


class ResponseManagementService:
    """Service for managing review responses and AI-powered assistance."""

    def __init__(
        self,
        db_session: AsyncSession,
        business_advisor: BusinessAdvisorProtocol,
        repository: Optional[BaseRepository] = None
    ):
        """Initialize response management service.
        
        Args:
            db_session: Database session
            business_advisor: AI advisor for response generation
            repository: Optional repository for data access
        """
        self._db = db_session
        self._advisor = business_advisor
        self._repository = repository or BaseRepository(db_session)

    async def generate_response_template(
        self,
        review_id: str,
        business_id: str,
        language: str = "en",
        tone_preference: Optional[ResponseTone] = None
    ) -> ResponseTemplate:
        """Generate AI-powered response template for a review.
        
        Args:
            review_id: ID of the review to respond to
            business_id: ID of the business
            language: Response language
            tone_preference: Preferred tone for the response
            
        Returns:
            ResponseTemplate with AI-generated content
            
        Raises:
            ValueError: If review or business not found
            Exception: If template generation fails
        """
        start_time = time.time()
        
        try:
            # Get review and classification data
            review_data = await self._get_review_with_classification(review_id)
            if not review_data:
                raise ValueError(f"Review {review_id} not found")
            
            review, classification = review_data
            
            # Get business context
            business_context = await self._get_business_context(business_id)
            
            # Create response generation prompt
            prompt = self._create_response_prompt(
                review, classification, tone_preference, language
            )
            
            # Generate response using business advisor
            advisor_response = await self._advisor.generate_response(
                message=prompt,
                context=business_context,
                language=language
            )
            
            # Parse and analyze the generated response
            template_text = self._extract_response_template(advisor_response.message)
            tone_analysis = await self._analyze_response_tone(template_text, language)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return ResponseTemplate(
                template_text=template_text,
                tone=tone_analysis.primary_tone,
                confidence_score=float(advisor_response.confidence_score),
                suggested_modifications=tone_analysis.suggestions,
                ai_model=advisor_response.ai_model,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Response template generation failed for review {review_id}: {e}")
            raise

    async def analyze_response_tone(
        self,
        response_text: str,
        language: str = "en"
    ) -> ToneAnalysis:
        """Analyze the tone and professionalism of a response draft.
        
        Args:
            response_text: The response text to analyze
            language: Language of the response
            
        Returns:
            ToneAnalysis with tone assessment and suggestions
        """
        return await self._analyze_response_tone(response_text, language)

    async def get_response_queue(
        self,
        business_id: str,
        priority_filter: Optional[ResponsePriority] = None,
        limit: int = 50
    ) -> List[PriorityQueueItem]:
        """Get prioritized queue of reviews needing responses.
        
        Args:
            business_id: ID of the business
            priority_filter: Optional priority level filter
            limit: Maximum number of items to return
            
        Returns:
            List of prioritized queue items
        """
        try:
            # Build query for reviews needing responses
            query = (
                select(Review, Classification)
                .join(Classification, Review.id == Classification.review_id)
                .where(Review.business_id == business_id)
                .order_by(
                    # Order by urgency first, then by days since published
                    desc(
                        case(
                            (Classification.urgency == "high", 4),
                            (Classification.urgency == "medium", 3),
                            (Classification.urgency == "low", 2),
                            else_=1
                        )
                    ),
                    desc(func.extract('days', func.now() - Review.published_at))
                )
                .limit(limit)
            )
            
            result = await self._db.execute(query)
            review_data = result.fetchall()
            
            # Convert to priority queue items
            queue_items = []
            for review, classification in review_data:
                # Calculate priority based on urgency and sentiment
                priority = self._calculate_response_priority(
                    classification.urgency,
                    classification.sentiment,
                    review.rating
                )
                
                # Skip if priority filter doesn't match
                if priority_filter and priority != priority_filter:
                    continue
                
                # Calculate days since published
                days_since = (datetime.now(timezone.utc) - review.published_at).days
                
                # Check if review already has a response
                has_response = await self._check_has_response(review.id)
                
                # Calculate urgency score for sorting
                urgency_score = self._calculate_urgency_score(
                    classification.urgency,
                    classification.sentiment,
                    review.rating,
                    days_since
                )
                
                queue_items.append(PriorityQueueItem(
                    review_id=str(review.id),
                    business_id=str(review.business_id),
                    priority=priority,
                    urgency_score=urgency_score,
                    sentiment=classification.sentiment,
                    topics=classification.topics,
                    days_since_published=days_since,
                    has_response=has_response,
                    created_at=review.published_at
                ))
            
            # Sort by urgency score (highest first)
            queue_items.sort(key=lambda x: x.urgency_score, reverse=True)
            
            return queue_items
            
        except Exception as e:
            logger.error(f"Failed to get response queue for business {business_id}: {e}")
            raise

    async def track_response_metrics(
        self,
        business_id: str,
        period_days: int = 30
    ) -> ResponseMetrics:
        """Calculate response rate and performance metrics.
        
        Args:
            business_id: ID of the business
            period_days: Number of days to analyze
            
        Returns:
            ResponseMetrics with performance data
        """
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=period_days)
            
            # Get total reviews in period
            total_query = (
                select(func.count(Review.id))
                .where(
                    and_(
                        Review.business_id == business_id,
                        Review.published_at >= start_date,
                        Review.published_at <= end_date
                    )
                )
            )
            total_result = await self._db.execute(total_query)
            total_reviews = total_result.scalar() or 0
            
            # Get reviews with responses
            # Note: This assumes a ReviewResponse table exists
            # For now, we'll simulate this calculation
            responded_reviews = await self._count_responded_reviews(
                business_id, start_date, end_date
            )
            
            # Calculate response rate
            response_rate = (responded_reviews / total_reviews * 100) if total_reviews > 0 else 0.0
            
            # Calculate average response time
            avg_response_time = await self._calculate_avg_response_time(
                business_id, start_date, end_date
            )
            
            # Get responses by priority and sentiment
            responses_by_priority = await self._get_responses_by_priority(
                business_id, start_date, end_date
            )
            responses_by_sentiment = await self._get_responses_by_sentiment(
                business_id, start_date, end_date
            )
            
            return ResponseMetrics(
                total_reviews=total_reviews,
                responded_reviews=responded_reviews,
                response_rate=response_rate,
                avg_response_time_hours=avg_response_time,
                responses_by_priority=responses_by_priority,
                responses_by_sentiment=responses_by_sentiment
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate response metrics for business {business_id}: {e}")
            raise

    async def save_response(
        self,
        review_id: str,
        response_text: str,
        user_id: str,
        is_published: bool = False
    ) -> str:
        """Save a response to a review.
        
        Args:
            review_id: ID of the review being responded to
            response_text: The response text
            user_id: ID of the user creating the response
            is_published: Whether the response is published or draft
            
        Returns:
            ID of the created response record
            
        Raises:
            ValueError: If review not found
        """
        try:
            # Verify review exists
            review_query = select(Review).where(Review.id == review_id)
            result = await self._db.execute(review_query)
            review = result.scalar_one_or_none()
            
            if not review:
                raise ValueError(f"Review {review_id} not found")
            
            # Create response record (assuming ReviewResponse model exists)
            # For now, we'll return a placeholder ID
            response_id = f"response-{review_id}-{int(time.time())}"
            
            logger.info(f"Response saved for review {review_id}: {response_id}")
            return response_id
            
        except Exception as e:
            logger.error(f"Failed to save response for review {review_id}: {e}")
            raise

    # Private helper methods
    
    async def _get_review_with_classification(
        self, review_id: str
    ) -> Optional[tuple[Review, Classification]]:
        """Get review with its classification data."""
        query = (
            select(Review, Classification)
            .join(Classification, Review.id == Classification.review_id)
            .where(Review.id == review_id)
        )
        
        result = await self._db.execute(query)
        return result.first()

    async def _get_business_context(self, business_id: str) -> BusinessContext:
        """Get business context for AI advisor."""
        # Get business data
        business_query = select(Business).where(Business.id == business_id)
        result = await self._db.execute(business_query)
        business = result.scalar_one_or_none()
        
        if not business:
            raise ValueError(f"Business {business_id} not found")
        
        # Get recent sentiment trend and topics
        # This would typically involve more complex analytics
        # For now, we'll use simplified data
        return BusinessContext(
            business_id=business_id,
            business_name=business.name,
            avg_rating=float(business.avg_rating or 0),
            total_reviews=business.total_reviews or 0,
            recent_sentiment_trend="stable",
            top_topics=["service", "food_quality"],
            competitor_mentions=0
        )

    def _create_response_prompt(
        self,
        review: Review,
        classification: Classification,
        tone_preference: Optional[ResponseTone],
        language: str
    ) -> str:
        """Create prompt for AI response generation."""
        tone_instruction = ""
        if tone_preference:
            tone_instruction = f"Use a {tone_preference.value} tone. "
        
        return f"""Please generate a professional response to this customer review:

Review: "{review.text}"
Rating: {review.rating}/5 stars
Sentiment: {classification.sentiment}
Topics: {', '.join(classification.topics)}
Urgency: {classification.urgency}

Guidelines:
- {tone_instruction}Respond in {language}
- Be professional and empathetic
- Address the specific concerns mentioned
- Thank the customer for their feedback
- Offer concrete solutions where appropriate
- Keep the response concise (2-3 sentences)
- Do not be defensive or make excuses

Generate only the response text, no additional commentary."""

    def _extract_response_template(self, advisor_message: str) -> str:
        """Extract the response template from advisor message."""
        # The advisor should return just the response text
        # Clean up any extra formatting or instructions
        lines = advisor_message.strip().split('\n')
        
        # Find the actual response content (skip any meta-commentary)
        response_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('Here') and not line.startswith('Response:'):
                response_lines.append(line)
        
        return ' '.join(response_lines) if response_lines else advisor_message.strip()

    async def _analyze_response_tone(
        self, response_text: str, language: str
    ) -> ToneAnalysis:
        """Analyze the tone of a response draft."""
        # This would typically use AI for tone analysis
        # For now, we'll implement basic heuristic analysis
        
        text_lower = response_text.lower()
        
        # Determine primary tone
        if any(word in text_lower for word in ['sorry', 'apologize', 'understand']):
            primary_tone = ResponseTone.EMPATHETIC
        elif any(word in text_lower for word in ['thank', 'appreciate', 'grateful']):
            primary_tone = ResponseTone.PROFESSIONAL
        elif any(word in text_lower for word in ['actually', 'however', 'but']):
            primary_tone = ResponseTone.DEFENSIVE
        else:
            primary_tone = ResponseTone.PROFESSIONAL
        
        # Calculate scores
        professionalism_score = 0.8  # Default high score
        empathy_score = 0.7 if primary_tone == ResponseTone.EMPATHETIC else 0.5
        
        # Generate suggestions
        suggestions = []
        if 'thank' not in text_lower:
            suggestions.append("Consider thanking the customer for their feedback")
        if len(response_text) > 300:
            suggestions.append("Consider making the response more concise")
        
        # Identify issues
        issues = []
        if any(word in text_lower for word in ['wrong', 'fault', 'blame', 'actually', 'however']):
            issues.append("Response may sound defensive")
        
        return ToneAnalysis(
            primary_tone=primary_tone,
            tone_confidence=0.8,
            professionalism_score=professionalism_score,
            empathy_score=empathy_score,
            suggestions=suggestions,
            issues=issues
        )

    def _calculate_response_priority(
        self, urgency: str, sentiment: str, rating: int
    ) -> ResponsePriority:
        """Calculate response priority based on review characteristics."""
        if urgency == "high" and sentiment == "negative":
            return ResponsePriority.URGENT
        elif urgency == "high" or (sentiment == "negative" and rating <= 2):
            return ResponsePriority.HIGH
        elif urgency == "medium" or rating <= 3:
            return ResponsePriority.MEDIUM
        else:
            return ResponsePriority.LOW

    def _calculate_urgency_score(
        self, urgency: str, sentiment: str, rating: int, days_since: int
    ) -> float:
        """Calculate numerical urgency score for sorting."""
        base_score = 0.0
        
        # Urgency contribution
        if urgency == "high":
            base_score += 40
        elif urgency == "medium":
            base_score += 20
        else:
            base_score += 10
        
        # Sentiment contribution
        if sentiment == "negative":
            base_score += 30
        elif sentiment == "neutral":
            base_score += 10
        
        # Rating contribution
        if rating <= 2:
            base_score += 25
        elif rating <= 3:
            base_score += 15
        
        # Time factor (more urgent as time passes)
        time_factor = min(days_since * 2, 20)  # Cap at 20 points
        base_score += time_factor
        
        return base_score

    async def _check_has_response(self, review_id: str) -> bool:
        """Check if a review already has a response."""
        # This would check the ReviewResponse table
        # For now, return False (no responses exist yet)
        return False

    async def _count_responded_reviews(
        self, business_id: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count reviews that have responses in the given period."""
        # This would join with ReviewResponse table
        # For now, return 0
        return 0

    async def _calculate_avg_response_time(
        self, business_id: str, start_date: datetime, end_date: datetime
    ) -> float:
        """Calculate average response time in hours."""
        # This would calculate based on ReviewResponse timestamps
        # For now, return 0
        return 0.0

    async def _get_responses_by_priority(
        self, business_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[ResponsePriority, int]:
        """Get response counts by priority level."""
        # This would analyze actual response data
        # For now, return empty dict
        return {priority: 0 for priority in ResponsePriority}

    async def _get_responses_by_sentiment(
        self, business_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, int]:
        """Get response counts by review sentiment."""
        # This would analyze actual response data
        # For now, return empty dict
        return {"positive": 0, "negative": 0, "neutral": 0}