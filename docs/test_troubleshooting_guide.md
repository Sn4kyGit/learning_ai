# Test Troubleshooting Guide - Common Test Failures

## Overview

This guide provides solutions for common test failures encountered in the Local Business Intelligence Bot project. It covers async/await issues, database problems, mock configurations, and performance-related failures with step-by-step resolution instructions.

## Common Test Failure Categories

### 1. Async/Await Related Issues

#### Problem: "RuntimeError: This event loop is already running"
```
RuntimeError: This event loop is already running
    at async def test_async_function():
```

**Root Cause**: Attempting to run async code in an already running event loop or improper pytest-asyncio configuration.

**Solution**:
```python
# Fix 1: Ensure proper pytest configuration
# pytest.ini
[tool:pytest]
asyncio_mode = auto

# Fix 2: Use proper async test fixtures
# conftest.py
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Fix 3: Mark async tests properly
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

#### Problem: "TypeError: object AsyncMock can't be used in 'await' expression"
```
TypeError: object AsyncMock can't be used in 'await' expression
```

**Root Cause**: Using regular Mock instead of AsyncMock for async methods.

**Solution**:
```python
# Wrong - Using regular Mock
mock_service = Mock()
mock_service.async_method.return_value = "result"

# Correct - Using AsyncMock
from unittest.mock import AsyncMock

mock_service = AsyncMock()
mock_service.async_method.return_value = "result"

# Or for specific methods
mock_service = Mock()
mock_service.async_method = AsyncMock(return_value="result")
```

#### Problem: "coroutine was never awaited" warnings
```
RuntimeWarning: coroutine 'test_function' was never awaited
```

**Root Cause**: Async function not properly awaited or missing async/await keywords.

**Solution**:
```python
# Wrong - Missing await
async def test_async_operation():
    result = some_async_function()  # Missing await
    assert result is not None

# Correct - Proper await usage
async def test_async_operation():
    result = await some_async_function()
    assert result is not None

# Wrong - Missing async in test definition
def test_async_operation():  # Missing async keyword
    result = await some_async_function()

# Correct - Proper async test definition
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
```

### 2. Database Related Issues

#### Problem: "sqlalchemy.exc.InvalidRequestError: Object is not bound to a Session"
```
sqlalchemy.exc.InvalidRequestError: Object '<Business at 0x...>' is not bound to a Session
```

**Root Cause**: Attempting to access database object attributes outside of session scope.

**Solution**:
```python
# Wrong - Accessing object after session closed
async def test_business_creation():
    async with AsyncSession() as session:
        business = Business(name="Test")
        session.add(business)
        await session.commit()
    
    # Session is closed here
    assert business.name == "Test"  # Error: not bound to session

# Correct - Access within session or refresh object
async def test_business_creation():
    async with AsyncSession() as session:
        business = Business(name="Test")
        session.add(business)
        await session.commit()
        await session.refresh(business)  # Refresh to load data
        
        # Access within session
        assert business.name == "Test"

# Alternative - Use expunge to detach from session
async def test_business_creation():
    async with AsyncSession() as session:
        business = Business(name="Test")
        session.add(business)
        await session.commit()
        await session.refresh(business)
        session.expunge(business)  # Detach from session
    
    # Now can access outside session
    assert business.name == "Test"
```

#### Problem: "asyncpg.exceptions.ConnectionDoesNotExistError"
```
asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation
```

**Root Cause**: Database connection closed prematurely or connection pool exhausted.

**Solution**:
```python
# Fix 1: Proper session management in conftest.py
@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide clean test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session with proper lifecycle
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()  # Ensure rollback
            await session.close()     # Explicit close
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

# Fix 2: Proper connection pool configuration
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,           # Increase pool size
    max_overflow=30,        # Allow overflow connections
    pool_timeout=30,        # Connection timeout
    pool_recycle=3600       # Recycle connections hourly
)
```

#### Problem: "psycopg2.errors.DuplicateDatabase: database already exists"
```
psycopg2.errors.DuplicateDatabase: database "businessbot_test" already exists
```

**Root Cause**: Test database not properly cleaned up between test runs.

**Solution**:
```bash
# Fix 1: Manual cleanup
dropdb businessbot_test --if-exists
createdb businessbot_test

