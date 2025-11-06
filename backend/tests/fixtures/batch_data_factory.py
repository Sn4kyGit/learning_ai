"""
Batch data factory for creating large datasets and complete business scenarios.

This module provides factories for creating comprehensive test datasets
that include all related entities for integration and E2E testing.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
import random

from backend.db.models import (
    Business, Organization, User, Review, Classification,
    UserBusinessAccess, DailyAnalytics, AIUsageLog,
    Conversation, ConversationMessage
)
from .core_data_factory import CoreDataFactory
from .analytics_data_factory import AnalyticsDataFactory


class BatchDataFactory:
    """Factory for creating batches of test data and complete business datasets."""
    
    @staticmethod
    def create_review_batch(
        business_id: Union[str, uuid.UUID],
        count: int = 10,
        sentiment_distribution: Optional[Dict[str, float]] = None,
        date_range_days: int = 30
    ) -> List[Review]:
        """Create a batch of reviews with varied sentiments and realistic distribution."""
        if sentiment_distribution is None:
            sentiment_distribution = {"positive": 0.6, "neutral": 0.2, "negative": 0.2}
        
        reviews = []
        
        # Create reviews with proper sentiment distribution
        for i in range(count):
            # Determine sentiment based on distribution
            rand_val = random.random()
            cumulative = 0
            sentiment = "positive"  # default
            
            for sent, prob in sentiment_distribution.items():
                cumulative += prob
                if rand_val <= cumulative:
                    sentiment = sent
                    break
            
            # Create review with determined sentiment
            review = CoreDataFactory.create_review(
                business_id=business_id,
                sentiment=sentiment,
                published_at=datetime.now() - timedelta(
                    days=random.randint(0, date_range_days),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                ),
                external_id=f"batch-review-{i+1}-{uuid.uuid4().hex[:8]}"
            )
            reviews.append(review)
        
        return reviews
    
    @staticmethod
    def create_classification_batch(
        review_ids: List[Union[str, uuid.UUID]],
        match_review_sentiment: bool = True
    ) -> List[Classification]:
        """Create classifications for a batch of reviews."""
        classifications = []
        
        for review_id in review_ids:
            # Create realistic classification
            classification = CoreDataFactory.create_classification(
                review_id=review_id
            )
            classifications.append(classification)
        
        return classifications
    
    @staticmethod
    def create_complete_business_dataset(
        organization_id: Optional[Union[str, uuid.UUID]] = None,
        review_count: int = 50,
        user_count: int = 3,
        days_of_data: int = 30
    ) -> Dict[str, Any]:
        """Create a complete business dataset for integration testing."""
        # Create organization if not provided
        if organization_id is None:
            organization = CoreDataFactory.create_organization()
            organization_id = organization.id
        else:
            organization = None
        
        # Create business
        business = CoreDataFactory.create_business(organization_id=organization_id)
        
        # Create users with different roles
        users = []
        for i in range(user_count):
            role = ["admin", "viewer", "admin"][i % 3]  # Mix of roles
            user = CoreDataFactory.create_user(
                organization_id=organization_id,
                role=role
            )
            users.append(user)
        
        # Create user business access
        user_access = []
        for user in users:
            access = CoreDataFactory.create_user_business_access(
                user_id=user.id,
                business_id=business.id,
                permission_level="full_access" if user.role == "admin" else "read_only"
            )
            user_access.append(access)
        
        # Create reviews
        reviews = BatchDataFactory.create_review_batch(
            business_id=business.id,
            count=review_count,
            date_range_days=days_of_data
        )
        
        # Create classifications
        classifications = BatchDataFactory.create_classification_batch(
            [review.id for review in reviews]
        )
        
        # Create daily analytics
        daily_analytics = AnalyticsDataFactory.create_analytics_batch(
            business_id=business.id,
            days=days_of_data
        )
        
        # Create AI usage logs
        ai_logs = AnalyticsDataFactory.create_ai_usage_batch(
            business_id=business.id,
            count=review_count
        )
        
        # Create conversations
        conversations = []
        messages = []
        for user in users[:2]:  # Only admin users have conversations
            conversation = AnalyticsDataFactory.create_conversation(
                business_id=business.id,
                user_id=user.id
            )
            conversations.append(conversation)
            
            # Add some messages
            user_msg = AnalyticsDataFactory.create_conversation_message(
                conversation_id=conversation.id,
                role="user",
                content="How is my restaurant performing this week?"
            )
            messages.append(user_msg)
            
            assistant_msg = AnalyticsDataFactory.create_conversation_message(
                conversation_id=conversation.id,
                role="assistant",
                content="Based on your recent reviews, your restaurant is performing well with positive sentiment trends."
            )
            messages.append(assistant_msg)
        
        return {
            "organization": organization,
            "business": business,
            "users": users,
            "user_access": user_access,
            "reviews": reviews,
            "classifications": classifications,
            "daily_analytics": daily_analytics,
            "ai_usage_logs": ai_logs,
            "conversations": conversations,
            "conversation_messages": messages
        }
    
    @staticmethod
    def create_multi_business_dataset(
        organization_id: Optional[Union[str, uuid.UUID]] = None,
        business_count: int = 3,
        reviews_per_business: int = 30,
        users_per_business: int = 2
    ) -> Dict[str, Any]:
        """Create a multi-business dataset for testing organization-level features."""
        # Create organization if not provided
        if organization_id is None:
            organization = CoreDataFactory.create_organization()
            organization_id = organization.id
        else:
            organization = None
        
        all_businesses = []
        all_users = []
        all_reviews = []
        all_classifications = []
        all_analytics = []
        all_ai_logs = []
        all_user_access = []
        
        for i in range(business_count):
            # Create business dataset
            dataset = BatchDataFactory.create_complete_business_dataset(
                organization_id=organization_id,
                review_count=reviews_per_business,
                user_count=users_per_business,
                days_of_data=30
            )
            
            # Collect all data
            all_businesses.append(dataset["business"])
            all_users.extend(dataset["users"])
            all_reviews.extend(dataset["reviews"])
            all_classifications.extend(dataset["classifications"])
            all_analytics.extend(dataset["daily_analytics"])
            all_ai_logs.extend(dataset["ai_usage_logs"])
            all_user_access.extend(dataset["user_access"])
        
        return {
            "organization": organization,
            "businesses": all_businesses,
            "users": all_users,
            "user_access": all_user_access,
            "reviews": all_reviews,
            "classifications": all_classifications,
            "daily_analytics": all_analytics,
            "ai_usage_logs": all_ai_logs
        }
    
    @staticmethod
    def create_performance_test_dataset(
        business_id: Union[str, uuid.UUID],
        review_count: int = 500,
        days_of_data: int = 90
    ) -> Dict[str, Any]:
        """Create large dataset for performance testing."""
        # Create large batch of reviews
        reviews = BatchDataFactory.create_review_batch(
            business_id=business_id,
            count=review_count,
            date_range_days=days_of_data
        )
        
        # Create classifications for all reviews
        classifications = BatchDataFactory.create_classification_batch(
            [review.id for review in reviews]
        )
        
        # Create daily analytics for the entire period
        daily_analytics = AnalyticsDataFactory.create_analytics_batch(
            business_id=business_id,
            days=days_of_data
        )
        
        # Create AI usage logs
        ai_logs = AnalyticsDataFactory.create_ai_usage_batch(
            business_id=business_id,
            count=review_count * 2  # More logs for performance testing
        )
        
        return {
            "reviews": reviews,
            "classifications": classifications,
            "daily_analytics": daily_analytics,
            "ai_usage_logs": ai_logs
        }