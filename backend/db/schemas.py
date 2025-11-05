"""
Pydantic schemas for request/response validation.

This module defines Pydantic models for API request validation,
response serialization, and data transfer objects.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = {"from_attributes": True, "use_enum_values": True}


# Organization schemas
class OrganizationBase(BaseSchema):
    """Base organization schema."""

    name: str = Field(..., min_length=1, max_length=255)
    subscription_tier: str = Field(default="basic")
    cost_limit_monthly: Decimal = Field(default=Decimal("100.00"), ge=0)


class OrganizationCreate(OrganizationBase):
    """Schema for creating organizations."""

    pass


class OrganizationResponse(OrganizationBase):
    """Schema for organization responses."""

    id: UUID
    created_at: datetime
    updated_at: datetime


# Business schemas
class BusinessBase(BaseSchema):
    """Base business schema."""

    name: str = Field(..., min_length=1, max_length=255)
    google_place_id: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None


class BusinessCreate(BusinessBase):
    """Schema for creating businesses."""

    organization_id: Optional[UUID] = None


class BusinessUpdate(BaseSchema):
    """Schema for updating businesses."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None


class BusinessResponse(BusinessBase):
    """Schema for business responses."""

    id: UUID
    organization_id: Optional[UUID]
    avg_rating: Decimal
    total_reviews: int
    created_at: datetime
    updated_at: datetime


# User schemas
class UserBase(BaseSchema):
    """Base user schema."""

    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., pattern=r"^(super_admin|admin|viewer)$")
    language_preference: str = Field(default="en", pattern=r"^(en|de|tr|ar)$")


class UserCreate(UserBase):
    """Schema for creating users."""

    password: str = Field(..., min_length=8)
    organization_id: Optional[UUID] = None


class UserUpdate(BaseSchema):
    """Schema for updating users."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, pattern=r"^(super_admin|admin|viewer)$")
    language_preference: Optional[str] = Field(None, pattern=r"^(en|de|tr|ar)$")


class UserResponse(UserBase):
    """Schema for user responses."""

    id: UUID
    organization_id: Optional[UUID]
    created_at: datetime
    last_login: Optional[datetime]


# Review schemas
class ReviewBase(BaseSchema):
    """Base review schema."""

    author_name: Optional[str] = Field(None, max_length=255)
    rating: Optional[int] = Field(None, ge=1, le=5)
    text: str = Field(..., min_length=1)
    language: str = Field(default="en", max_length=5)
    published_at: datetime
    source: str = Field(default="google", max_length=50)


class ReviewCreate(ReviewBase):
    """Schema for creating reviews."""

    business_id: UUID
    external_id: Optional[str] = Field(None, max_length=255)


class ReviewResponse(ReviewBase):
    """Schema for review responses."""

    id: UUID
    business_id: UUID
    external_id: Optional[str]
    created_at: datetime


# Classification schemas
class ClassificationBase(BaseSchema):
    """Base classification schema."""

    sentiment: str = Field(..., pattern=r"^(positive|negative|neutral)$")
    topics: List[str] = Field(..., min_length=0)
    urgency: str = Field(..., pattern=r"^(low|medium|high)$")
    competitor_mentioned: bool = Field(default=False)
    confidence_score: Decimal = Field(..., ge=0, le=1)
    ai_model: str = Field(..., max_length=50)
    processing_time_ms: Optional[int] = Field(None, ge=0)


class ClassificationCreate(ClassificationBase):
    """Schema for creating classifications."""

    review_id: UUID


class ClassificationResponse(ClassificationBase):
    """Schema for classification responses."""

    id: UUID
    review_id: UUID
    created_at: datetime


# Analytics schemas
class DashboardMetrics(BaseSchema):
    """Schema for dashboard metrics."""

    avg_rating: Decimal
    total_reviews: int
    sentiment_distribution: Dict[str, float]
    top_topics: List[str]
    competitor_mentions: int
    response_rate: Decimal
    avg_response_time_hours: Optional[Decimal]
    trend_data: List[Dict[str, Any]]


class TrendData(BaseSchema):
    """Schema for trend analysis data."""

    date: date
    avg_rating: Decimal
    sentiment_positive: Decimal
    sentiment_neutral: Decimal
    sentiment_negative: Decimal
    review_count: int


# AI Service schemas
class ReviewClassificationRequest(BaseSchema):
    """Schema for review classification requests."""

    business_id: UUID
    reviews: List[str] = Field(..., min_length=1, max_length=500)


class ClassificationResult(BaseSchema):
    """Schema for classification results."""

    sentiment: str
    topics: List[str]
    urgency: str
    competitor_mentioned: bool
    confidence_score: Decimal
    processing_time_ms: int
    ai_model: str


class ChatRequest(BaseSchema):
    """Schema for chat requests."""

    business_id: UUID
    message: str = Field(..., min_length=1, max_length=1000)
    language: str = Field(default="en", max_length=5)


class ChatResponse(BaseSchema):
    """Schema for chat responses."""

    message: str
    language: str
    confidence_score: Decimal
    processing_time_ms: int
    ai_model: str
    cost_usd: Decimal


# Conversation schemas
class ConversationMessageCreate(BaseSchema):
    """Schema for creating conversation messages."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=5000)
    ai_model: Optional[str] = None
    processing_time_ms: Optional[int] = None
    cost_usd: Optional[Decimal] = None


