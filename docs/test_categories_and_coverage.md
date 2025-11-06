# Test Categories and Coverage Requirements

## Overview

This document defines the test categories, coverage requirements, and quality standards for the Local Business Intelligence Bot project. All tests must meet these requirements to ensure comprehensive validation of system functionality and maintain high code quality.

## Test Categories

### 1. Unit Tests (backend/tests/unit/)

#### Definition
Unit tests validate individual components in isolation, with all external dependencies mocked. They focus on testing single functions, methods, or classes without any external system interactions.

#### Characteristics
- **Execution Time**: < 100ms per test
- **Isolation**: Complete isolation from external systems
- **Dependencies**: All dependencies mocked using unittest.mock or pytest-mock
- **Scope**: Single class, function, or module
- **Database**: No database connections (use mocks)
- **Network**: No network calls (use mocks)
- **File System**: No file system access (use mocks)

#### Coverage Requirements
```python
UNIT_TEST_COVERAGE = {
    "minimum_coverage": 85,           # 85% line coverage minimum
    "critical_paths": 100,            # 100% for AI services, auth, data processing
    "branch_coverage": 80,            # 80% branch coverage
    "excluded_patterns": [
        "*/tests/*",                  # Exclude test files
        "*/migrations/*",             # Exclude database migrations
        "*/conftest.py",              # Exclude test configuration
        "*/main.py",                  # Exclude FastAPI app entry point
        "*/__init__.py"               # Exclude init files
    ]
}
```

#### Critical Path Components (100% Coverage Required)
```python
CRITICAL_PATHS = [
    # AI Services
    "backend/ai/gpt5_classifier.py",
    "backend/ai/claude_advisor.py", 
    "backend/ai/cost_tracker.py",
    "backend/ai/language_detector.py",
    
    # Authentication & Authorization
    "backend/services/auth_service.py",
    "backend/services/auth_dependencies.py",
    "backend/services/user_management_service.py",
    
    # Data Processing
    "backend/services/review/processor.py",
    "backend/services/analytics/calculator.py",
    "backend/db/repositories/base.py",
    "backend/db/repositories/business.py",
    "backend/db/repositories/review.py",
    
    # External Integrations
    "backend/external/google_places.py",
    "backend/external/base_client.py"
]
```

#### Example Unit Test Structure
```python
class TestReviewClassificationService:
    """Unit tests for review classification service."""
    
    @pytest.fixture
    def mock_dependencies(self) -> Dict[str, Mock]:
        """Provide all mocked dependencies."""
        return {
            'gpt5_classifier': Mock(spec=GPT5NanoClassifier),
            'repository': Mock(spec=ReviewRepositoryProtocol),
            'cost_tracker': Mock(spec=CostTracker)
        }
    
    @pytest.fixture
    def service(self, mock_dependencies: Dict[str, Mock]) -> ReviewClassificationService:
        """Create service with mocked dependencies."""
        return ReviewClassificationService(
            classifier=mock_dependencies['gpt5_classifier'],
            repository=mock_dependencies['repository'],
            cost_tracker=mock_dependencies['cost_tracker']
        )
    
    def test_classify_review_success_returns_classification(self, service, mock_dependencies):
        """Test successful review classification returns proper result."""
        # Arrange
        review_text = "Great food and excellent service!"
        expected_classification = ClassificationResult(
            sentiment="positive",
            topics=["food_quality", "service"],
            confidence_score=0.95
        )
        mock_dependencies['gpt5_classifier'].classify_review.return_value = expected_classification
        
        # Act
        result = service.classify_review(review_text)
        
        # Assert
        assert result.sentiment == "positive"
        assert "food_quality" in result.topics
        assert result.confidence_score >= 0.9
        mock_dependencies['gpt5_classifier'].classify_review.assert_called_once_with(review_text)
```

### 2. Integration Tests (backend/tests/integration/)

#### Definition
Integration tests validate the interaction between different system components, including API endpoints, database operations, and service integrations. They use real database connections but mock external APIs.

#### Characteristics
- **Execution Time**: < 5 seconds per test
- **Database**: Real test database connections
- **API Endpoints**: Test actual FastAPI endpoints
- **Authentication**: Real JWT token validation
- **External APIs**: Mocked (Google Places, OpenAI, Anthropic)
- **Services**: Real service layer interactions

