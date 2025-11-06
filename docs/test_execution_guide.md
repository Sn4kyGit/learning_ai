# Test Execution Guide - Local Development Setup

## Overview

This guide provides comprehensive instructions for setting up and running the test suite in your local development environment. The Local Business Intelligence Bot uses a multi-layered testing approach with unit, integration, and end-to-end tests.

## Prerequisites

### System Requirements
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- Docker (optional, for containerized testing)

### Environment Setup

1. **Clone and Setup Repository**
```bash
git clone <repository-url>
cd local-business-intelligence-bot
```

2. **Backend Setup**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx
```

3. **Frontend Setup**
```bash
cd frontend
npm install
npm install --save-dev vitest @vue/test-utils jsdom
```

4. **Database Setup**
```bash
# Create test database
createdb businessbot_test

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/businessbot_test"
export REDIS_URL="redis://localhost:6379/1"
export ENVIRONMENT="test"
```

5. **Environment Configuration**
```bash
# Copy environment files
cp .env.example .env
cp frontend/.env.example frontend/.env

# Update .env with test configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/businessbot_test
REDIS_URL=redis://localhost:6379/1
OPENAI_API_KEY=test_key_for_mocking
ANTHROPIC_API_KEY=test_key_for_mocking
GOOGLE_PLACES_API_KEY=test_key_for_mocking
```

## Running Tests

### Backend Tests

#### Quick Test Execution
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html --cov-report=term-missing

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m e2e                    # End-to-end tests only
pytest -m "not slow"             # Exclude slow tests
```

#### Detailed Test Execution
```bash
# Run tests with verbose output
pytest -v

# Run tests with detailed failure information
pytest --tb=long

# Run tests and stop on first failure
pytest -x

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run specific test file
pytest backend/tests/unit/test_auth_service.py

# Run specific test class
pytest backend/tests/unit/test_auth_service.py::TestAuthService

# Run specific test method
pytest backend/tests/unit/test_auth_service.py::TestAuthService::test_login_success
```

#### Performance and Load Testing
```bash
# Run performance tests
pytest -m performance

# Run load testing
python backend/tests/performance/load_testing.py

# Run with performance profiling
pytest --profile-svg backend/tests/unit/test_ai_service_factory.py
```

### Frontend Tests

#### Vue.js Component Tests
```bash
cd frontend

# Run all frontend tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm run test src/test/components/BusinessRegistrationModal.test.ts

# Run tests matching pattern
npm run test -- --reporter=verbose --run src/test/services/
```

#### End-to-End Frontend Tests
```bash
# Run E2E tests
npm run test:e2e

# Run E2E tests in headless mode
npm run test:e2e:headless
```

### Integrated Test Execution

#### Full Test Suite
```bash
# Run comprehensive test suite (backend + frontend)
python scripts/run_comprehensive_tests.py

# Run with coverage analysis
python scripts/run_coverage_suite.py

# Run E2E tests across both backend and frontend
python scripts/run_e2e_tests.py
```

#### CI/CD Simulation
```bash
# Simulate CI/CD pipeline locally
python scripts/coverage_ci_integration.py

# Run critical path validation
python scripts/critical_path_validator.py

# Collect test artifacts
python scripts/test_artifact_collector.py
```

## Test Database Management

### Database Setup and Cleanup
```bash
# Create fresh test database
dropdb businessbot_test --if-exists
createdb businessbot_test

# Run migrations on test database
alembic -c alembic.ini upgrade head

# Reset test database between test runs
pytest --create-db --reuse-db
```

### Test Data Management
```bash
# Seed test database with fixtures
python -c "
from backend.tests.fixtures.database_seeding import seed_test_database
import asyncio
asyncio.run(seed_test_database())
"

# Clean test data
python -c "
from backend.tests.fixtures.database_seeding import clean_test_database
import asyncio
asyncio.run(clean_test_database())
"
```

## Mock Services Configuration

