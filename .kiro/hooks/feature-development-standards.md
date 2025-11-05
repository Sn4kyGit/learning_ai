---
name: "Feature Development Standards Enforcement"
description: "Ensures every feature is developed with tests, best practices, and OOP principles"
trigger: "on_code_change"
enabled: true
---

# Feature Development Standards Hook

## Trigger Conditions
- When any Python file is created or modified in `/backend/`
- When any Vue file is created or modified in `/frontend/`
- When implementing any new feature or functionality

## Enforcement Rules

### 1. Test-Driven Development
**MANDATORY**: Every new feature MUST include tests WRITTEN ALONGSIDE implementation (not after).

- **Unit Tests**: Every service class and business logic function
- **Integration Tests**: Every API endpoint  
- **E2E Tests**: Critical user workflows
- **Test Coverage**: Minimum 80% coverage for new code
- **Test Location**: Tests must be in appropriate `/tests/` directory structure
- **TDD Approach**: Write failing test → Implement feature → Refactor while keeping tests green

### 2. Object-Oriented Programming Compliance
**MANDATORY**: All new code MUST follow OOP principles.

- **Single Responsibility**: Each class has one clear purpose
- **Dependency Injection**: External services injected, not hardcoded
- **Interface Segregation**: Clear interfaces/protocols defined
- **Composition over Inheritance**: Prefer composition for complex relationships
- **SOLID Principles**: All five SOLID principles must be followed

### 3. Code Quality Standards
**MANDATORY**: All code MUST meet quality standards before merge.

- **PEP 8 Compliance**: Python code formatted with Black
- **Type Hints**: All functions have proper type annotations
- **Docstrings**: Google-style docstrings for all classes and functions
- **File Size Limit**: No file exceeds 500 lines of code
- **Function Size Limit**: No function exceeds 50 lines

### 4. Architecture Compliance
**MANDATORY**: Code MUST follow the defined project structure.

- **Layer Separation**: Clear separation between AI, DB, Services, Routes
- **Repository Pattern**: Data access through repository classes
- **Service Layer**: Business logic in dedicated service classes
- **Error Handling**: Custom exception hierarchy used consistently

## Pre-Implementation Checklist

Before starting any feature development, ensure:

- [ ] Feature requirements are clearly defined
- [ ] **Test cases are planned and documented (Unit + Integration + E2E)**
- [ ] **Test fixtures and mocks are designed**
- [ ] Class design follows OOP principles
- [ ] Dependencies are identified and can be injected
- [ ] Error handling strategy is defined
- [ ] Performance implications are considered

## Implementation Checklist

During feature development (TDD Cycle):

- [ ] **Write failing unit tests first**
- [ ] **Write failing integration tests for API endpoints**
- [ ] Implement minimal code to make tests pass
- [ ] Refactor while keeping tests green
- [ ] **Add E2E tests for complete user workflows**
- [ ] Add comprehensive docstrings
- [ ] Handle edge cases and errors
- [ ] Validate input parameters
- [ ] Log important operations

## Post-Implementation Checklist

After feature implementation:

- [ ] **All tests pass (unit + integration + E2E)**
- [ ] **Code coverage meets minimum 80%**
- [ ] **Test execution time < 30 seconds for unit tests**
- [ ] Code formatted with Black/Prettier
- [ ] Type checking passes (mypy)
- [ ] Linting passes (flake8/ESLint)
- [ ] Documentation updated
- [ ] Performance tested
- [ ] Security reviewed

## Example Implementation Pattern

```python
# Example: Proper feature implementation structure

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

# 1. Define interfaces/protocols
class ReviewClassifierProtocol(ABC):
    @abstractmethod
    async def classify_review(self, text: str) -> ClassificationResult:
        """Classify a review text into sentiment and topics."""
        pass

# 2. Define data structures
@dataclass
class ClassificationResult:
    """Result of review classification."""
    sentiment: str
    topics: List[str]
    confidence: float
    urgency: str

# 3. Implement service with dependency injection
class ReviewService:
    """Service for processing restaurant reviews."""
    
    def __init__(self, classifier: ReviewClassifierProtocol, repository: ReviewRepository):
        """Initialize service with injected dependencies.
        
        Args:
            classifier: AI classifier for review analysis
            repository: Data access layer for reviews
        """
        self._classifier = classifier
        self._repository = repository
    
    async def process_review(self, review_text: str, business_id: str) -> ClassificationResult:
        """Process a single review through classification pipeline.
        
        Args:
            review_text: The review content to analyze
            business_id: ID of the business being reviewed
            
        Returns:
            Classification result with sentiment and topics
            
        Raises:
            ReviewProcessingError: If classification fails
        """
        try:
            # Validate input
            if not review_text.strip():
                raise ValueError("Review text cannot be empty")
            
            # Classify review
            result = await self._classifier.classify_review(review_text)
            
            # Store result
            await self._repository.save_classification(business_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process review for business {business_id}: {e}")
            raise ReviewProcessingError(f"Review processing failed: {e}") from e

# 4. Comprehensive test coverage
class TestReviewService:
    """Test suite for ReviewService."""
    
    @pytest.fixture
    def mock_classifier(self):
        """Mock classifier for testing."""
        classifier = Mock(spec=ReviewClassifierProtocol)
        classifier.classify_review.return_value = ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            confidence=0.95,
            urgency="low"
        )
        return classifier
    
    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing."""
        return Mock(spec=ReviewRepository)
    
    @pytest.fixture
    def service(self, mock_classifier, mock_repository):
        """Service instance for testing."""
        return ReviewService(mock_classifier, mock_repository)
    
    async def test_process_review_success(self, service, mock_classifier, mock_repository):
        """Test successful review processing."""
        # Arrange
        review_text = "Great food and excellent service!"
        business_id = "test-business-123"
        
        # Act
        result = await service.process_review(review_text, business_id)
        
        # Assert
        assert result.sentiment == "positive"
        assert "food_quality" in result.topics
        mock_classifier.classify_review.assert_called_once_with(review_text)
        mock_repository.save_classification.assert_called_once()
    
    async def test_process_review_empty_text_raises_error(self, service):
        """Test that empty review text raises ValueError."""
        # Arrange
        review_text = "   "  # Empty/whitespace only
        business_id = "test-business-123"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Review text cannot be empty"):
            await service.process_review(review_text, business_id)
```

