"""
SQLAlchemy models for Local Business Intelligence Bot.

This module defines all database models including Business, Review,
Classification, User, and related entities.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Date,
    Text,
    ForeignKey,
    DECIMAL,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.db.database import Base


class Organization(Base):
    """Organization model for multi-tenant support."""

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    subscription_tier = Column(String(50), nullable=False, default="basic")
    cost_limit_monthly = Column(DECIMAL(10, 2), nullable=False, default=100.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    businesses = relationship("Business", back_populates="organization")
    users = relationship("User", back_populates="organization")


class Business(Base):
    """Business model representing a restaurant or local business."""

    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    name = Column(String(255), nullable=False)
    google_place_id = Column(String(255), unique=True, nullable=False)
    category = Column(String(100))
    address = Column(Text)
    avg_rating = Column(DECIMAL(3, 2), default=0.0)
    total_reviews = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    organization = relationship("Organization", back_populates="businesses")
    reviews = relationship("Review", back_populates="business")
    daily_analytics = relationship("DailyAnalytics", back_populates="business")
    ai_usage_logs = relationship("AIUsageLog", back_populates="business")
    monthly_cost_summaries = relationship(
        "MonthlyCostSummary", back_populates="business"
    )
    user_access = relationship("UserBusinessAccess", back_populates="business")
    conversations = relationship("Conversation", back_populates="business")


class User(Base):
    """User model with role-based access control."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # super_admin, admin, viewer
    language_preference = Column(String(5), default="en")
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    organization = relationship("Organization", back_populates="users")
    business_access = relationship(
        "UserBusinessAccess", 
        back_populates="user",
        foreign_keys="UserBusinessAccess.user_id"
    )
    conversations = relationship("Conversation", back_populates="user")

    # Constraints
    __table_args__ = (Index("idx_users_email", "email"),)


class UserBusinessAccess(Base):
    """Many-to-many relationship between users and businesses with permissions."""

    __tablename__ = "user_business_access"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    business_id = Column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), primary_key=True
    )
    permission_level = Column(String(50), nullable=False)  # full_access, read_only
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    granted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship(
        "User", back_populates="business_access", foreign_keys=[user_id]
    )
    business = relationship("Business", back_populates="user_access")
    granted_by_user = relationship("User", foreign_keys=[granted_by])


class Review(Base):
    """Review model for customer feedback data."""

    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    author_name = Column(String(255))
    rating = Column(Integer)  # 1-5 stars
    text = Column(Text, nullable=False)
    language = Column(String(5), default="en")
    published_at = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50), nullable=False, default="google")
    external_id = Column(String(255))  # For deduplication
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    business = relationship("Business", back_populates="reviews")
    classifications = relationship("Classification", back_populates="review")
    responses = relationship("ReviewResponse", back_populates="review")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "business_id", "external_id", "source", name="uq_review_external"
        ),
        Index("idx_reviews_business_id", "business_id"),
        Index("idx_reviews_published_at", "published_at"),
    )


class Classification(Base):
    """Classification results from AI analysis of reviews."""

    __tablename__ = "classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    sentiment = Column(String(20), nullable=False)  # positive, negative, neutral
    topics = Column(JSON, nullable=False)  # Array of topic strings stored as JSON
    urgency = Column(String(20), nullable=False)  # low, medium, high
    competitor_mentioned = Column(Boolean, default=False)
    confidence_score = Column(DECIMAL(4, 3), nullable=False)
    ai_model = Column(String(50), nullable=False)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    review = relationship("Review", back_populates="classifications")

    # Constraints
    __table_args__ = (
        Index("idx_classifications_review_id", "review_id"),
        Index("idx_classifications_urgency", "urgency"),
    )


class DailyAnalytics(Base):
    """Daily analytics aggregation for businesses."""

    __tablename__ = "daily_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    date = Column(Date, nullable=False)
    avg_rating = Column(DECIMAL(3, 2))
    sentiment_positive = Column(DECIMAL(5, 2))
    sentiment_neutral = Column(DECIMAL(5, 2))
    sentiment_negative = Column(DECIMAL(5, 2))
    review_count = Column(Integer, default=0)
    top_topics = Column(JSON)  # Array of topic strings stored as JSON
    competitor_mentions = Column(Integer, default=0)
    response_rate = Column(DECIMAL(5, 2), default=0.0)
    avg_response_time_hours = Column(DECIMAL(8, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    business = relationship("Business", back_populates="daily_analytics")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "business_id", "date", name="uq_daily_analytics_business_date"
        ),
        Index("idx_daily_analytics_business_date", "business_id", "date"),
    )


class AIUsageLog(Base):
    """Log of AI service usage for cost tracking."""

    __tablename__ = "ai_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    ai_service = Column(String(50), nullable=False)  # gpt5_nano, claude_haiku
    operation = Column(String(50), nullable=False)  # classify, chat, report
    tokens_used = Column(Integer, nullable=False)
    cost_usd = Column(DECIMAL(10, 6), nullable=False)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    business = relationship("Business", back_populates="ai_usage_logs")

    # Constraints
    __table_args__ = (
        Index("idx_ai_usage_logs_business_created", "business_id", "created_at"),
    )