### AI Services Mocking
```python
# Set environment variables for mocking
export AI_SERVICES_MOCK=true
export OPENAI_API_KEY=mock_key
export ANTHROPIC_API_KEY=mock_key

# Or configure in test files
@pytest.fixture
def mock_ai_services():
    with patch('backend.ai.gpt5_classifier.GPT5NanoClassifier') as mock_gpt, \
         patch('backend.ai.claude_advisor.ClaudeHaikuAdvisor') as mock_claude:
        yield {
            'gpt5': mock_gpt,
            'claude': mock_claude
        }
```

### External API Mocking
```python
# Mock Google Places API
@pytest.fixture
def mock_google_places():
    with patch('backend.external.google_places.GooglePlacesClient') as mock:
        mock.return_value.search_places.return_value = [
            {"place_id": "test123", "name": "Test Restaurant"}
        ]
        yield mock
```

## Debugging Tests

### Debug Configuration
```bash
# Run tests with Python debugger
pytest --pdb

# Run tests with debugger on failure
pytest --pdb-trace

# Run single test with debugging
pytest -s backend/tests/unit/test_auth_service.py::TestAuthService::test_login_success
```

### Logging Configuration
```python
# Enable debug logging in tests
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use pytest logging
pytest --log-cli-level=DEBUG
```

### IDE Integration

#### VS Code Configuration
```json
// .vscode/settings.json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "backend/tests"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.autoTestDiscoverOnSaveEnabled": true
}
```

#### PyCharm Configuration
1. Go to Settings → Tools → Python Integrated Tools
2. Set Default test runner to pytest
3. Set Working directory to project root
4. Add environment variables in run configuration

## Performance Monitoring

### Test Execution Time
```bash
# Monitor test execution time
pytest --durations=10

# Profile slow tests
pytest --profile --profile-svg

# Set timeout for tests
pytest --timeout=300
```

### Memory Usage Monitoring
```bash
# Monitor memory usage
pytest --memray

# Profile memory leaks
python -m pytest --memray-bin-path=./memray-results backend/tests/
```

## Continuous Integration Setup

### GitHub Actions Integration
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=backend --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Local CI Simulation
```bash
# Run tests as they would run in CI
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Or use act to run GitHub Actions locally
act -j test
```

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check database exists
psql -l | grep businessbot_test

# Reset database connection
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/businessbot_test"
```

#### Async Test Issues
```python
# Ensure proper async test configuration
# In conftest.py
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Mark async tests properly
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

#### Mock Configuration Issues
```python
# Ensure mocks are properly configured
@pytest.fixture
def mock_service():
    with patch('backend.services.some_service.SomeService') as mock:
        mock.return_value.method.return_value = "expected_result"
        yield mock

# Use AsyncMock for async methods
from unittest.mock import AsyncMock
mock_service.async_method = AsyncMock(return_value="result")
```

### Performance Issues
```bash
# Identify slow tests
pytest --durations=0

# Run tests in parallel
pytest -n auto

# Use faster test database
export DATABASE_URL="sqlite+aiosqlite:///test.db"
```

### Coverage Issues
```bash
# Check coverage configuration
cat .coveragerc

# Generate detailed coverage report
pytest --cov=backend --cov-report=html --cov-branch

# Identify uncovered lines
pytest --cov=backend --cov-report=term-missing
```

## Best Practices

### Test Organization
- Keep test files under 500 lines
- Use descriptive test class and method names
- Follow Arrange-Act-Assert pattern
- Group related tests in classes
- Use fixtures for common setup

### Test Data Management
- Use factories for test data creation
- Clean up test data after each test
- Use database transactions for isolation
- Mock external services consistently

### Performance Optimization
- Run unit tests frequently (they should be fast)
- Run integration tests before commits
- Run E2E tests before releases
- Use parallel execution for large test suites
- Profile and optimize slow tests

### Maintenance
- Update test dependencies regularly
- Review and refactor tests with code changes
- Monitor test execution time trends
- Keep test documentation current
- Remove obsolete tests promptly

This guide should help you set up and run tests effectively in your local development environment. For specific issues not covered here, refer to the troubleshooting guide or consult the project's test maintenance procedures.