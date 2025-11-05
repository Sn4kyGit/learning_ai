# Local Business Intelligence Bot - Development Standards

## Code Quality Standards

### Python Backend Standards
- **PEP 8 Compliance**: All Python code MUST follow PEP 8 style guidelines
- **Type Hints**: Use Python type hints for all function parameters and return values
- **Docstrings**: Every class and function MUST have descriptive docstrings following Google style
- **Line Length**: Maximum 88 characters per line (Black formatter standard)
- **Import Organization**: Use isort for consistent import ordering

### File Size Limits
- **Maximum File Size**: No single file should exceed 500 lines of code
- **Class Size**: Individual classes should not exceed 200 lines
- **Function Size**: Individual functions should not exceed 50 lines
- **Refactoring Rule**: When approaching limits, extract functionality into separate modules/classes

### Object-Oriented Programming Principles
- **Single Responsibility**: Each class should have one clear purpose
- **Dependency Injection**: Use dependency injection for external services (AI APIs, database)
- **Interface Segregation**: Define clear interfaces/protocols for AI agents and data access
- **Composition over Inheritance**: Prefer composition for complex relationships
- **SOLID Principles**: Follow SOLID principles throughout the codebase

## Project Structure Standards

### Backend Structure
```
backend/
├── main.py                    # FastAPI app entry point (<100 lines)
├── config.py                  # Configuration management
├── requirements.txt           # Dependencies
│
├── ai/                        # AI service layer
│   ├── __init__.py
│   ├── base.py               # Abstract base classes
│   ├── gpt5_classifier.py    # GPT-5 Nano implementation
│   └── claude_advisor.py     # Claude Haiku implementation
│
├── db/                        # Database layer
│   ├── __init__.py
│   ├── database.py           # Connection management
│   ├── models.py             # SQLAlchemy models
│   ├── schemas.py            # Pydantic schemas
│   └── repositories/         # Repository pattern
│       ├── __init__.py
│       ├── base.py
│       ├── business.py
│       └── review.py
│
├── services/                  # Business logic layer
│   ├── __init__.py
│   ├── review_service.py     # Review processing logic
│   ├── analytics_service.py  # Analytics calculations
│   └── report_service.py     # Report generation
│
├── routes/                    # API endpoints
│   ├── __init__.py
│   ├── health.py             # Health check endpoints
│   ├── reviews.py            # Review endpoints
│   ├── chat.py               # Chat endpoints
│   ├── analytics.py          # Analytics endpoints
│   └── businesses.py         # Business endpoints
│
├── external/                  # External API integrations
│   ├── __init__.py
│   ├── google_places.py      # Google Places API client
│   └── base_client.py        # Base HTTP client
│
└── tests/                     # Test suite
    ├── __init__.py
    ├── conftest.py           # Pytest configuration
    ├── unit/                 # Unit tests
    ├── integration/          # Integration tests
    └── fixtures/             # Test data
```

### Frontend Structure
```
frontend/src/
├── main.js                   # Vue app entry
├── App.vue                   # Root component
├── router/index.js           # Vue Router config
│
├── views/                    # Page components
│   ├── Dashboard.vue
│   ├── ChatView.vue
│   └── ReviewAnalysis.vue
│
├── components/               # Reusable components
│   ├── common/              # Generic components
│   ├── charts/              # Chart components
│   └── forms/               # Form components
│
├── services/                 # API and business logic
│   ├── api.js               # HTTP client
│   ├── auth.js              # Authentication
│   └── utils.js             # Utility functions
│
├── stores/                   # State management
│   └── index.js             # Pinia stores
│
└── assets/                   # Static assets
    ├── styles/
    └── images/
```

## Testing Standards

### Test Coverage Requirements
- **Minimum Coverage**: 80% code coverage for backend services
- **Critical Path Coverage**: 100% coverage for AI integration and data processing
- **Unit Tests**: Every service class must have comprehensive unit tests
- **Integration Tests**: API endpoints must have integration tests
- **Test-First Development**: Write tests BEFORE implementing features (TDD)
- **Test Categories**: Unit (fast, isolated), Integration (API endpoints), E2E (user workflows)