class ConversationMessageResponse(BaseSchema):
    """Schema for conversation message responses."""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    ai_model: Optional[str] = None
    processing_time_ms: Optional[int] = None
    cost_usd: Optional[Decimal] = None
    created_at: datetime


class ConversationCreate(BaseSchema):
    """Schema for creating conversations."""

    business_id: UUID
    user_id: UUID
    language: str = Field(default="en", max_length=5)


class ConversationResponse(BaseSchema):
    """Schema for conversation responses."""

    id: UUID
    business_id: UUID
    user_id: UUID
    language: str
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessageResponse] = []


class WeeklyReportRequest(BaseSchema):
    """Schema for weekly report requests."""

    business_id: UUID
    language: str = Field(default="en", max_length=5)
    report_period_days: int = Field(default=7, ge=1, le=30)


class WeeklyReportResponse(BaseSchema):
    """Schema for weekly report responses."""

    business_id: UUID
    report_period_start: datetime
    report_period_end: datetime
    summary: str
    action_items: List[str]
    sentiment_analysis: str
    top_themes: List[str]
    competitor_mentions: int
    language: str
    ai_model: str


# Cost tracking schemas
class CostSummary(BaseSchema):
    """Schema for cost summary."""

    current_month_cost: Decimal
    cost_limit: Decimal
    usage_percentage: Decimal
    remaining_budget: Decimal
    classification_cost: Decimal
    chat_cost: Decimal
    report_cost: Decimal


class AIUsageLogResponse(BaseSchema):
    """Schema for AI usage log responses."""

    id: UUID
    business_id: UUID
    ai_service: str
    operation: str
    tokens_used: int
    cost_usd: Decimal
    processing_time_ms: Optional[int]
    created_at: datetime


# Report schemas (WeeklyReportRequest is defined above)


class WeeklyReportResponse(BaseSchema):
    """Schema for weekly report responses."""

    business_id: UUID
    report_period_start: datetime
    report_period_end: datetime
    summary: str
    action_items: List[str]
    sentiment_analysis: str
    top_themes: List[str]
    competitor_mentions: int
    language: str
    ai_model: str


