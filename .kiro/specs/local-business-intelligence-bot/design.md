# Design Document

## Overview

The Local Business Intelligence Bot is designed as a scalable, multi-tenant SaaS platform that leverages a dual-agent AI architecture to provide restaurant owners with actionable insights from customer reviews. The system combines fast, cost-effective review classification with strategic business advisory capabilities, all while maintaining GDPR compliance and supporting multiple languages.

### Key Design Principles

- **Dual-Agent Architecture**: Separate AI agents optimized for different tasks (classification vs. advisory)
- **Multi-Tenant Support**: Role-based access control with organization-level grouping
- **Cost Optimization**: Intelligent batching and caching to minimize AI API costs
- **Real-time Responsiveness**: Event-driven architecture for immediate alerts and updates
- **Scalability**: Microservice-inspired layered architecture supporting horizontal scaling
- **Compliance-First**: GDPR compliance built into data handling from the ground up

## Architecture

### High-Level System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Vue.js SPA]
        PWA[Progressive Web App]
    end
    
    subgraph "API Gateway Layer"
        API[FastAPI Gateway]
        Auth[Authentication Middleware]
        RateLimit[Rate Limiting]
    end
    
    subgraph "Business Logic Layer"
        ReviewSvc[Review Service]
        AnalyticsSvc[Analytics Service]
        NotificationSvc[Notification Service]
        UserSvc[User Management Service]
        ReportSvc[Report Service]
    end
    
    subgraph "AI Services Layer"
        GPT5[GPT-5 Nano Classifier]
        Claude[Claude Haiku Advisor]
        LangDetect[Language Detector]
        CostTracker[Cost Tracking]
    end
    
    subgraph "Data Layer"
        PostgresDB[(PostgreSQL)]
        Redis[(Redis Cache)]
        BackupStorage[(Backup Storage)]
    end
    
    subgraph "External Services"
        GoogleAPI[Google Places API]
        EmailSvc[Email Service]
        SMSSvc[SMS Service]
    end
    
    UI --> API
    API --> Auth
    API --> RateLimit
    API --> ReviewSvc
    API --> AnalyticsSvc
    API --> NotificationSvc
    API --> UserSvc
    API --> ReportSvc
    
    ReviewSvc --> GPT5
    ReviewSvc --> LangDetect
    AnalyticsSvc --> Claude
    NotificationSvc --> EmailSvc
    NotificationSvc --> SMSSvc
    
    ReviewSvc --> PostgresDB
    AnalyticsSvc --> PostgresDB
    AnalyticsSvc --> Redis
    UserSvc --> PostgresDB
    
    ReviewSvc --> GoogleAPI
    GPT5 --> CostTracker
    Claude --> CostTracker
    
    PostgresDB --> BackupStorage
```

### Deployment Architecture

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx/Cloudflare]
    end
    
    subgraph "Application Tier"
        App1[FastAPI Instance 1]
        App2[FastAPI Instance 2]
        App3[FastAPI Instance N]
    end
    
    subgraph "Background Workers"
        Worker1[Review Processor]
        Worker2[Report Generator]
        Worker3[Alert Handler]
        Scheduler[Cron Scheduler]
    end
    
    subgraph "Data Tier"
        PrimaryDB[(PostgreSQL Primary)]
        ReadReplica[(PostgreSQL Read Replica)]
        RedisCluster[(Redis Cluster)]
    end
    
    subgraph "External Services"
        AI_APIs[OpenAI/Anthropic APIs]
        Google[Google Places API]
        Email[Email Provider]
    end
    
    LB --> App1
    LB --> App2
    LB --> App3
    
    App1 --> PrimaryDB
    App2 --> ReadReplica
    App3 --> RedisCluster
    
    Worker1 --> AI_APIs
    Worker2 --> Email
    Worker3 --> Email
    
    Scheduler --> Worker1
    Scheduler --> Worker2
```

## Components and Interfaces

### Core Service Interfaces