### Testing Patterns
- **Arrange-Act-Assert**: Use AAA pattern for all tests
- **Test Isolation**: Each test must be independent and repeatable
- **Mock External Services**: Mock all external APIs (OpenAI, Anthropic, Google Places)
- **Fixture Usage**: Use pytest fixtures for common test data
- **Parameterized Tests**: Use pytest.mark.parametrize for multiple test cases

### Test Implementation Strategy
**MANDATORY**: Tests must be written alongside feature implementation, not after.

**Unit Tests** (backend/tests/unit/):
```python
# Example: Service layer unit test
class TestReviewClassificationService:
    @pytest.fixture
    def mock_ai_client(self):
        return Mock(spec=ReviewClassifier)
    
    @pytest.fixture
    def mock_repository(self):
        return Mock(spec=ReviewRepository)
    
    @pytest.fixture
    def service(self, mock_ai_client, mock_repository):
        return ReviewClassificationService(
            classifier=mock_ai_client,
            repository=mock_repository
        )
    
    async def test_classify_review_success(self, service, mock_ai_client):
        # Arrange
        review_text = "Great food and service!"
        expected_result = ClassificationResult(
            sentiment="positive",
            topics=["food_quality", "service"],
            confidence=0.95
        )
        mock_ai_client.classify_review.return_value = expected_result
        
        # Act
        result = await service.classify_review(review_text)
        
        # Assert
        assert result.sentiment == "positive"
        assert "food_quality" in result.topics
        mock_ai_client.classify_review.assert_called_once_with(review_text)
```

**Integration Tests** (backend/tests/integration/):
```python
# Example: API endpoint integration test
class TestReviewAPI:
    async def test_classify_reviews_endpoint(self, client, test_db):
        # Arrange
        payload = {
            "business_id": "test-restaurant",
            "reviews": ["Great food!", "Slow service"]
        }
        
        # Act
        response = await client.post("/api/classify-reviews", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["classifications"]) == 2
        assert data["classifications"][0]["sentiment"] in ["positive", "negative", "neutral"]
```

**End-to-End Tests** (backend/tests/e2e/):
```python
# Example: Complete user workflow test
class TestUserWorkflow:
    async def test_complete_review_analysis_workflow(self, client, test_db):
        # Arrange: Create business
        business_data = {"name": "Test Restaurant", "google_place_id": "test123"}
        business_response = await client.post("/api/businesses", json=business_data)
        business_id = business_response.json()["id"]
        
        # Act 1: Import reviews
        import_response = await client.post(f"/api/businesses/{business_id}/import-reviews")
        assert import_response.status_code == 200
        
        # Act 2: Get analytics
        analytics_response = await client.get(f"/api/analytics/{business_id}")
        assert analytics_response.status_code == 200
        
        # Act 3: Chat with advisor
        chat_payload = {"message": "How is my restaurant performing?"}
        chat_response = await client.post(f"/api/chat/{business_id}", json=chat_payload)
        
        # Assert: Complete workflow works
        assert chat_response.status_code == 200
        assert "sentiment" in chat_response.json()["response"].lower()
```

### Test File Organization
```python
# Example test structure
class TestReviewClassificationService:
    """Test suite for review classification service."""
    
    def test_classify_positive_review_success(self, mock_gpt_client):
        # Arrange
        service = ReviewClassificationService(ai_client=mock_gpt_client)
        review_text = "Great food and excellent service!"
        
        # Act
        result = service.classify_review(review_text)
        
        # Assert
        assert result.sentiment == "positive"
        assert "food_quality" in result.topics
```

## Error Handling Standards

### Exception Hierarchy
```python
# Custom exception hierarchy
class BusinessBotException(Exception):
    """Base exception for the application."""
    pass

class AIServiceException(BusinessBotException):
    """Exceptions related to AI service calls."""
    pass

class DatabaseException(BusinessBotException):
    """Database-related exceptions."""
    pass

class ExternalAPIException(BusinessBotException):
    """External API integration exceptions."""
    pass
```

### Error Handling Patterns
- **Fail Fast**: Validate inputs early and fail with clear error messages
- **Graceful Degradation**: Provide fallback behavior when external services fail
- **Logging**: Log all errors with appropriate context and severity levels
- **User-Friendly Messages**: Convert technical errors to user-friendly messages at API boundary

## Performance Standards

