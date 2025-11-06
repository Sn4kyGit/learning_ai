"""
Core data factory for creating basic test data objects.

This module provides factories for creating core business entities
like organizations, businesses, users, and reviews with realistic values.
"""

import uuid
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union
import random
import string

from backend.db.models import (
    Business, Organization, User, Review, Classification,
    UserBusinessAccess, DailyAnalytics, AIUsageLog
)


class CoreDataFactory:
    """Factory for creating core test data objects with realistic values."""
    
    # Sample data for realistic test objects
    RESTAURANT_NAMES = [
        "The Golden Fork", "Bella Vista", "Ocean Breeze Cafe", "Mountain View Bistro",
        "Urban Kitchen", "Sunset Grill", "The Cozy Corner", "Spice Garden",
        "Harbor Light Restaurant", "The Green Table"
    ]
    
    RESTAURANT_CATEGORIES = [
        "restaurant", "cafe", "fast_food", "fine_dining", "bakery",
        "pizza", "asian", "italian", "mexican", "american"
    ]
    
    REVIEW_TEXTS = {
        "positive": [
            "Excellent food and outstanding service! Highly recommend.",
            "Amazing atmosphere and delicious meals. Will definitely return.",
            "Best restaurant in town! Fresh ingredients and friendly staff.",
            "Perfect dining experience. Great value for money.",
            "Wonderful food quality and quick service. Love this place!"
        ],
        "negative": [
            "Food was cold and service was extremely slow.",
            "Poor quality ingredients and overpriced meals.",
            "Terrible experience. Staff was rude and unprofessional.",
            "Long wait times and disappointing food quality.",
            "Not worth the money. Better options available elsewhere."
        ],
        "neutral": [
            "Average food quality, nothing special but decent.",
            "Standard restaurant experience. Food was okay.",
            "Reasonable prices but could improve on service.",
            "Good location but food could be better.",
            "Decent meal, would consider returning."
        ]
    }
    
    TOPICS = [
        "food_quality", "service", "ambiance", "cleanliness", "value",
        "wait_time", "staff_behavior", "portion_size", "taste", "presentation"
    ]
    
    USER_ROLES = ["super_admin", "admin", "viewer"]
    PERMISSION_LEVELS = ["full_access", "read_only"]
    
    @staticmethod
    def create_organization(
        name: Optional[str] = None,
        subscription_tier: str = "premium",
        cost_limit_monthly: Optional[Decimal] = None,
        **kwargs
    ) -> Organization:
        """Create test organization with realistic data."""
        if name is None:
            name = f"{random.choice(['Global', 'Metro', 'Elite', 'Prime'])} Restaurant Group"
        
        if cost_limit_monthly is None:
            cost_limit_monthly = Decimal(str(random.choice([100, 200, 500, 1000])))
        
        return Organization(
            name=name,
            subscription_tier=subscription_tier,
            cost_limit_monthly=cost_limit_monthly,
            **kwargs
        )
    
    @staticmethod
    def create_business(
        name: Optional[str] = None,
        google_place_id: Optional[str] = None,
        organization_id: Optional[Union[str, uuid.UUID]] = None,
        category: Optional[str] = None,
        address: Optional[str] = None,
        avg_rating: Optional[float] = None,
        total_reviews: Optional[int] = None,
        **kwargs
    ) -> Business:
        """Create test business with realistic data."""
        if name is None:
            name = random.choice(CoreDataFactory.RESTAURANT_NAMES)
        
        if category is None:
            category = random.choice(CoreDataFactory.RESTAURANT_CATEGORIES)
        
        if address is None:
            street_num = random.randint(100, 9999)
            street_names = ["Main St", "Oak Ave", "First St", "Park Blvd", "Center Dr"]
            cities = ["Springfield", "Riverside", "Franklin", "Georgetown", "Madison"]
            address = f"{street_num} {random.choice(street_names)}, {random.choice(cities)}"
        
        if avg_rating is None:
            avg_rating = round(random.uniform(3.0, 5.0), 1)
        
        if total_reviews is None:
            total_reviews = random.randint(10, 500)
        
        return Business(
            name=name,
            google_place_id=google_place_id or f"test-place-{uuid.uuid4().hex[:8]}",
            organization_id=organization_id,
            category=category,
            address=address,
            avg_rating=avg_rating,
            total_reviews=total_reviews,
            **kwargs
        )
    
    @staticmethod
    def create_user(
        email: Optional[str] = None,
        name: Optional[str] = None,
        role: Optional[str] = None,
        language_preference: str = "en",
        organization_id: Optional[Union[str, uuid.UUID]] = None,
        password_hash: str = "hashed_password",
        **kwargs
    ) -> User:
        """Create test user with realistic data."""
        if email is None:
            username = ''.join(random.choices(string.ascii_lowercase, k=8))
            email = f"{username}@example.com"
        
        if name is None:
            first_names = ["John", "Jane", "Mike", "Sarah", "David", "Lisa", "Tom", "Emma"]
            last_names = ["Smith", "Johnson", "Brown", "Davis", "Wilson", "Miller", "Taylor"]
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        if role is None:
            role = random.choice(CoreDataFactory.USER_ROLES)
        
        return User(
            email=email,
            name=name,
            role=role,
            language_preference=language_preference,
            organization_id=organization_id,
            password_hash=password_hash,
            **kwargs
        )
    
    @staticmethod
    def create_review(
        business_id: Union[str, uuid.UUID],
        author_name: Optional[str] = None,
        rating: Optional[int] = None,
        text: Optional[str] = None,
        language: str = "en",
        published_at: Optional[datetime] = None,
        source: str = "google",
        external_id: Optional[str] = None,
        sentiment: Optional[str] = None,
        **kwargs
    ) -> Review:
        """Create test review with realistic data."""
        if author_name is None:
            first_names = ["Alex", "Jordan", "Casey", "Taylor", "Morgan", "Riley"]
            last_names = ["Anderson", "Thompson", "Garcia", "Martinez", "Robinson"]
            author_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        # Determine sentiment and corresponding rating/text
        if sentiment is None:
            sentiment = random.choices(
                ["positive", "negative", "neutral"],
                weights=[0.6, 0.2, 0.2]
            )[0]
        
        if rating is None:
            if sentiment == "positive":
                rating = random.choice([4, 5])
            elif sentiment == "negative":
                rating = random.choice([1, 2])
            else:
                rating = 3
        
        if text is None:
            text = random.choice(CoreDataFactory.REVIEW_TEXTS[sentiment])
        
        if published_at is None:
            # Random date within last 90 days
            days_ago = random.randint(0, 90)
            published_at = datetime.now() - timedelta(days=days_ago)
        
        return Review(
            business_id=business_id,
            author_name=author_name,
            rating=rating,
            text=text,
            language=language,
            published_at=published_at,
            source=source,
            external_id=external_id or f"review-{uuid.uuid4().hex[:8]}",
            **kwargs
        )
    
    @staticmethod
    def create_classification(
        review_id: Union[str, uuid.UUID],
        sentiment: Optional[str] = None,
        topics: Optional[List[str]] = None,
        urgency: Optional[str] = None,
        competitor_mentioned: Optional[bool] = None,
        confidence_score: Optional[Decimal] = None,
        ai_model: str = "gpt-5-nano",
        processing_time_ms: Optional[int] = None,
        **kwargs
    ) -> Classification:
        """Create test classification with realistic data."""
        if sentiment is None:
            sentiment = random.choices(
                ["positive", "negative", "neutral"],
                weights=[0.6, 0.2, 0.2]
            )[0]
        
        if topics is None:
            # Select 1-3 random topics
            topic_count = random.randint(1, 3)
            topics = random.sample(CoreDataFactory.TOPICS, topic_count)
        
        if urgency is None:
            if sentiment == "negative":
                urgency = random.choices(["high", "medium", "low"], weights=[0.4, 0.4, 0.2])[0]
            else:
                urgency = random.choices(["high", "medium", "low"], weights=[0.1, 0.3, 0.6])[0]
        
        if competitor_mentioned is None:
            competitor_mentioned = random.choice([True, False]) if random.random() < 0.1 else False
        
        if confidence_score is None:
            confidence_score = Decimal(str(round(random.uniform(0.75, 0.99), 3)))
        
        if processing_time_ms is None:
            processing_time_ms = random.randint(50, 300)
        
        return Classification(
            review_id=review_id,
            sentiment=sentiment,
            topics=topics,
            urgency=urgency,
            competitor_mentioned=competitor_mentioned,
            confidence_score=confidence_score,
            ai_model=ai_model,
            processing_time_ms=processing_time_ms,
            **kwargs
        )
    
    @staticmethod
    def create_user_business_access(
        user_id: Union[str, uuid.UUID],
        business_id: Union[str, uuid.UUID],
        permission_level: Optional[str] = None,
        granted_by: Optional[Union[str, uuid.UUID]] = None,
        **kwargs
    ) -> UserBusinessAccess:
        """Create user business access relationship."""
        if permission_level is None:
            permission_level = random.choice(CoreDataFactory.PERMISSION_LEVELS)
        
        return UserBusinessAccess(
            user_id=user_id,
            business_id=business_id,
            permission_level=permission_level,
            granted_by=granted_by,
            **kwargs
        )