class MonthlyCostSummary(Base):
    """Monthly cost summary for businesses."""

    __tablename__ = "monthly_cost_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    month = Column(Date, nullable=False)  # First day of month
    classification_cost = Column(DECIMAL(10, 2), default=0.0)
    chat_cost = Column(DECIMAL(10, 2), default=0.0)
    report_cost = Column(DECIMAL(10, 2), default=0.0)
    total_cost = Column(DECIMAL(10, 2), default=0.0)
    cost_limit = Column(DECIMAL(10, 2), nullable=False)
    usage_percentage = Column(DECIMAL(5, 2), default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    business = relationship("Business", back_populates="monthly_cost_summaries")

    # Constraints
    __table_args__ = (
        UniqueConstraint("business_id", "month", name="uq_monthly_cost_business_month"),
    )


class Conversation(Base):
    """Conversation model for chat history tracking."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    language = Column(String(5), nullable=False, default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    business = relationship("Business")
    user = relationship("User")
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        Index("idx_conversations_business_user", "business_id", "user_id"),
        Index("idx_conversations_updated", "updated_at"),
    )


class ConversationMessage(Base):
    """Individual messages within a conversation."""

    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    ai_model = Column(String(50))  # Only for assistant messages
    processing_time_ms = Column(Integer)  # Only for assistant messages
    cost_usd = Column(DECIMAL(10, 6))  # Only for assistant messages
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Constraints
    __table_args__ = (
        Index("idx_conversation_messages_conversation", "conversation_id"),
        Index("idx_conversation_messages_created", "created_at"),
    )


class ReviewResponse(Base):
    """Review responses created by restaurant owners."""

    __tablename__ = "review_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime(timezone=True))
    ai_generated = Column(Boolean, default=False)
    ai_model = Column(String(50))  # Model used for generation if AI-generated
    tone_analysis = Column(JSON)  # Tone analysis results stored as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    review = relationship("Review", back_populates="responses")
    user = relationship("User")

    # Constraints
    __table_args__ = (
        Index("idx_review_responses_review", "review_id"),
        Index("idx_review_responses_user", "user_id"),
        Index("idx_review_responses_published", "published_at"),
    )


class ConsentRecord(Base):
    """GDPR consent records for data processing activities."""

    __tablename__ = "consent_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    consent_type = Column(String(50), nullable=False)  # data_processing, marketing, etc.
    purpose = Column(Text, nullable=False)
    granted = Column(Boolean, nullable=False)
    legal_basis = Column(String(50), nullable=False, default="consent")
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    withdrawn_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User")

    # Constraints
    __table_args__ = (
        Index("idx_consent_records_user", "user_id"),
        Index("idx_consent_records_type", "consent_type"),
        Index("idx_consent_records_created", "created_at"),
    )


class DataSubjectRequest(Base):
    """GDPR data subject rights requests."""

    __tablename__ = "data_subject_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    request_type = Column(String(50), nullable=False)  # access, erasure, portability, etc.
    status = Column(String(50), nullable=False, default="pending")  # pending, processing, completed, rejected
    request_details = Column(JSON)  # Additional request details
    response_data = Column(JSON)  # Response data for the request
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    notes = Column(Text)

    # Relationships
    user = relationship("User")

    # Constraints
    __table_args__ = (
        Index("idx_data_subject_requests_user", "user_id"),
        Index("idx_data_subject_requests_type", "request_type"),
        Index("idx_data_subject_requests_status", "status"),
        Index("idx_data_subject_requests_requested", "requested_at"),
    )


class DataBreachLog(Base):
    """GDPR data breach incident log."""

    __tablename__ = "data_breach_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    breach_id = Column(String(100), unique=True, nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    description = Column(Text, nullable=False)
    affected_data_types = Column(JSON, nullable=False)  # Array of data types
    affected_users_count = Column(Integer, nullable=False)
    discovered_at = Column(DateTime(timezone=True), nullable=False)
    contained_at = Column(DateTime(timezone=True))
    root_cause = Column(Text)
    mitigation_steps = Column(JSON)  # Array of mitigation steps
    authority_notified = Column(Boolean, default=False)
    authority_notified_at = Column(DateTime(timezone=True))
    users_notified = Column(Boolean, default=False)
    users_notified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Constraints
    __table_args__ = (
        Index("idx_data_breach_logs_breach_id", "breach_id"),
        Index("idx_data_breach_logs_severity", "severity"),
        Index("idx_data_breach_logs_discovered", "discovered_at"),
    )


class DataRetentionPolicy(Base):
    """Data retention policies for different data types."""

    __tablename__ = "data_retention_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_type = Column(String(100), nullable=False, unique=True)
    retention_period_days = Column(Integer, nullable=False)
    description = Column(Text)
    legal_basis = Column(String(100))
    auto_cleanup_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Constraints
    __table_args__ = (
        Index("idx_data_retention_policies_type", "data_type"),
    )