## Enforcement Actions

If standards are not met:

1. **Automated Checks**: Pre-commit hooks prevent commits that don't meet standards
2. **CI/CD Pipeline**: Build fails if tests don't pass or coverage is insufficient
3. **Code Review**: PRs blocked until standards compliance is verified
4. **Documentation**: Non-compliant code requires refactoring before merge

## Benefits of This Approach

- **Maintainability**: Clean, well-structured code is easier to maintain
- **Testability**: Dependency injection makes code highly testable
- **Reliability**: Comprehensive tests catch bugs early
- **Scalability**: Proper architecture supports future growth
- **Team Collaboration**: Consistent standards improve team productivity

## Automated Quality Checks

### File Size Enforcement
```bash
# Check during development
find backend/ -name "*.py" -exec wc -l {} + | awk '$1 > 500 {print "❌ " $2 " has " $1 " lines (limit: 500)"}'
find frontend/src/ -name "*.vue" -exec wc -l {} + | awk '$1 > 300 {print "❌ " $2 " has " $1 " lines (limit: 300)"}'
```

### Code Quality Commands
```bash
# Run all quality checks
black backend/ --check                    # Code formatting
flake8 backend/                          # Linting
mypy backend/                            # Type checking
isort backend/ --check-only              # Import sorting
pylint backend/ --fail-under=8.0         # Code quality score
pytest backend/tests/ --cov=backend/     # Tests with coverage
```

### Folder Structure Validation
The hook validates that new files follow the approved structure:

```
backend/
├── ai/                    # AI services (max 5 files)
│   ├── base.py           # <100 lines
│   ├── gpt5_classifier.py # <300 lines
│   ├── claude_advisor.py  # <300 lines
│   ├── cost_tracker.py    # <200 lines
│   └── language_detector.py # <150 lines
├── services/              # Business logic (domain-split)
│   ├── review/           # Review domain
│   ├── analytics/        # Analytics domain
│   ├── notification/     # Notification domain
│   └── user/            # User management domain
├── db/                   # Database layer
│   ├── models/          # Split models by domain
│   ├── repositories/    # Repository implementations
│   └── schemas/         # Pydantic schemas
└── routes/              # API endpoints (max 200 lines each)
```

### OOP Compliance Checks

**Interface Segregation Check:**
```python
# ❌ Bad: Fat interface
class AIService:
    def classify_review(self): pass
    def generate_chat_response(self): pass
    def calculate_costs(self): pass
    def detect_language(self): pass

# ✅ Good: Segregated interfaces
class ReviewClassifier(Protocol):
    def classify_review(self): pass

class ChatAdvisor(Protocol):
    def generate_response(self): pass
```

**Dependency Injection Check:**
```python
# ❌ Bad: Hardcoded dependencies
class ReviewService:
    def __init__(self):
        self.classifier = GPT5Classifier()  # Hardcoded!
        self.db = PostgreSQLDB()           # Hardcoded!

# ✅ Good: Injected dependencies
class ReviewService:
    def __init__(self, classifier: ReviewClassifier, repository: ReviewRepository):
        self._classifier = classifier
        self._repository = repository
```

### Performance Standards Check

**Database Query Optimization:**
- All queries must use appropriate indexes
- N+1 query problems must be avoided
- Batch operations for multiple records
- Use async/await for database operations

**AI API Efficiency:**
- Batch multiple reviews in single API calls
- Implement request caching where appropriate
- Use exponential backoff for retries
- Track and limit token usage

### Security Standards Check

**Input Validation:**
```python
# ✅ All inputs validated
class ReviewRequest(BaseModel):
    business_id: str = Field(..., min_length=1, max_length=100)
    review_text: str = Field(..., min_length=1, max_length=5000)
    rating: int = Field(..., ge=1, le=5)
```

**Secret Management:**
```python
# ❌ Bad: Hardcoded secrets
api_key = "sk-proj-abc123..."

# ✅ Good: Environment variables
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable required")
```

This hook ensures that every feature developed follows professional software development practices and maintains high code quality throughout the project.