```python
# AI Service Interfaces
class ReviewClassifierProtocol(Protocol):
    async def classify_review(
        self, 
        text: str, 
        language: str = "en"
    ) -> ClassificationResult:
        """Classify a single review for sentiment, topics, and urgency."""
        ...
    
    async def classify_batch(
        self, 
        reviews: List[ReviewText]
    ) -> List[ClassificationResult]:
        """Classify multiple reviews in a single API call for cost efficiency."""
        ...

class BusinessAdvisorProtocol(Protocol):
    async def generate_response(
        self, 
        message: str, 
        context: BusinessContext,
        language: str = "en"
    ) -> AdvisorResponse:
        """Generate contextual business advice based on review data."""
        ...
    
    async def generate_report(
        self, 
        business_data: BusinessAnalytics,
        language: str = "en"
    ) -> WeeklyReport:
        """Generate comprehensive weekly business report."""
        ...

# Repository Interfaces
class ReviewRepositoryProtocol(Protocol):
    async def save_review(self, review: Review) -> Review:
        """Save a new review to the database."""
        ...
    
    async def get_reviews_by_business(
        self, 
        business_id: str,
        filters: ReviewFilters = None
    ) -> List[Review]:
        """Retrieve reviews for a specific business with optional filtering."""
        ...
    
    async def get_unprocessed_reviews(self) -> List[Review]:
        """Get all reviews that haven't been classified yet."""
        ...

class BusinessRepositoryProtocol(Protocol):
    async def create_business(self, business: BusinessCreate) -> Business:
        """Create a new business entity."""
        ...
    
    async def get_businesses_by_user(
        self, 
        user_id: str,
        permissions: UserPermissions
    ) -> List[Business]:
        """Get businesses accessible to a user based on their role."""
        ...
```

### Service Layer Components

#### Review Processing Service
```python
class ReviewProcessingService:
    """Orchestrates the complete review processing pipeline."""
    
    def __init__(
        self,
        classifier: ReviewClassifierProtocol,
        language_detector: LanguageDetector,
        repository: ReviewRepositoryProtocol,
        cost_tracker: CostTracker,
        alert_service: AlertService
    ):
        self._classifier = classifier
        self._language_detector = language_detector
        self._repository = repository
        self._cost_tracker = cost_tracker
        self._alert_service = alert_service
    
    async def process_new_reviews(self, business_id: str) -> ProcessingResult:
        """Process all new reviews for a business through the complete pipeline."""
        # 1. Get unprocessed reviews
        # 2. Detect languages
        # 3. Batch classify reviews
        # 4. Save classifications
        # 5. Check for alerts
        # 6. Update analytics
        pass
```

#### Analytics Service
```python
class AnalyticsService:
    """Handles business intelligence calculations and dashboard data."""
    
    def __init__(
        self,
        repository: AnalyticsRepositoryProtocol,
        cache: CacheService,
        advisor: BusinessAdvisorProtocol
    ):
        self._repository = repository
        self._cache = cache
        self._advisor = advisor
    
    async def get_dashboard_data(
        self, 
        business_id: str,
        user_permissions: UserPermissions
    ) -> DashboardData:
        """Get comprehensive dashboard data with caching."""
        # 1. Check cache first
        # 2. Calculate metrics if not cached
        # 3. Apply user permission filters
        # 4. Cache results
        pass
    
    async def calculate_trends(
        self, 
        business_id: str, 
        period: TimePeriod
    ) -> TrendAnalysis:
        """Calculate sentiment and topic trends over time."""
        pass
```

#### Notification Service
```python
class NotificationService:
    """Handles real-time alerts and notifications."""
    
    def __init__(
        self,
        email_service: EmailService,
        sms_service: SMSService,
        push_service: PushNotificationService
    ):
        self._email = email_service
        self._sms = sms_service
        self._push = push_service
    
    async def send_critical_alert(
        self, 
        alert: CriticalAlert,
        recipients: List[NotificationRecipient]
    ) -> NotificationResult:
        """Send immediate alerts for critical reviews."""
        # 1. Determine notification channels per recipient
        # 2. Format messages for each channel
        # 3. Send notifications concurrently
        # 4. Track delivery status
        pass
```