# Fix 2: Automated cleanup in conftest.py
@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Setup and cleanup test database."""
    # Drop existing test database
    subprocess.run(["dropdb", "businessbot_test", "--if-exists"], check=False)
    
    # Create fresh test database
    subprocess.run(["createdb", "businessbot_test"], check=True)
    
    yield
    
    # Cleanup after all tests
    subprocess.run(["dropdb", "businessbot_test", "--if-exists"], check=False)

# Fix 3: Use pytest-postgresql for automatic database management
pip install pytest-postgresql

# In conftest.py
from pytest_postgresql import factories

postgresql_proc = factories.postgresql_proc(
    port=None,
    unixsocketdir='/tmp'
)
postgresql = factories.postgresql('postgresql_proc')
```

### 3. Mock Configuration Issues

#### Problem: "AttributeError: Mock object has no attribute 'return_value'"
```
AttributeError: Mock object has no attribute 'return_value'
```

**Root Cause**: Incorrect mock configuration or accessing non-existent mock attributes.

**Solution**:
```python
# Wrong - Incorrect mock setup
mock_service = Mock()
mock_service.method.return_value.attribute = "value"  # Error if method not called

# Correct - Proper mock configuration
mock_service = Mock()
mock_service.method.return_value = Mock(attribute="value")

# Or use spec for better validation
mock_service = Mock(spec=SomeService)
mock_service.method.return_value = Mock(attribute="value")

# For nested attributes
mock_service = Mock()
mock_service.method.return_value.attribute.value = "test"
```

#### Problem: "AssertionError: Expected call not found"
```
AssertionError: Expected call not found. Expected: call.method('arg')
Actual calls: [call.method('different_arg')]
```

**Root Cause**: Mock assertion doesn't match actual method calls.

**Solution**:
```python
# Debug mock calls
mock_service = Mock()
# ... test code ...
print(f"Mock calls: {mock_service.method.call_args_list}")

# Use ANY for flexible matching
from unittest.mock import ANY
mock_service.method.assert_called_with(ANY, specific_arg="value")

# Use call objects for complex assertions
from unittest.mock import call
expected_calls = [
    call.method("arg1"),
    call.method("arg2")
]
mock_service.assert_has_calls(expected_calls)

# Check if method was called at all
assert mock_service.method.called
assert mock_service.method.call_count == 2
```

#### Problem: "Mock object is not callable"
```
TypeError: 'Mock' object is not callable
```

**Root Cause**: Attempting to call a Mock that wasn't configured as callable.

**Solution**:
```python
# Wrong - Mock not configured as callable
mock_function = Mock()
result = mock_function()  # Error: not callable

# Correct - Configure mock as callable
mock_function = Mock(return_value="result")
result = mock_function()  # Works

# Or use side_effect for dynamic behavior
mock_function = Mock(side_effect=lambda x: f"processed_{x}")
result = mock_function("input")  # Returns "processed_input"
```

### 4. API Testing Issues

#### Problem: "httpx.ConnectError: All connection attempts failed"
```
httpx.ConnectError: [Errno 61] Connection refused
```

**Root Cause**: Test client not properly configured or FastAPI app not available.

**Solution**:
```python
# Fix 1: Proper test client configuration in conftest.py
@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide test client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Fix 2: Ensure app dependencies are overridden
@pytest.fixture
async def test_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide test client with database override."""
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()
```

#### Problem: "422 Unprocessable Entity" for valid requests
```
422 Unprocessable Entity: {"detail": [{"type": "missing", "loc": ["body", "field"]}]}
```

**Root Cause**: Request payload doesn't match Pydantic schema expectations.

**Solution**:
```python
# Debug request/response
async def test_api_endpoint():
    payload = {"field": "value"}
    response = await client.post("/api/endpoint", json=payload)
    
    # Debug response
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Check if payload matches schema
    from backend.db.schemas import SomeSchema
    try:
        validated = SomeSchema(**payload)
        print(f"Validation successful: {validated}")
    except ValidationError as e:
        print(f"Validation error: {e}")

# Fix common validation issues
# Wrong - Missing required fields
payload = {"optional_field": "value"}

# Correct - Include all required fields
payload = {
    "required_field": "value",
    "optional_field": "value"
}

# Wrong - Incorrect data types
payload = {"numeric_field": "string_value"}

# Correct - Proper data types
payload = {"numeric_field": 123}
```

### 5. Performance Test Issues

#### Problem: "AssertionError: Operation took 2.5s, expected <0.5s"
```
AssertionError: Operation took 2.5s, expected <0.5s
```

**Root Cause**: Performance requirements not met due to inefficient code or test environment.

**Solution**:
```python
# Fix 1: Profile slow operations
import cProfile
import pstats

def test_performance_with_profiling():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run slow operation
    result = slow_operation()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Show top 10 slow functions

# Fix 2: Use appropriate test environment
# Don't run performance tests with debug logging enabled
import logging
logging.getLogger().setLevel(logging.WARNING)

# Use faster test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///test.db"  # Faster than PostgreSQL for tests

# Fix 3: Optimize test data
# Use smaller datasets for performance tests
test_data = create_test_reviews(count=10)  # Instead of 1000

# Fix 4: Mock expensive operations
@patch('backend.external.google_places.GooglePlacesClient')
def test_performance_with_mocks(mock_client):
    mock_client.return_value.get_reviews.return_value = []  # Instant response
    # Test performance of internal logic only