#### Coverage Requirements
```python
INTEGRATION_TEST_COVERAGE = {
    "api_endpoints": 100,             # All API endpoints must have integration tests
    "service_integration": 90,        # 90% coverage for service interactions
    "database_operations": 95,        # 95% coverage for database operations
    "authentication_flows": 100,      # 100% coverage for auth flows
    "error_handling": 85             # 85% coverage for error scenarios
}
```

#### Required Integration Test Categories
```python
INTEGRATION_TEST_CATEGORIES = {
    "api_endpoints": [
        "test_auth_endpoints.py",           # Authentication API tests
        "test_business_endpoints.py",       # Business management API tests
        "test_chat_endpoints.py",           # AI chat API tests
        "test_analytics_endpoints.py",      # Analytics API tests
        "test_notifications_endpoints.py",  # Notification API tests
        "test_reports_endpoints.py"         # Report generation API tests
    ],
    
    "service_integration": [
        "test_ai_integration.py",           # AI service integration
        "test_database_integration.py",     # Database service integration
        "test_google_places_integration.py", # Google Places integration
        "test_backup_integration.py",       # Backup service integration
        "test_gdpr_compliance_integration.py" # GDPR compliance integration
    ],
    
    "workflow_integration": [
        "test_review_processing_integration.py", # Review processing workflow
        "test_analytics_integration.py",         # Analytics calculation workflow
        "test_alert_notification_integration.py" # Alert notification workflow
    ]
}
```

#### Example Integration Test Structure
```python
class TestBusinessEndpoints:
    """Integration tests for business management API endpoints."""
    
    @pytest.fixture
    async def authenticated_client(self, test_client: AsyncClient, test_db: AsyncSession) -> AsyncClient:
        """Provide authenticated test client with real JWT token."""
        # Create and authenticate user
        user = await create_test_user(test_db, role="business_owner")
        token = await authenticate_user(test_client, user.email, "testpassword")
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        return test_client
    
    async def test_create_business_endpoint_success(
        self, 
        authenticated_client: AsyncClient, 
        test_db: AsyncSession,
        mock_google_places: Mock
    ):
        """Test business creation endpoint with valid data."""
        # Arrange
        business_data = {
            "name": "Test Restaurant",
            "google_place_id": "ChIJ123abc",
            "address": "123 Main St, City, State"
        }
        mock_google_places.get_place_details.return_value = {
            "name": "Test Restaurant",
            "formatted_address": "123 Main St, City, State",
            "rating": 4.5
        }
        
        # Act
        response = await authenticated_client.post("/api/businesses", json=business_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == business_data["name"]
        assert data["google_place_id"] == business_data["google_place_id"]
        
        # Verify database persistence
        business = await test_db.get(Business, data["id"])
        assert business is not None
        assert business.name == business_data["name"]
```

### 3. End-to-End Tests (backend/tests/e2e/)

#### Definition
End-to-end tests validate complete user workflows from start to finish, testing the entire system as users would interact with it. They simulate real user scenarios and validate the complete data flow.

#### Characteristics
- **Execution Time**: < 30 seconds per test
- **User Workflows**: Complete user journeys
- **Data Flow**: Data flows through all system layers
- **Multi-Service**: Tests interactions between multiple services
- **Real Scenarios**: Based on actual user behavior patterns

#### Coverage Requirements
```python
E2E_TEST_COVERAGE = {
    "user_workflows": 100,            # All major user journeys
    "multi_tenant": 100,              # Multi-tenant functionality
    "performance_critical": 100,      # Performance-critical operations
    "error_recovery": 80,             # Error recovery scenarios
    "cross_service": 90               # Cross-service interactions
}
```

#### Required E2E Test Scenarios
```python
E2E_TEST_SCENARIOS = [
    # Complete User Workflows
    "test_complete_user_workflows.py",      # Full user journey tests
    
    # Performance and Scalability
    "test_performance_optimization.py",     # Performance requirement validation
    "test_database_optimization.py",        # Database performance tests
    
    # Deployment and Operations
    "test_deployment_scenarios.py",         # Deployment validation tests
    
    # Summary and Reporting
    "test_summary_report.py"               # End-to-end reporting tests
]
```

