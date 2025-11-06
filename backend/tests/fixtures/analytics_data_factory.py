"""
Analytics and AI data factory for creating test data related to analytics and AI operations.

This module provides factories for creating analytics, AI usage logs, conversations,
and other data related to business intelligence and AI operations.
"""

import uuid
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union
import random

from backend.db.models import (
    DailyAnalytics, AIUsageLog, MonthlyCostSummary,
    Conversation, ConversationMessage, ReviewResponse
)


class AnalyticsDataFactory:
    """Factory for creating analytics and AI-related test data."""
    
    TOPICS = [
        "food_quality", "service", "ambiance", "cleanliness", "value",
        "wait_time", "staff_behavior", "portion_size", "taste", "presentation"
    ]
    
    @staticmethod
    def create_daily_analytics(
        business_id: Union[str, uuid.UUID],
        date: Optional[date] = None,
        **kwargs
    ) -> DailyAnalytics:
        """Create daily analytics with realistic data."""
        if date is None:
            date = datetime.now().date() - timedelta(days=random.randint(0, 30))
        
        # Generate realistic analytics data
        review_count = random.randint(0, 20)
        avg_rating = Decimal(str(round(random.uniform(3.0, 5.0), 2)))
        
        # Sentiment distribution
        positive_pct = round(random.uniform(40, 80), 2)
        negative_pct = round(random.uniform(5, 25), 2)
        neutral_pct = round(100 - positive_pct - negative_pct, 2)
        
        return DailyAnalytics(
            business_id=business_id,
            date=date,
            avg_rating=avg_rating,
            sentiment_positive=Decimal(str(positive_pct)),
            sentiment_neutral=Decimal(str(neutral_pct)),
            sentiment_negative=Decimal(str(negative_pct)),
            review_count=review_count,
            top_topics=random.sample(AnalyticsDataFactory.TOPICS, random.randint(2, 5)),
            competitor_mentions=random.randint(0, 3),
            response_rate=Decimal(str(round(random.uniform(0, 100), 2))),
            avg_response_time_hours=Decimal(str(round(random.uniform(1, 48), 2))),
            **kwargs
        )
    
    @staticmethod
    def create_ai_usage_log(
        business_id: Union[str, uuid.UUID],
        ai_service: str = "gpt-5-nano",
        operation: str = "classify",
        **kwargs
    ) -> AIUsageLog:
        """Create AI usage log entry."""
        # Realistic token usage and costs
        token_costs = {
            "gpt-5-nano": {"classify": (50, 0.0001), "chat": (200, 0.0004)},
            "claude-haiku": {"chat": (150, 0.0003), "report": (500, 0.001)}
        }
        
        tokens, base_cost = token_costs.get(ai_service, {}).get(operation, (100, 0.0002))
        tokens_used = random.randint(int(tokens * 0.5), int(tokens * 1.5))
        cost_usd = Decimal(str(round(base_cost * (tokens_used / tokens), 6)))
        
        return AIUsageLog(
            business_id=business_id,
            ai_service=ai_service,
            operation=operation,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            processing_time_ms=random.randint(100, 2000),
            **kwargs
        )
    
    @staticmethod
    def create_monthly_cost_summary(
        organization_id: Union[str, uuid.UUID],
        month: Optional[date] = None,
        **kwargs
    ) -> MonthlyCostSummary:
        """Create monthly cost summary with realistic data."""
        if month is None:
            month = datetime.now().date().replace(day=1)
        
        # Generate realistic cost data
        total_cost = Decimal(str(round(random.uniform(50, 500), 2)))
        gpt_cost = Decimal(str(round(total_cost * random.uniform(0.4, 0.7), 2)))
        claude_cost = total_cost - gpt_cost
        
        return MonthlyCostSummary(
            organization_id=organization_id,
            month=month,
            total_cost_usd=total_cost,
            gpt_cost_usd=gpt_cost,
            claude_cost_usd=claude_cost,
            total_tokens=random.randint(10000, 100000),
            total_requests=random.randint(500, 5000),
            **kwargs
        )
    
    @staticmethod
    def create_conversation(
        business_id: Union[str, uuid.UUID],
        user_id: Union[str, uuid.UUID],
        language: str = "en",
        **kwargs
    ) -> Conversation:
        """Create conversation."""
        return Conversation(
            business_id=business_id,
            user_id=user_id,
            language=language,
            **kwargs
        )
    
    @staticmethod
    def create_conversation_message(
        conversation_id: Union[str, uuid.UUID],
        role: str,
        content: str,
        ai_model: Optional[str] = None,
        **kwargs
    ) -> ConversationMessage:
        """Create conversation message."""
        processing_time_ms = None
        cost_usd = None
        
        if role == "assistant":
            ai_model = ai_model or "claude-haiku"
            processing_time_ms = random.randint(500, 3000)
            cost_usd = Decimal(str(round(random.uniform(0.001, 0.01), 6)))
        
        return ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            ai_model=ai_model,
            processing_time_ms=processing_time_ms,
            cost_usd=cost_usd,
            **kwargs
        )
    
    @staticmethod
    def create_review_response(
        review_id: Union[str, uuid.UUID],
        business_id: Union[str, uuid.UUID],
        response_text: Optional[str] = None,
        **kwargs
    ) -> ReviewResponse:
        """Create review response with realistic data."""
        if response_text is None:
            responses = [
                "Thank you for your feedback! We appreciate your business.",
                "We're glad you enjoyed your experience with us!",
                "Thank you for taking the time to leave a review.",
                "We appreciate your kind words and look forward to serving you again.",
                "Thanks for the feedback. We'll work to improve your experience next time."
            ]
            response_text = random.choice(responses)
        
        return ReviewResponse(
            review_id=review_id,
            business_id=business_id,
            response_text=response_text,
            **kwargs
        )
    
    @staticmethod
    def create_analytics_batch(
        business_id: Union[str, uuid.UUID],
        days: int = 30
    ) -> List[DailyAnalytics]:
        """Create a batch of daily analytics for a date range."""
        analytics = []
        
        for i in range(days):
            analytics_date = datetime.now().date() - timedelta(days=i)
            daily_analytics = AnalyticsDataFactory.create_daily_analytics(
                business_id=business_id,
                date=analytics_date
            )
            analytics.append(daily_analytics)
        
        return analytics
    
    @staticmethod
    def create_ai_usage_batch(
        business_id: Union[str, uuid.UUID],
        count: int = 50,
        service_distribution: Optional[Dict[str, float]] = None
    ) -> List[AIUsageLog]:
        """Create a batch of AI usage logs with realistic distribution."""
        if service_distribution is None:
            service_distribution = {
                "gpt-5-nano": 0.7,
                "claude-haiku": 0.3
            }
        
        logs = []
        
        for _ in range(count):
            # Determine service based on distribution
            rand_val = random.random()
            cumulative = 0
            service = "gpt-5-nano"  # default
            
            for svc, prob in service_distribution.items():
                cumulative += prob
                if rand_val <= cumulative:
                    service = svc
                    break
            
            # Determine operation based on service
            if service == "gpt-5-nano":
                operation = random.choice(["classify", "chat"])
            else:  # claude-haiku
                operation = random.choice(["chat", "report"])
            
            log = AnalyticsDataFactory.create_ai_usage_log(
                business_id=business_id,
                ai_service=service,
                operation=operation
            )
            logs.append(log)
        
        return logs