### Multi-Tenant User Management

```python
class UserManagementService:
    """Handles authentication, authorization, and role-based access."""
    
    def __init__(
        self,
        user_repository: UserRepositoryProtocol,
        auth_provider: AuthenticationProvider,
        permission_engine: PermissionEngine
    ):
        self._user_repo = user_repository
        self._auth = auth_provider
        self._permissions = permission_engine
    
    async def authenticate_user(self, credentials: UserCredentials) -> AuthResult:
        """Authenticate user and return access tokens."""
        pass
    
    async def check_business_access(
        self, 
        user_id: str, 
        business_id: str,
        required_permission: Permission
    ) -> bool:
        """Check if user has required permission for a business."""
        pass
    
    async def get_user_businesses(
        self, 
        user_id: str
    ) -> List[BusinessAccess]:
        """Get all businesses accessible to a user with their permission levels."""
        pass
```

## Data Models

### Core Entity Models

```python
# Business Domain Models
@dataclass
class Business:
    id: str
    name: str
    google_place_id: str
    category: str
    address: str
    organization_id: Optional[str]
    avg_rating: float
    total_reviews: int
    created_at: datetime
    updated_at: datetime

@dataclass
class Review:
    id: str
    business_id: str
    author_name: str
    rating: int
    text: str
    language: str
    published_at: datetime
    source: str  # google, yelp, manual
    created_at: datetime

@dataclass
class Classification:
    id: str
    review_id: str
    sentiment: str  # positive, negative, neutral
    topics: List[str]  # food_quality, service, ambiance, price, cleanliness
    urgency: str  # low, medium, high
    competitor_mentioned: bool
    confidence_score: float
    ai_model: str
    processing_time_ms: int
    created_at: datetime

# User Management Models
@dataclass
class User:
    id: str
    email: str
    name: str
    role: UserRole  # super_admin, admin, viewer
    language_preference: str
    organization_id: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]

@dataclass
class Organization:
    id: str
    name: str
    subscription_tier: str
    cost_limit_monthly: Decimal
    created_at: datetime

@dataclass
class UserBusinessAccess:
    user_id: str
    business_id: str
    permission_level: str  # full_access, read_only
    granted_by: str
    granted_at: datetime

# Analytics Models
@dataclass
class DashboardMetrics:
    business_id: str
    date: date
    avg_rating: float
    sentiment_positive: float
    sentiment_neutral: float
    sentiment_negative: float
    review_count: int
    top_topics: List[str]
    competitor_mentions: int
    response_rate: float
    avg_response_time_hours: float

# Cost Tracking Models
@dataclass
class AIUsageLog:
    id: str
    business_id: str
    ai_service: str  # gpt5_nano, claude_haiku
    operation: str  # classify, chat, report
    tokens_used: int
    cost_usd: Decimal
    processing_time_ms: int
    created_at: datetime

@dataclass
class MonthlyCostSummary:
    business_id: str
    month: date
    classification_cost: Decimal
    chat_cost: Decimal
    report_cost: Decimal
    total_cost: Decimal
    cost_limit: Decimal
    usage_percentage: float
```

### Database Schema Design