#### Example E2E Test Structure
```python
class TestCompleteUserWorkflow:
    """End-to-end tests for complete user workflows."""
    
    async def test_business_owner_complete_journey(
        self, 
        test_client: AsyncClient, 
        test_db: AsyncSession,
        mock_external_services: Dict[str, Mock]
    ):
        """Test complete business owner journey from registration to insights."""
        
        # Step 1: User Registration
        registration_data = {
            "email": "owner@restaurant.com",
            "password": "securepassword",
            "full_name": "Restaurant Owner",
            "role": "business_owner"
        }
        register_response = await test_client.post("/auth/register", json=registration_data)
        assert register_response.status_code == 201
        
        # Step 2: User Login
        login_response = await test_client.post("/auth/login", json={
            "email": registration_data["email"],
            "password": registration_data["password"]
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Step 3: Business Registration
        business_data = {
            "name": "Amazing Restaurant",
            "google_place_id": "ChIJ123abc",
            "address": "123 Main St, City, State"
        }
        business_response = await test_client.post("/api/businesses", json=business_data)
        assert business_response.status_code == 201
        business_id = business_response.json()["id"]
        
        # Step 4: Review Import
        mock_external_services['google_places'].get_reviews.return_value = [
            {"text": "Excellent food!", "rating": 5, "author": "John D."},
            {"text": "Slow service", "rating": 2, "author": "Jane S."},
            {"text": "Great atmosphere", "rating": 4, "author": "Mike R."}
        ]
        
        import_response = await test_client.post(f"/api/businesses/{business_id}/import-reviews")
        assert import_response.status_code == 200
        assert import_response.json()["imported_count"] == 3
        
        # Step 5: Analytics Generation
        # Wait for async processing
        await asyncio.sleep(1)
        
        analytics_response = await test_client.get(f"/api/analytics/{business_id}")
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        
        # Verify analytics structure
        assert "sentiment_distribution" in analytics_data
        assert "topic_analysis" in analytics_data
        assert analytics_data["total_reviews"] == 3
        
        # Step 6: AI Chat Interaction
        chat_payload = {"message": "How is my restaurant performing?"}
        chat_response = await test_client.post(f"/api/chat/{business_id}", json=chat_payload)
        assert chat_response.status_code == 200
        assert len(chat_response.json()["response"]) > 0
        
        # Step 7: Report Generation
        report_response = await test_client.post(f"/api/reports/{business_id}/weekly")
        assert report_response.status_code == 200
        report_data = report_response.json()
        assert "summary" in report_data
        assert "action_items" in report_data
```

### 4. Performance Tests (backend/tests/performance/)

#### Definition
Performance tests validate that the system meets response time and throughput requirements under various load conditions.

#### Performance Requirements
```python
PERFORMANCE_REQUIREMENTS = {
    "api_simple": 0.5,              # Simple API calls < 500ms
    "api_ai": 3.0,                  # AI operations < 3s
    "batch_500": 60.0,              # 500 reviews < 60s
    "dashboard_load": 0.5,          # Dashboard < 500ms
    "database_query": 0.1,          # Database queries < 100ms
    "concurrent_users": 50,         # Support 50 concurrent users
    "memory_usage": "512MB",        # Max memory usage per process
    "cpu_usage": "80%"              # Max CPU usage under load
}
```

#### Example Performance Test
```python
class TestPerformanceRequirements:
    """Performance tests for system requirements."""
    
    @pytest.fixture
    def performance_tester(self) -> PerformanceTester:
        """Provide performance testing utilities."""
        return PerformanceTester()
    
    async def test_api_response_time_requirements(
        self, 
        test_client: AsyncClient, 
        performance_tester: PerformanceTester
    ):
        """Test API endpoints meet response time requirements."""
        
        # Test simple API endpoint
        result = await performance_tester.measure_async_operation(
            operation=lambda: test_client.get("/api/health"),
            operation_name="health_check",
            max_time=0.5
        )
        assert result.success, f"Health check too slow: {result.execution_time}s"
        
        # Test AI operation
        result = await performance_tester.measure_async_operation(
            operation=lambda: test_client.post("/api/classify-reviews", json={
                "business_id": "test123",
                "reviews": ["Test review"]
            }),
            operation_name="ai_classification",
            max_time=3.0
        )
        assert result.success, f"AI classification too slow: {result.execution_time}s"
```

## Frontend Test Categories

### 1. Component Tests (frontend/src/test/components/)

#### Coverage Requirements
```javascript
const FRONTEND_COVERAGE_REQUIREMENTS = {
    component_rendering: 90,        // 90% component rendering coverage
    user_interactions: 85,          // 85% user interaction coverage
    props_validation: 95,           // 95% props validation coverage
    event_handling: 90,             // 90% event handling coverage
    state_management: 85            // 85% state management coverage
};
```