# Authentication schemas
class LoginRequest(BaseSchema):
    """Schema for login requests."""

    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseSchema):
    """Schema for authentication token responses."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseSchema):
    """Schema for refresh token requests."""

    refresh_token: str = Field(..., min_length=1)


# Error schemas
class ErrorResponse(BaseSchema):
    """Schema for error responses."""

    detail: str
    error_code: Optional[str] = None
    errors: Optional[Dict[str, Any]] = None


# Health check schemas
class HealthCheckResponse(BaseSchema):
    """Schema for health check responses."""

    status: str
    timestamp: datetime
    version: str
    database: str
    redis: Optional[str] = None


# Additional schemas for new endpoints

# Business access schemas
class BusinessAccessCreate(BaseSchema):
    """Schema for creating business access."""
    
    user_id: UUID
    business_id: UUID
    permission_level: str = Field(..., pattern=r"^(read_only|full_access)$")


class BusinessAccessResponse(BaseSchema):
    """Schema for business access responses."""
    
    user_id: UUID
    business_id: UUID
    permission_level: str
    granted_by: UUID
    granted_at: datetime


# Notification schemas
class NotificationPreferences(BaseSchema):
    """Schema for notification preferences."""
    
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    notification_channels: List[str] = Field(default=["email", "in_app"])


class AlertThresholds(BaseSchema):
    """Schema for alert thresholds."""
    
    critical_rating_threshold: float = Field(3.5, ge=1.0, le=5.0)
    sentiment_drop_threshold: float = Field(0.2, ge=0.1, le=1.0)
    competitor_mention_alerts: bool = True
    crisis_mode_threshold: int = Field(3, ge=1, le=10)
    alert_frequency_limit: int = Field(5, ge=1, le=50)


# Report configuration schemas
class ReportConfiguration(BaseSchema):
    """Schema for report configuration."""
    
    business_id: UUID
    report_day: int = Field(..., ge=1, le=7)
    delivery_method: str = Field(..., pattern=r"^(web_only|web_and_email)$")
    language: str = Field(default="en")
    include_sections: List[str] = Field(default=["sentiment_analysis", "top_topics"])
    next_report_date: datetime
    created_at: datetime
    updated_at: datetime


# Import/Export schemas
class ImportResult(BaseSchema):
    """Schema for import operation results."""
    
    imported_count: int
    skipped_count: int
    total_processed: int
    errors: List[str] = Field(default=[])


# Budget management schemas
class BudgetStatus(BaseSchema):
    """Schema for budget status."""
    
    current_cost: Decimal
    cost_limit: Decimal
    usage_percentage: float
    remaining_budget: Decimal
    is_warning: bool
    is_exceeded: bool
    disabled_operations: List[str] = Field(default=[])


class CostBreakdown(BaseSchema):
    """Schema for detailed cost breakdown."""
    
    period: Dict[str, date]
    total_cost: Decimal
    total_tokens: int
    total_operations: int
    services: Dict[str, Dict[str, Any]]


# GDPR Compliance schemas
class ConsentRecordCreate(BaseSchema):
    """Schema for creating consent records."""
    
    consent_type: str = Field(..., pattern=r"^(data_processing|marketing|analytics|ai_processing)$")
    purpose: str = Field(..., min_length=1, max_length=500)
    granted: bool
    legal_basis: str = Field(default="consent", max_length=50)
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=500)


class ConsentRecordResponse(BaseSchema):
    """Schema for consent record responses."""
    
    id: UUID
    user_id: UUID
    consent_type: str
    purpose: str
    granted: bool
    legal_basis: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    withdrawn_at: Optional[datetime]


class DataSubjectRequestCreate(BaseSchema):
    """Schema for creating data subject requests."""
    
    request_type: str = Field(..., pattern=r"^(access|rectification|erasure|portability|restriction|objection)$")
    request_details: Optional[Dict[str, Any]] = None


class DataSubjectRequestResponse(BaseSchema):
    """Schema for data subject request responses."""
    
    id: UUID
    user_id: UUID
    request_type: str
    status: str
    request_details: Optional[Dict[str, Any]]
    response_data: Optional[Dict[str, Any]]
    requested_at: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]


class DataBreachLogCreate(BaseSchema):
    """Schema for creating data breach logs."""
    
    severity: str = Field(..., pattern=r"^(low|medium|high|critical)$")
    description: str = Field(..., min_length=1, max_length=1000)
    affected_data_types: List[str] = Field(..., min_length=1)
    affected_users_count: int = Field(..., ge=0)
    discovered_at: datetime
    contained_at: Optional[datetime] = None
    root_cause: Optional[str] = Field(None, max_length=1000)
    mitigation_steps: Optional[List[str]] = None


class DataBreachLogResponse(BaseSchema):
    """Schema for data breach log responses."""
    
    id: UUID
    breach_id: str
    severity: str
    description: str
    affected_data_types: List[str]
    affected_users_count: int
    discovered_at: datetime
    contained_at: Optional[datetime]
    root_cause: Optional[str]
    mitigation_steps: Optional[List[str]]
    authority_notified: bool
    authority_notified_at: Optional[datetime]
    users_notified: bool
    users_notified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class PrivacyNoticeResponse(BaseSchema):
    """Schema for privacy notice responses."""
    
    language: str
    last_updated: str
    version: str
    content: Dict[str, Any]


class DataMinimizationReport(BaseSchema):
    """Schema for data minimization validation reports."""
    
    business_id: UUID
    validated_at: datetime
    compliant: bool
    issues: List[str]
    recommendations: List[str]


class DataCleanupReport(BaseSchema):
    """Schema for data cleanup reports."""
    
    conversations_deleted: int
    messages_deleted: int
    old_analytics_deleted: int
    cleanup_completed_at: datetime


class DataRetentionPolicyCreate(BaseSchema):
    """Schema for creating data retention policies."""
    
    data_type: str = Field(..., min_length=1, max_length=100)
    retention_period_days: int = Field(..., ge=1)
    description: Optional[str] = Field(None, max_length=500)
    legal_basis: Optional[str] = Field(None, max_length=100)
    auto_cleanup_enabled: bool = Field(default=True)


class DataRetentionPolicyResponse(BaseSchema):
    """Schema for data retention policy responses."""
    
    id: UUID
    data_type: str
    retention_period_days: int
    description: Optional[str]
    legal_basis: Optional[str]
    auto_cleanup_enabled: bool
    created_at: datetime
    updated_at: datetime