```sql
-- Core business tables
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(50) NOT NULL DEFAULT 'basic',
    cost_limit_monthly DECIMAL(10,2) NOT NULL DEFAULT 100.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    google_place_id VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100),
    address TEXT,
    avg_rating DECIMAL(3,2) DEFAULT 0.0,
    total_reviews INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('super_admin', 'admin', 'viewer')),
    language_preference VARCHAR(5) DEFAULT 'en',
    organization_id UUID REFERENCES organizations(id),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE TABLE user_business_access (
    user_id UUID REFERENCES users(id),
    business_id UUID REFERENCES businesses(id),
    permission_level VARCHAR(50) NOT NULL CHECK (permission_level IN ('full_access', 'read_only')),
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, business_id)
);

-- Review and classification tables
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) NOT NULL,
    author_name VARCHAR(255),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    text TEXT NOT NULL,
    language VARCHAR(5) DEFAULT 'en',
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'google',
    external_id VARCHAR(255), -- For deduplication
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(business_id, external_id, source)
);

CREATE TABLE classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(id) NOT NULL,
    sentiment VARCHAR(20) NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    topics TEXT[] NOT NULL, -- Array of topic strings
    urgency VARCHAR(20) NOT NULL CHECK (urgency IN ('low', 'medium', 'high')),
    competitor_mentioned BOOLEAN DEFAULT FALSE,
    confidence_score DECIMAL(4,3) NOT NULL,
    ai_model VARCHAR(50) NOT NULL,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analytics and reporting tables
CREATE TABLE daily_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) NOT NULL,
    date DATE NOT NULL,
    avg_rating DECIMAL(3,2),
    sentiment_positive DECIMAL(5,2),
    sentiment_neutral DECIMAL(5,2),
    sentiment_negative DECIMAL(5,2),
    review_count INTEGER DEFAULT 0,
    top_topics TEXT[],
    competitor_mentions INTEGER DEFAULT 0,
    response_rate DECIMAL(5,2) DEFAULT 0.0,
    avg_response_time_hours DECIMAL(8,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(business_id, date)
);

-- Cost tracking tables
CREATE TABLE ai_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) NOT NULL,
    ai_service VARCHAR(50) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    tokens_used INTEGER NOT NULL,
    cost_usd DECIMAL(10,6) NOT NULL,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE monthly_cost_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) NOT NULL,
    month DATE NOT NULL, -- First day of month
    classification_cost DECIMAL(10,2) DEFAULT 0.0,
    chat_cost DECIMAL(10,2) DEFAULT 0.0,
    report_cost DECIMAL(10,2) DEFAULT 0.0,
    total_cost DECIMAL(10,2) DEFAULT 0.0,
    cost_limit DECIMAL(10,2) NOT NULL,
    usage_percentage DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(business_id, month)
);

-- Indexes for performance
CREATE INDEX idx_reviews_business_id ON reviews(business_id);
CREATE INDEX idx_reviews_published_at ON reviews(published_at);
CREATE INDEX idx_classifications_review_id ON classifications(review_id);
CREATE INDEX idx_classifications_urgency ON classifications(urgency);
CREATE INDEX idx_daily_analytics_business_date ON daily_analytics(business_id, date);
CREATE INDEX idx_ai_usage_logs_business_created ON ai_usage_logs(business_id, created_at);
CREATE INDEX idx_user_business_access_user_id ON user_business_access(user_id);
```

## Error Handling

### Exception Hierarchy

```python
class BusinessBotException(Exception):
    """Base exception for the Local Business Intelligence Bot."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

class AIServiceException(BusinessBotException):
    """Exceptions related to AI service calls."""
    pass

class RateLimitExceededException(AIServiceException):
    """Raised when AI API rate limits are exceeded."""
    pass

class CostLimitExceededException(AIServiceException):
    """Raised when monthly cost limits are exceeded."""
    pass

class DatabaseException(BusinessBotException):
    """Database-related exceptions."""
    pass

class AuthenticationException(BusinessBotException):
    """Authentication and authorization exceptions."""
    pass

class ValidationException(BusinessBotException):
    """Input validation exceptions."""
    pass

class ExternalAPIException(BusinessBotException):
    """External API integration exceptions."""
    pass
```

### Error Handling Strategy