#### Example Component Test
```javascript
describe('BusinessRegistrationModal', () => {
  it('should render form fields correctly', async () => {
    // Arrange
    const wrapper = mount(BusinessRegistrationModal, {
      props: { isVisible: true }
    });
    
    // Act
    await nextTick();
    
    // Assert
    expect(wrapper.find('[data-testid="business-name-input"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="address-input"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="submit-button"]').exists()).toBe(true);
  });
  
  it('should validate required fields on submit', async () => {
    // Arrange
    const wrapper = mount(BusinessRegistrationModal, {
      props: { isVisible: true }
    });
    
    // Act
    await wrapper.find('[data-testid="submit-button"]').trigger('click');
    await nextTick();
    
    // Assert
    expect(wrapper.find('.error-message').text()).toContain('Business name is required');
  });
});
```

### 2. Service Tests (frontend/src/test/services/)

#### Coverage Requirements
```javascript
const SERVICE_COVERAGE_REQUIREMENTS = {
    api_calls: 100,                 // 100% API call coverage
    error_handling: 90,             // 90% error handling coverage
    data_transformation: 95,        // 95% data transformation coverage
    authentication: 100             // 100% authentication coverage
};
```

### 3. Store Tests (frontend/src/test/stores/)

#### Coverage Requirements
```javascript
const STORE_COVERAGE_REQUIREMENTS = {
    state_mutations: 100,           // 100% state mutation coverage
    getters: 95,                    // 95% getter coverage
    actions: 90,                    // 90% action coverage
    persistence: 85                 // 85% persistence coverage
};
```

## Coverage Analysis and Reporting

### Coverage Configuration (.coveragerc)
```ini
[run]
source = backend
omit = 
    backend/tests/*
    backend/migrations/*
    backend/conftest.py
    backend/main.py
    */__init__.py
    */venv/*
    */node_modules/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod

[html]
directory = htmlcov
```

### Coverage Thresholds by Component
```python
COVERAGE_THRESHOLDS = {
    # Critical Components (100% required)
    "backend/ai/": 100,
    "backend/services/auth_service.py": 100,
    "backend/db/repositories/": 100,
    
    # Core Components (90% required)
    "backend/services/": 90,
    "backend/routes/": 90,
    "backend/external/": 90,
    
    # Supporting Components (80% required)
    "backend/middleware/": 80,
    "backend/config.py": 80,
    
    # Overall Project Minimum
    "overall": 80
}
```

### Coverage Reporting Commands
```bash
# Generate coverage report
pytest --cov=backend --cov-report=html --cov-report=term-missing --cov-fail-under=80

# Generate branch coverage
pytest --cov=backend --cov-branch --cov-report=html

# Generate coverage for specific component
pytest --cov=backend/ai --cov-report=term-missing backend/tests/unit/test_ai_*

# Coverage with exclusions
pytest --cov=backend --cov-report=html --cov-config=.coveragerc
```

### Critical Path Coverage Validation
```python
# scripts/critical_path_validator.py
CRITICAL_PATHS_100_PERCENT = [
    "backend/ai/gpt5_classifier.py",
    "backend/ai/claude_advisor.py",
    "backend/services/auth_service.py",
    "backend/db/repositories/base.py"
]

def validate_critical_path_coverage():
    """Validate 100% coverage for critical paths."""
    for path in CRITICAL_PATHS_100_PERCENT:
        coverage = get_file_coverage(path)
        if coverage < 100:
            raise CoverageError(f"{path} has {coverage}% coverage, requires 100%")
```

## Quality Gates and CI/CD Integration

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-coverage
        name: pytest coverage check
        entry: pytest --cov=backend --cov-fail-under=80
        language: system
        pass_filenames: false
        
      - id: critical-path-coverage
        name: critical path coverage validation
        entry: python scripts/critical_path_validator.py
        language: system
        pass_filenames: false
```

### GitHub Actions Integration
```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    pytest --cov=backend --cov-report=xml --cov-fail-under=80
    
- name: Validate critical path coverage
  run: |
    python scripts/critical_path_validator.py
    
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
    fail_ci_if_error: true
```

### Coverage Trend Monitoring
```python
# Monitor coverage trends over time
COVERAGE_HISTORY = {
    "target_trend": "increasing",    # Coverage should increase over time
    "minimum_change": -2,            # Max 2% decrease allowed
    "alert_threshold": 75,           # Alert if below 75%
    "critical_threshold": 70         # Fail CI if below 70%
}
```

This comprehensive coverage framework ensures high-quality testing across all system components while maintaining performance and maintainability standards.