### Response Time Requirements
- **API Endpoints**: < 500ms for simple queries, < 3s for AI operations
- **Database Queries**: Use indexes and optimize N+1 query problems
- **Caching Strategy**: Implement caching for frequently accessed data
- **Async Operations**: Use async/await for I/O bound operations

### Resource Management
- **Connection Pooling**: Use connection pooling for database and HTTP clients
- **Memory Management**: Avoid memory leaks in long-running processes
- **Rate Limiting**: Implement rate limiting for external API calls
- **Batch Processing**: Process multiple items in batches where possible

## Security Standards

### API Security
- **Input Validation**: Validate all inputs using Pydantic schemas
- **SQL Injection Prevention**: Use SQLAlchemy ORM, never raw SQL with user input
- **API Key Management**: Store API keys in environment variables, never in code
- **CORS Configuration**: Configure CORS appropriately for frontend domain

### Data Protection
- **Sensitive Data**: Never log API keys, user passwords, or PII
- **Data Sanitization**: Sanitize user inputs before processing
- **Audit Logging**: Log all significant operations for audit trails

## Documentation Standards

### Code Documentation
- **README Files**: Each major module should have a README explaining its purpose
- **API Documentation**: Use FastAPI's automatic documentation features
- **Architecture Decisions**: Document significant architectural decisions and trade-offs
- **Setup Instructions**: Provide clear setup and deployment instructions

### Comment Standards
```python
# Good: Explains WHY, not WHAT
def calculate_sentiment_score(reviews: List[Review]) -> float:
    """Calculate weighted sentiment score.
    
    Uses recency weighting to give more importance to recent reviews
    since they better reflect current business performance.
    """
    # Weight recent reviews more heavily (exponential decay)
    weighted_sum = sum(
        review.sentiment_score * exp(-days_old * 0.1) 
        for review in reviews
    )
```

## Git Workflow Standards

### Commit Standards
- **Conventional Commits**: Use conventional commit format (feat:, fix:, docs:, etc.)
- **Atomic Commits**: Each commit should represent a single logical change
- **Clear Messages**: Write clear, descriptive commit messages
- **Branch Naming**: Use descriptive branch names (feature/ai-integration, fix/database-connection)

### Code Review Standards
- **Pull Request Size**: Keep PRs focused and reviewable (< 400 lines changed)
- **Review Checklist**: Check for code standards, tests, and documentation
- **Approval Requirements**: Require at least one approval before merging
- **CI/CD Integration**: All tests must pass before merging

## Development Tools

### Required Tools
- **Code Formatting**: Black for Python, Prettier for JavaScript
- **Linting**: Flake8 for Python, ESLint for JavaScript
- **Type Checking**: mypy for Python static type checking
- **Testing**: pytest for Python, Vitest for JavaScript
- **Pre-commit Hooks**: Use pre-commit to enforce standards

### IDE Configuration
```json
// .vscode/settings.json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.testing.pytestEnabled": true,
    "editor.formatOnSave": true,
    "editor.rulers": [88]
}
```

## Project-Specific Standards for Local Business Intelligence Bot

### File Size Monitoring
**MANDATORY**: Monitor and enforce file size limits throughout development.

```bash
# Pre-commit hook to check file sizes
find backend/ -name "*.py" -exec wc -l {} + | awk '$1 > 500 {print "WARNING: " $2 " has " $1 " lines (limit: 500)"}'
```

### Recommended File Splits for Large Components

**AI Services** (if approaching 500 lines):
```
backend/ai/
├── base.py                    # Abstract base classes (<100 lines)
├── gpt5_classifier.py         # GPT-5 implementation (<300 lines)
├── claude_advisor.py          # Claude implementation (<300 lines)
├── cost_tracker.py            # Cost tracking logic (<200 lines)
└── language_detector.py       # Language detection (<150 lines)
```

**Services Layer** (split by domain):
```
backend/services/
├── review/
│   ├── __init__.py
│   ├── processor.py           # Review processing (<250 lines)
│   ├── classifier.py          # Classification logic (<200 lines)
│   └── importer.py            # Google Places import (<200 lines)
├── analytics/
│   ├── __init__.py
│   ├── calculator.py          # Metrics calculation (<300 lines)
│   ├── dashboard.py           # Dashboard data prep (<200 lines)
│   └── reporter.py            # Report generation (<250 lines)
├── notification/
│   ├── __init__.py
│   ├── alert_service.py       # Real-time alerts (<200 lines)
│   └── email_service.py       # Email notifications (<150 lines)
└── user/
    ├── __init__.py
    ├── auth_service.py        # Authentication (<200 lines)
    └── permission_service.py  # Role-based access (<150 lines)
```

