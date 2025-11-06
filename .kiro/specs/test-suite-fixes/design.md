# Test Suite Fixes - Design Document

## Overview

The test suite redesign focuses on creating a robust, maintainable testing framework that properly handles async operations, provides comprehensive coverage, and follows OOP best practices. The design emphasizes test isolation, proper mocking, and clear test organization while maintaining performance and reliability.

### Key Design Principles

- **Async-First Testing**: Proper async/await handling with pytest-asyncio
- **Test Isolation**: Complete isolation between tests with proper cleanup
- **Comprehensive Mocking**: Proper mock configuration for external dependencies
- **Performance Validation**: Built-in performance testing for critical operations
- **OOP Compliance**: Test organization following project structure and size limits
- **CI/CD Integration**: Reliable test execution in automated environments

## Architecture

### Test Framework Architecture

```mermaid
graph TB
    subgraph "Test Configuration Layer"
        PyTestConfig[pytest.ini]
        ConfTest[conftest.py]
        TestEnv[Test Environment]
    end
    
    subgraph "Test Categories"
        UnitTests[Unit Tests]
        IntegrationTests[Integration Tests]
        E2ETests[End-to-End Tests]
        PerformanceTests[Performance Tests]
    end
    
    subgraph "Test Infrastructure"
        AsyncFixtures[Async Fixtures]
        MockServices[Mock Services]
        TestDatabase[Test Database]
        TestClient[API Test Client]
    end
    
    subgraph "Test Utilities"
        TestHelpers[Test Helper Classes]
        DataFactories[Test Data Factories]
        AssertionHelpers[Custom Assertions]
        CoverageTools[Coverage Analysis]
    end
    
    PyTestConfig --> UnitTests
    PyTestConfig --> IntegrationTests
    PyTestConfig --> E2ETests
    
    ConfTest --> AsyncFixtures
    ConfTest --> MockServices
    ConfTest --> TestDatabase
    
    UnitTests --> MockServices
    IntegrationTests --> TestClient
    E2ETests --> TestDatabase
    
    TestHelpers --> DataFactories
    TestHelpers --> AssertionHelpers
```

### Test Organization Structure

```
backend/tests/
├── conftest.py                    # Global test configuration and fixtures
├── pytest.ini                    # Pytest configuration
├── test_config.py                 # Test-specific configuration
│
├── unit/                          # Unit tests (isolated, mocked dependencies)
│   ├── __init__.py
│   ├── test_ai/                   # AI service unit tests
│   │   ├── test_base_protocols.py
│   │   ├── test_gpt5_classifier.py
│   │   ├── test_claude_advisor.py
│   │   └── test_cost_tracker.py
│   ├── test_services/             # Service layer unit tests
│   │   ├── test_auth_service.py
│   │   ├── test_analytics_service.py
│   │   ├── test_review_service.py
│   │   └── test_notification_service.py
│   ├── test_db/                   # Database layer unit tests
│   │   ├── test_models.py
│   │   ├── test_repositories.py
│   │   └── test_schemas.py
│   └── test_utils/                # Utility function tests
│
├── integration/                   # Integration tests (real API endpoints)
│   ├── __init__.py
│   ├── test_api/                  # API endpoint integration tests
│   │   ├── test_auth_endpoints.py
│   │   ├── test_business_endpoints.py
│   │   ├── test_chat_endpoints.py
│   │   └── test_analytics_endpoints.py
│   ├── test_services/             # Service integration tests
│   │   ├── test_ai_integration.py
│   │   ├── test_database_integration.py
│   │   └── test_external_api_integration.py
│   └── test_workflows/            # Business workflow integration tests
│
├── e2e/                           # End-to-end tests (complete user workflows)
│   ├── __init__.py
│   ├── test_user_workflows.py     # Complete user journey tests
│   ├── test_multi_tenant.py       # Multi-tenant functionality tests
│   ├── test_performance.py        # Performance and load tests
│   └── test_deployment.py         # Deployment scenario tests
│
├── fixtures/                      # Test data and fixtures
│   ├── __init__.py
│   ├── business_fixtures.py       # Business-related test data
│   ├── user_fixtures.py           # User and auth test data
│   ├── review_fixtures.py         # Review and classification test data
│   └── mock_responses.py          # Mock API response data
│
└── helpers/                       # Test utility classes and functions
    ├── __init__.py
    ├── async_helpers.py           # Async test utilities
    ├── mock_helpers.py            # Mock configuration helpers
    ├── assertion_helpers.py       # Custom assertion functions
    └── performance_helpers.py     # Performance testing utilities
```

## Components and Interfaces