```

#### Problem: "TimeoutError: Operation timed out after 5.0 seconds"
```
asyncio.TimeoutError: Operation timed out after 5.0 seconds
```

**Root Cause**: Async operation taking longer than expected timeout.

**Solution**:
```python
# Fix 1: Increase timeout for legitimate slow operations
async def test_slow_operation():
    try:
        result = await asyncio.wait_for(slow_async_operation(), timeout=30.0)
    except asyncio.TimeoutError:
        pytest.fail("Operation timed out - investigate performance issue")

# Fix 2: Mock slow external services
@patch('backend.ai.gpt5_classifier.OpenAIClient')
async def test_with_mocked_ai(mock_client):
    # Mock returns immediately instead of waiting for API
    mock_client.return_value.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content='{"sentiment": "positive"}'))]
    )
    
    result = await fast_operation_with_mocked_ai()
    assert result is not None

# Fix 3: Use asyncio.gather for concurrent operations
async def test_concurrent_operations():
    # Run operations concurrently instead of sequentially
    tasks = [async_operation(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 10
```

### 6. Frontend Test Issues

#### Problem: "ReferenceError: document is not defined"
```
ReferenceError: document is not defined
```

**Root Cause**: DOM not available in test environment.

**Solution**:
```javascript
// Fix 1: Configure jsdom in vitest.config.ts
export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts']
  }
});

// Fix 2: Mock document in test setup
// src/test/setup.ts
import { vi } from 'vitest';

Object.defineProperty(window, 'document', {
  value: document,
  writable: true
});

// Fix 3: Use proper Vue Test Utils mounting
import { mount } from '@vue/test-utils';

describe('Component', () => {
  it('should render', () => {
    const wrapper = mount(Component, {
      global: {
        plugins: [router, pinia]
      }
    });
    expect(wrapper.exists()).toBe(true);
  });
});
```

#### Problem: "TypeError: Cannot read properties of undefined (reading 'push')"
```
TypeError: Cannot read properties of undefined (reading 'push')
```

**Root Cause**: Router not properly mocked in component tests.

**Solution**:
```javascript
// Fix 1: Mock router in test
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } }
  ]
});

const wrapper = mount(Component, {
  global: {
    plugins: [router]
  }
});

// Fix 2: Mock router methods specifically
const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  go: vi.fn(),
  back: vi.fn(),
  forward: vi.fn()
};

const wrapper = mount(Component, {
  global: {
    mocks: {
      $router: mockRouter
    }
  }
});
```

## Debugging Strategies

### 1. Verbose Test Output
```bash
# Run tests with maximum verbosity
pytest -vvv --tb=long

# Show local variables in tracebacks
pytest --tb=auto --showlocals

# Capture print statements
pytest -s

# Show warnings
pytest --disable-warnings
```

### 2. Interactive Debugging
```python
# Use pytest debugger
pytest --pdb

# Set breakpoint in test
def test_something():
    import pdb; pdb.set_trace()
    result = function_under_test()
    assert result is not None

# Use ipdb for better debugging experience
pip install ipdb
import ipdb; ipdb.set_trace()
```

### 3. Logging Configuration
```python
# Enable debug logging in tests
import logging
logging.basicConfig(level=logging.DEBUG)

# Or configure specific loggers
logging.getLogger('backend.services').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Use pytest logging
pytest --log-cli-level=DEBUG --log-cli-format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
```

### 4. Test Isolation Debugging
```python
# Run single test
pytest backend/tests/unit/test_auth_service.py::TestAuthService::test_login_success

# Run tests in random order to catch dependencies
pip install pytest-randomly
pytest --randomly-seed=12345

# Run tests multiple times to catch flaky tests
pytest --count=10 backend/tests/unit/test_auth_service.py
```

## Prevention Strategies

### 1. Test Code Reviews
- Review test code as thoroughly as production code
- Ensure proper mock configurations
- Verify test isolation and cleanup
- Check for proper async/await usage

### 2. Continuous Integration
```yaml
# .github/workflows/test.yml
- name: Run tests with retries
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: pytest --maxfail=5

- name: Run tests in parallel
  run: pytest -n auto --dist worksteal
```

### 3. Test Maintenance
- Regularly update test dependencies
- Monitor test execution times
- Remove obsolete tests
- Refactor tests when code changes
- Keep test documentation current

### 4. Quality Gates
```python
# Pre-commit hooks for test quality
repos:
  - repo: local
    hooks:
      - id: test-syntax
        name: Test syntax check
        entry: python -m py_compile
        language: system
        files: ^backend/tests/.*\.py$
        
      - id: test-imports
        name: Test import check
        entry: python -c "import sys; [__import__(f.replace('/', '.').replace('.py', '')) for f in sys.argv[1:]]"
        language: system
        files: ^backend/tests/.*\.py$
```

This troubleshooting guide should help you quickly identify and resolve common test issues. For complex problems not covered here, consider consulting the test maintenance procedures or seeking help from the development team.