### Code Quality Checklist for Each Feature

**Before Implementation:**
- [ ] Class design follows Single Responsibility Principle
- [ ] Dependencies are injected, not hardcoded
- [ ] Interfaces/protocols defined for external services
- [ ] Error handling strategy planned
- [ ] Test strategy defined

**During Implementation:**
- [ ] Functions < 50 lines each
- [ ] Classes < 200 lines each
- [ ] Files < 500 lines total
- [ ] Type hints on all functions
- [ ] Docstrings in Google format
- [ ] PEP 8 compliance (use Black formatter)

**Post Implementation:**
- [ ] All tests pass (pytest)
- [ ] Code coverage > 80%
- [ ] Linting passes (flake8, mypy)
- [ ] No code smells (pylint score > 8.0)
- [ ] Documentation updated

### Automated Quality Gates

**Pre-commit Configuration** (.pre-commit-config.yaml):
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: local
    hooks:
      - id: file-size-check
        name: Check file sizes
        entry: bash -c 'find backend/ -name "*.py" -exec wc -l {} + | awk "$1 > 500 {print \"ERROR: \" $2 \" has \" $1 \" lines (limit: 500)\"; exit 1}"'
        language: system
        pass_filenames: false
```

### OOP Design Patterns for This Project

**Repository Pattern** (Data Access):
```python
from abc import ABC, abstractmethod
from typing import List, Optional

class ReviewRepositoryProtocol(ABC):
    @abstractmethod
    async def save_review(self, review: Review) -> Review:
        pass
    
    @abstractmethod
    async def get_reviews_by_business(self, business_id: str) -> List[Review]:
        pass

class PostgreSQLReviewRepository(ReviewRepositoryProtocol):
    def __init__(self, db_session: AsyncSession):
        self._session = db_session
    
    async def save_review(self, review: Review) -> Review:
        # Implementation
        pass
```

**Strategy Pattern** (AI Services):
```python
class AIClassifierStrategy(ABC):
    @abstractmethod
    async def classify_review(self, text: str) -> ClassificationResult:
        pass

class GPT5NanoClassifier(AIClassifierStrategy):
    def __init__(self, api_client: OpenAIClient, cost_tracker: CostTracker):
        self._client = api_client
        self._cost_tracker = cost_tracker
```

**Observer Pattern** (Alerts):
```python
class ReviewAnalysisObserver(ABC):
    @abstractmethod
    async def on_critical_review(self, review: Review, classification: Classification):
        pass

class AlertService(ReviewAnalysisObserver):
    async def on_critical_review(self, review: Review, classification: Classification):
        if classification.urgency == "high":
            await self._send_alert(review, classification)
```

### Specific Linting Rules for This Project

**flake8 Configuration** (.flake8):
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503, E501
exclude = 
    .git,
    __pycache__,
    .venv,
    migrations/
per-file-ignores =
    __init__.py:F401
max-complexity = 10
```

**mypy Configuration** (mypy.ini):
```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

[mypy-tests.*]
disallow_untyped_defs = False
```

### Performance Monitoring

**Code Performance Rules:**
- Database queries must use indexes (check with EXPLAIN)
- AI API calls must be batched when possible
- Cache frequently accessed data (Redis)
- Use async/await for I/O operations
- Profile critical paths with cProfile

**Memory Management:**
- Close database connections properly
- Use context managers for file operations
- Avoid memory leaks in long-running processes
- Monitor memory usage in production

### Security Code Review Checklist

- [ ] No hardcoded secrets or API keys
- [ ] All inputs validated with Pydantic
- [ ] SQL injection prevention (use ORM)
- [ ] XSS prevention in API responses
- [ ] CORS configured correctly
- [ ] Rate limiting implemented
- [ ] Authentication/authorization on all endpoints
- [ ] Sensitive data not logged
- [ ] Error messages don't leak information

These standards ensure maintainable, testable, and scalable code throughout the project development.