### Test Configuration Framework

```python
# conftest.py - Global test configuration
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from httpx import AsyncClient
from unittest.mock import AsyncMock, Mock

from backend.main import app
from backend.db.database import get_db_session
from backend.config import get_settings

class TestConfig:
    """Test-specific configuration."""
    DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/businessbot_test"
    REDIS_URL = "redis://localhost:6379/1"
    AI_SERVICES_MOCK = True
    EMAIL_BACKEND = "mock"
    ENVIRONMENT = "test"

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide clean test database session for each test."""
    engine = create_async_engine(TestConfig.DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide test client with database override."""
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
def mock_ai_services() -> dict:
    """Provide mocked AI services for testing."""
    return {
        "gpt5_classifier": AsyncMock(spec=ReviewClassifierProtocol),
        "claude_advisor": AsyncMock(spec=BusinessAdvisorProtocol),
        "cost_tracker": AsyncMock(spec=CostTracker),
        "language_detector": Mock(spec=LanguageDetector)
    }
```

### Test Helper Classes

```python
# helpers/async_helpers.py
import asyncio
from typing import Any, Awaitable, TypeVar

T = TypeVar('T')

class AsyncTestHelper:
    """Helper class for async test operations."""
    
    @staticmethod
    async def run_with_timeout(coro: Awaitable[T], timeout: float = 5.0) -> T:
        """Run coroutine with timeout for performance testing."""
        return await asyncio.wait_for(coro, timeout=timeout)
    
    @staticmethod
    async def assert_async_raises(
        exception_class: type, 
        coro: Awaitable[Any]
    ) -> None:
        """Assert that async operation raises specific exception."""
        with pytest.raises(exception_class):
            await coro
    
    @staticmethod
    def create_async_mock_with_return(return_value: Any) -> AsyncMock:
        """Create AsyncMock with specific return value."""
        mock = AsyncMock()
        mock.return_value = return_value
        return mock

# helpers/mock_helpers.py
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

class MockServiceFactory:
    """Factory for creating properly configured service mocks."""
    
    @staticmethod
    def create_gpt5_classifier_mock() -> AsyncMock:
        """Create properly configured GPT-5 classifier mock."""
        mock = AsyncMock(spec=GPT5NanoClassifier)
        mock.classify_review.return_value = ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            urgency="low",
            confidence_score=0.95,
            competitor_mentioned=False
        )
        mock.classify_batch.return_value = [
            ClassificationResult(
                sentiment="positive",
                topics=["service"],
                urgency="low",
                confidence_score=0.92,
                competitor_mentioned=False
            )
        ]
        return mock
    
    @staticmethod
    def create_claude_advisor_mock() -> AsyncMock:
        """Create properly configured Claude advisor mock."""
        mock = AsyncMock(spec=ClaudeHaikuAdvisor)
        mock.generate_response.return_value = AdvisorResponse(
            message="Based on your reviews, I recommend focusing on service quality.",
            conversation_id="test-conv-123",
            language="en"
        )
        mock.generate_report.return_value = WeeklyReport(
            summary="Your restaurant received 15 reviews this week.",
            action_items=["Improve service speed", "Address cleanliness concerns"],
            sentiment_trend="positive",
            language="en"
        )
        return mock

# helpers/assertion_helpers.py
from typing import Any, Dict, List
import time

class TestAssertions:
    """Custom assertion helpers for business logic validation."""
    
    @staticmethod
    def assert_classification_result(
        result: ClassificationResult,
        expected_sentiment: str = None,
        expected_topics: List[str] = None,
        min_confidence: float = 0.8
    ) -> None:
        """Assert classification result meets expectations."""
        assert result.confidence_score >= min_confidence
        if expected_sentiment:
            assert result.sentiment == expected_sentiment
        if expected_topics:
            assert all(topic in result.topics for topic in expected_topics)
    
    @staticmethod
    def assert_response_time(start_time: float, max_seconds: float) -> None:
        """Assert operation completed within time limit."""
        elapsed = time.time() - start_time
        assert elapsed <= max_seconds, f"Operation took {elapsed:.2f}s, expected <{max_seconds}s"
    
    @staticmethod
    def assert_api_response(
        response: Any,
        expected_status: int = 200,
        required_fields: List[str] = None
    ) -> None:
        """Assert API response format and content."""
        assert response.status_code == expected_status
        if required_fields and response.status_code == 200:
            data = response.json()
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
```

### Performance Testing Framework