```python
class ErrorHandler:
    """Centralized error handling with logging and user-friendly messages."""
    
    def __init__(self, logger: Logger):
        self._logger = logger
    
    async def handle_ai_service_error(
        self, 
        error: Exception, 
        context: dict
    ) -> ErrorResponse:
        """Handle AI service errors with appropriate fallbacks."""
        if isinstance(error, RateLimitExceededException):
            # Queue request for later processing
            await self._queue_for_retry(context)
            return ErrorResponse(
                message="Request queued due to rate limits",
                retry_after=error.details.get("retry_after", 60)
            )
        
        elif isinstance(error, CostLimitExceededException):
            # Disable non-essential AI operations
            await self._disable_non_essential_operations(context["business_id"])
            return ErrorResponse(
                message="Monthly cost limit exceeded",
                action_required="increase_cost_limit"
            )
        
        # Log error and return generic message
        self._logger.error(f"AI service error: {error}", extra=context)
        return ErrorResponse(
            message="AI service temporarily unavailable",
            retry_after=300
        )
```

## Testing Strategy

### Test Architecture

```python
# Test Configuration
class TestConfig:
    """Test-specific configuration."""
    DATABASE_URL = "postgresql://test:test@localhost:5432/businessbot_test"
    REDIS_URL = "redis://localhost:6379/1"
    AI_SERVICES_MOCK = True
    EMAIL_BACKEND = "mock"
    
# Test Fixtures
@pytest.fixture
async def test_db():
    """Provide clean test database for each test."""
    engine = create_async_engine(TestConfig.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine)
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def mock_ai_services():
    """Mock AI services for testing."""
    classifier = Mock(spec=ReviewClassifierProtocol)
    advisor = Mock(spec=BusinessAdvisorProtocol)
    
    # Configure default responses
    classifier.classify_review.return_value = ClassificationResult(
        sentiment="positive",
        topics=["food_quality"],
        urgency="low",
        confidence_score=0.95
    )
    
    return {"classifier": classifier, "advisor": advisor}

# Integration Test Example
class TestReviewProcessingIntegration:
    """Integration tests for the complete review processing pipeline."""
    
    async def test_complete_review_processing_workflow(
        self, 
        test_db, 
        mock_ai_services
    ):
        # Arrange
        business = await create_test_business(test_db)
        reviews = await create_test_reviews(test_db, business.id, count=5)
        
        service = ReviewProcessingService(
            classifier=mock_ai_services["classifier"],
            repository=ReviewRepository(test_db),
            # ... other dependencies
        )
        
        # Act
        result = await service.process_new_reviews(business.id)
        
        # Assert
        assert result.processed_count == 5
        assert result.success_count == 5
        assert result.error_count == 0
        
        # Verify classifications were saved
        classifications = await get_classifications_by_business(test_db, business.id)
        assert len(classifications) == 5
```

### Performance Testing

```python
class TestPerformance:
    """Performance tests for critical operations."""
    
    async def test_batch_classification_performance(self, mock_ai_services):
        """Test that batch classification meets performance requirements."""
        # Arrange
        reviews = [f"Review text {i}" for i in range(500)]
        service = ReviewProcessingService(mock_ai_services["classifier"])
        
        # Act
        start_time = time.time()
        results = await service.classify_batch(reviews)
        end_time = time.time()
        
        # Assert
        processing_time = end_time - start_time
        assert processing_time < 60  # Must complete within 60 seconds
        assert len(results) == 500
    
    async def test_dashboard_response_time(self, test_db):
        """Test dashboard data loading performance."""
        # Arrange
        business = await create_test_business_with_data(test_db, review_count=1000)
        service = AnalyticsService(test_db)
        
        # Act
        start_time = time.time()
        dashboard_data = await service.get_dashboard_data(business.id)
        end_time = time.time()
        
        # Assert
        response_time = end_time - start_time
        assert response_time < 0.5  # Must load within 500ms
        assert dashboard_data.avg_rating is not None
```

This design provides a robust, scalable foundation for the Local Business Intelligence Bot with clear separation of concerns, comprehensive error handling, and strong testing strategies.