```python
# helpers/performance_helpers.py
import time
import asyncio
from typing import Callable, Any, List
from dataclasses import dataclass

@dataclass
class PerformanceResult:
    """Performance test result data."""
    operation_name: str
    execution_time: float
    success: bool
    error_message: str = None

class PerformanceTester:
    """Performance testing utilities."""
    
    def __init__(self, max_response_time: float = 0.5):
        self.max_response_time = max_response_time
        self.results: List[PerformanceResult] = []
    
    async def measure_async_operation(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> PerformanceResult:
        """Measure execution time of async operation."""
        start_time = time.time()
        try:
            await operation(*args, **kwargs)
            execution_time = time.time() - start_time
            success = execution_time <= self.max_response_time
            result = PerformanceResult(
                operation_name=operation_name,
                execution_time=execution_time,
                success=success,
                error_message=None if success else f"Exceeded {self.max_response_time}s limit"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            result = PerformanceResult(
                operation_name=operation_name,
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
        
        self.results.append(result)
        return result
    
    async def measure_batch_operation(
        self,
        operation: Callable,
        batch_size: int,
        max_batch_time: float,
        operation_name: str
    ) -> PerformanceResult:
        """Measure batch operation performance."""
        start_time = time.time()
        try:
            # Create batch data
            batch_data = [f"test_item_{i}" for i in range(batch_size)]
            await operation(batch_data)
            
            execution_time = time.time() - start_time
            success = execution_time <= max_batch_time
            result = PerformanceResult(
                operation_name=f"{operation_name}_batch_{batch_size}",
                execution_time=execution_time,
                success=success,
                error_message=None if success else f"Batch exceeded {max_batch_time}s limit"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            result = PerformanceResult(
                operation_name=f"{operation_name}_batch_{batch_size}",
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
        
        self.results.append(result)
        return result
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all performance test results."""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        avg_time = sum(r.execution_time for r in self.results) / total_tests if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "average_execution_time": avg_time,
            "failed_operations": [r for r in self.results if not r.success]
        }
```

## Error Handling

### Test Error Management

```python
# helpers/error_helpers.py
import logging
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

class TestErrorHandler:
    """Centralized test error handling and logging."""
    
    def __init__(self):
        self.logger = logging.getLogger("test_suite")
        self.error_count = 0
        self.errors: List[Dict[str, Any]] = []
    
    def log_test_error(
        self,
        test_name: str,
        error: Exception,
        context: Dict[str, Any] = None
    ) -> None:
        """Log test error with context information."""
        self.error_count += 1
        error_info = {
            "test_name": test_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        self.errors.append(error_info)
        self.logger.error(f"Test failed: {test_name} - {error}", extra=context)
    
    @asynccontextmanager
    async def capture_async_errors(self, test_name: str):
        """Context manager for capturing async test errors."""
        try:
            yield
        except Exception as e:
            self.log_test_error(test_name, e)
            raise
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all test errors."""
        return {
            "total_errors": self.error_count,
            "error_details": self.errors,
            "most_common_errors": self._get_most_common_errors()
        }
    
    def _get_most_common_errors(self) -> Dict[str, int]:
        """Get count of most common error types."""
        error_types = {}
        for error in self.errors:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        return dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True))
```

## Testing Strategy

### Test Categories and Coverage

```python
# Test coverage requirements by category
COVERAGE_REQUIREMENTS = {
    "unit_tests": {
        "minimum_coverage": 85,
        "critical_paths": 100,  # AI services, auth, data processing
        "excluded_patterns": ["*/tests/*", "*/migrations/*", "*/conftest.py"]
    },
    "integration_tests": {
        "api_endpoints": 100,  # All endpoints must have integration tests
        "service_integration": 90,
        "database_operations": 95
    },
    "e2e_tests": {
        "user_workflows": 100,  # All major user journeys
        "multi_tenant": 100,
        "performance_critical": 100
    }
}

# Performance requirements by operation type
PERFORMANCE_REQUIREMENTS = {
    "api_simple": 0.5,      # Simple API calls < 500ms
    "api_ai": 3.0,          # AI operations < 3s
    "batch_500": 60.0,      # 500 reviews < 60s
    "dashboard_load": 0.5,   # Dashboard < 500ms
    "database_query": 0.1    # Database queries < 100ms
}
```

### Test Execution Strategy

```python
# pytest.ini configuration
[tool:pytest]
asyncio_mode = auto
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    --maxfail=10
    --tb=short
    -v
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (API endpoints)
    e2e: End-to-end tests (complete workflows)
    performance: Performance and load tests
    slow: Tests that take more than 5 seconds
    external: Tests that require external services
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

This design provides a comprehensive framework for fixing and enhancing the test suite while maintaining high code quality and performance standards.
</content>