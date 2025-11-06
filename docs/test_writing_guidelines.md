# Test Writing Guidelines - Project Standards

## Overview

This document provides comprehensive guidelines for writing tests in the Local Business Intelligence Bot project. All tests must follow OOP principles, maintain file size limits, and adhere to project coding standards while ensuring comprehensive coverage and maintainability.

## Test Architecture Principles

### Object-Oriented Test Design

#### Test Class Organization
```python
class TestReviewClassificationService:
    """Test suite for review classification service.
    
    Follows single responsibility principle - tests only classification logic.
    Each test method focuses on one specific behavior or scenario.
    """
    
    @pytest.fixture
    def mock_ai_client(self) -> Mock:
        """Provide mocked AI client for isolation."""
        return Mock(spec=ReviewClassifierProtocol)
    
    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Provide mocked repository for data access."""
        return Mock(spec=ReviewRepositoryProtocol)
    
    @pytest.fixture
    def service(self, mock_ai_client: Mock, mock_repository: Mock) -> ReviewClassificationService:
        """Provide service instance with injected dependencies."""
        return ReviewClassificationService(
            classifier=mock_ai_client,
            repository=mock_repository
        )
    
    def test_classify_positive_review_success(self, service: ReviewClassificationService, mock_ai_client: Mock):
        """Test successful classification of positive review."""
        # Arrange
        review_text = "Excellent food and outstanding service!"
        expected_classification = ClassificationResult(
            sentiment="positive",
            topics=["food_quality", "service"],
            confidence_score=0.95,
            urgency="low"
        )
        mock_ai_client.classify_review.return_value = expected_classification
        
        # Act
        result = service.classify_review(review_text)
        
        # Assert
        assert result.sentiment == "positive"
        assert "food_quality" in result.topics
        assert result.confidence_score >= 0.9
        mock_ai_client.classify_review.assert_called_once_with(review_text)
```

#### Dependency Injection in Tests
```python
class TestBusinessAdvisoryService:
    """Test business advisory service with proper dependency injection."""
    
    @pytest.fixture
    def dependencies(self) -> Dict[str, Mock]:
        """Provide all service dependencies as mocks."""
        return {
            'claude_advisor': Mock(spec=ClaudeHaikuAdvisor),
            'analytics_service': Mock(spec=AnalyticsService),
            'review_repository': Mock(spec=ReviewRepositoryProtocol),
            'cost_tracker': Mock(spec=CostTracker)
        }
    
    @pytest.fixture
    def service(self, dependencies: Dict[str, Mock]) -> BusinessAdvisoryService:
        """Create service with injected dependencies."""
        return BusinessAdvisoryService(
            advisor=dependencies['claude_advisor'],
            analytics=dependencies['analytics_service'],
            repository=dependencies['review_repository'],
            cost_tracker=dependencies['cost_tracker']
        )
```

### File Size and Organization Standards

#### Maximum File Sizes
- **Test files**: 500 lines maximum
- **Test classes**: 200 lines maximum  
- **Test methods**: 50 lines maximum
- **Setup/fixture methods**: 30 lines maximum

#### File Splitting Strategy
```python
# When test file approaches 500 lines, split by domain:

# test_auth_service.py (approaching limit)
# Split into:
# test_auth_login.py          - Login functionality tests
# test_auth_registration.py   - Registration tests  
# test_auth_password_reset.py - Password reset tests
# test_auth_permissions.py    - Permission and role tests

# Example split:
class TestAuthLogin:
    """Tests for authentication login functionality."""
    
    def test_login_with_valid_credentials_success(self):
        """Test successful login with valid email and password."""
        pass
    
    def test_login_with_invalid_password_fails(self):
        """Test login failure with incorrect password."""
        pass

class TestAuthRegistration:
    """Tests for user registration functionality."""
    
    def test_register_new_user_success(self):
        """Test successful registration of new user."""
        pass
```

## Test Categories and Implementation

### Unit Tests (backend/tests/unit/)

#### Characteristics
- **Isolation**: No external dependencies (database, APIs, file system)
- **Speed**: Execute in milliseconds
- **Scope**: Single class or function
- **Mocking**: All dependencies mocked

#### Implementation Pattern
```python
class TestReviewProcessor:
    """Unit tests for review processing logic."""
    
    @pytest.fixture
    def mock_classifier(self) -> AsyncMock:
        """Mock AI classifier for isolated testing."""
        mock = AsyncMock(spec=ReviewClassifierProtocol)
        mock.classify_review.return_value = ClassificationResult(
            sentiment="positive",
            topics=["service"],
            confidence_score=0.92,
            urgency="low"
        )
        return mock
    
    @pytest.fixture
    def processor(self, mock_classifier: AsyncMock) -> ReviewProcessor:
        """Create processor with mocked dependencies."""
        return ReviewProcessor(classifier=mock_classifier)
    
    async def test_process_single_review_success(self, processor: ReviewProcessor, mock_classifier: AsyncMock):
        """Test processing single review returns classification."""
        # Arrange
        review_text = "Great service and food quality!"
        
        # Act
        result = await processor.process_review(review_text)
        
        # Assert
        assert result.sentiment == "positive"
        assert "service" in result.topics
        mock_classifier.classify_review.assert_called_once_with(review_text)
    
    async def test_process_batch_reviews_handles_errors(self, processor: ReviewProcessor, mock_classifier: AsyncMock):
        """Test batch processing handles individual review errors gracefully."""
        # Arrange
        reviews = ["Good food", "Bad service", "Excellent experience"]
        mock_classifier.classify_review.side_effect = [
            ClassificationResult(sentiment="positive", topics=["food"], confidence_score=0.9, urgency="low"),
            Exception("API Error"),
            ClassificationResult(sentiment="positive", topics=["service"], confidence_score=0.95, urgency="low")
        ]
        
        # Act
        results = await processor.process_batch(reviews)
        
        # Assert
        assert len(results) == 2  # Only successful classifications
        assert all(r.sentiment == "positive" for r in results)
```

### Integration Tests (backend/tests/integration/)

#### Characteristics
- **Real APIs**: Test actual API endpoints
- **Database**: Use test database with real connections
- **Authentication**: Test with actual JWT tokens
- **External Services**: Mock external APIs only

#### Implementation Pattern
```python
class TestReviewEndpoints:
    """Integration tests for review API endpoints."""
    
    @pytest.fixture
    async def authenticated_client(self, test_client: AsyncClient, test_db: AsyncSession) -> AsyncClient:
        """Provide authenticated test client."""
        # Create test user
        user = await create_test_user(test_db, email="test@example.com", role="business_owner")
        
        # Get JWT token
        login_response = await test_client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Set authorization header
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        return test_client
    
    @pytest.fixture
    async def test_business(self, test_db: AsyncSession) -> Business:
        """Create test business for endpoint testing."""
        business = Business(
            name="Test Restaurant",
            google_place_id="test_place_123",
            owner_id=1
        )
        test_db.add(business)
        await test_db.commit()
        await test_db.refresh(business)
        return business
    
    async def test_import_reviews_endpoint_success(
        self, 
        authenticated_client: AsyncClient, 
        test_business: Business,
        mock_google_places: Mock
    ):
        """Test review import endpoint with valid business."""
        # Arrange
        mock_google_places.get_reviews.return_value = [
            {"text": "Great food!", "rating": 5, "time": "2023-01-01"},
            {"text": "Good service", "rating": 4, "time": "2023-01-02"}
        ]
        
        # Act
        response = await authenticated_client.post(f"/api/businesses/{test_business.id}/import-reviews")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["imported_count"] == 2
        assert "import_id" in data
    
    async def test_classify_reviews_endpoint_validation(self, authenticated_client: AsyncClient):
        """Test review classification endpoint input validation."""
        # Arrange
        invalid_payload = {
            "business_id": "",  # Invalid empty business_id
            "reviews": []       # Invalid empty reviews list
        }
        
        # Act
        response = await authenticated_client.post("/api/classify-reviews", json=invalid_payload)
        
        # Assert
        assert response.status_code == 422
        error_data = response.json()
        assert "business_id" in str(error_data["detail"])
```

### End-to-End Tests (backend/tests/e2e/)

#### Characteristics
- **Complete Workflows**: Test entire user journeys
- **Real Data Flow**: Data flows through all system layers
- **Multi-Service**: Tests service interactions
- **User Perspective**: Tests from user's point of view

#### Implementation Pattern
```python
class TestCompleteUserWorkflow:
    """End-to-end tests for complete user workflows."""
    
    @pytest.fixture
    async def business_owner_session(self, test_client: AsyncClient, test_db: AsyncSession) -> Dict[str, Any]:
        """Set up complete business owner session."""
        # Create user account
        user_data = {
            "email": "owner@restaurant.com",
            "password": "securepassword",
            "full_name": "Restaurant Owner",
            "role": "business_owner"
        }
        register_response = await test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201
        
        # Login and get token
        login_response = await test_client.post("/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        token_data = login_response.json()
        
        # Set authorization
        test_client.headers.update({"Authorization": f"Bearer {token_data['access_token']}"})
        
        return {
            "client": test_client,
            "user_id": token_data["user_id"],
            "token": token_data["access_token"]
        }
    
    async def test_complete_business_setup_and_analysis_workflow(
        self, 
        business_owner_session: Dict[str, Any],
        mock_google_places: Mock,
        mock_ai_services: Dict[str, Mock]
    ):
        """Test complete workflow from business registration to insights."""
        client = business_owner_session["client"]
        
        # Step 1: Register business
        business_data = {
            "name": "Amazing Restaurant",
            "google_place_id": "ChIJ123abc",
            "address": "123 Main St, City, State"
        }
        business_response = await client.post("/api/businesses", json=business_data)
        assert business_response.status_code == 201
        business_id = business_response.json()["id"]
        
        # Step 2: Import reviews from Google Places
        mock_google_places.get_reviews.return_value = [
            {"text": "Excellent food and service!", "rating": 5, "author": "John D.", "time": "2023-01-15"},
            {"text": "Food was cold, slow service", "rating": 2, "author": "Jane S.", "time": "2023-01-14"},
            {"text": "Great atmosphere, will come back", "rating": 4, "author": "Mike R.", "time": "2023-01-13"}
        ]
        
        import_response = await client.post(f"/api/businesses/{business_id}/import-reviews")
        assert import_response.status_code == 200
        assert import_response.json()["imported_count"] == 3
        
        # Step 3: Wait for classification to complete (simulate async processing)
        await asyncio.sleep(0.1)  # Allow async processing
        
        # Step 4: Get analytics dashboard
        analytics_response = await client.get(f"/api/analytics/{business_id}")
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        
        # Verify analytics data structure
        assert "sentiment_distribution" in analytics_data
        assert "topic_analysis" in analytics_data
        assert "recent_reviews_count" in analytics_data
        assert analytics_data["recent_reviews_count"] == 3
        
        # Step 5: Chat with AI advisor
        chat_payload = {
            "message": "What should I focus on to improve my restaurant?",
            "language": "en"
        }
        chat_response = await client.post(f"/api/chat/{business_id}", json=chat_payload)
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        # Verify AI response
        assert "response" in chat_data
        assert "conversation_id" in chat_data
        assert len(chat_data["response"]) > 0
        
        # Step 6: Generate weekly report
        report_response = await client.post(f"/api/reports/{business_id}/weekly")
        assert report_response.status_code == 200
        report_data = report_response.json()
        
        # Verify report structure
        assert "summary" in report_data
        assert "action_items" in report_data
        assert "sentiment_trend" in report_data
        assert isinstance(report_data["action_items"], list)
```

## Async Testing Patterns

### Async Test Configuration
```python
# conftest.py - Proper async setup
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_test_helper() -> AsyncTestHelper:
    """Provide async testing utilities."""
    return AsyncTestHelper()

class AsyncTestHelper:
    """Helper class for async test operations."""
    
    @staticmethod
    async def run_with_timeout(coro: Awaitable[T], timeout: float = 5.0) -> T:
        """Run coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout=timeout)
    
    @staticmethod
    async def assert_async_raises(exception_class: type, coro: Awaitable[Any]) -> None:
        """Assert async operation raises exception."""
        with pytest.raises(exception_class):
            await coro
```

### AsyncMock Usage
```python
class TestAsyncService:
    """Test async service methods properly."""
    
    @pytest.fixture
    def mock_async_client(self) -> AsyncMock:
        """Create properly configured AsyncMock."""
        mock = AsyncMock(spec=AsyncHTTPClient)
        mock.post.return_value = AsyncMock(
            status_code=200,
            json=AsyncMock(return_value={"success": True})
        )
        return mock
    
    async def test_async_operation_success(self, mock_async_client: AsyncMock):
        """Test async operation with proper mocking."""
        # Arrange
        service = SomeAsyncService(client=mock_async_client)
        
        # Act
        result = await service.perform_async_operation("test_data")
        
        # Assert
        assert result is not None
        mock_async_client.post.assert_called_once()
```

## Mock Configuration Standards

### Service Mocking Patterns
```python
class MockServiceFactory:
    """Factory for creating standardized service mocks."""
    
    @staticmethod
    def create_gpt5_classifier_mock() -> AsyncMock:
        """Create GPT-5 classifier mock with realistic responses."""
        mock = AsyncMock(spec=GPT5NanoClassifier)
        
        # Configure default behavior
        mock.classify_review.return_value = ClassificationResult(
            sentiment="positive",
            topics=["food_quality"],
            confidence_score=0.95,
            urgency="low",
            competitor_mentioned=False
        )
        
        # Configure batch processing
        mock.classify_batch.return_value = [
            ClassificationResult(
                sentiment="positive",
                topics=["service"],
                confidence_score=0.92,
                urgency="low",
                competitor_mentioned=False
            )
        ]
        
        return mock
    
    @staticmethod
    def create_database_session_mock() -> AsyncMock:
        """Create database session mock with transaction support."""
        mock = AsyncMock(spec=AsyncSession)
        
        # Configure transaction methods
        mock.commit = AsyncMock()
        mock.rollback = AsyncMock()
        mock.close = AsyncMock()
        
        # Configure query methods
        mock.execute = AsyncMock()
        mock.scalar = AsyncMock()
        mock.scalars = AsyncMock()
        
        return mock
```

### External API Mocking
```python
@pytest.fixture
def mock_external_apis() -> Dict[str, Mock]:
    """Mock all external API services."""
    with patch('backend.external.google_places.GooglePlacesClient') as mock_google, \
         patch('backend.ai.gpt5_classifier.OpenAIClient') as mock_openai, \
         patch('backend.ai.claude_advisor.AnthropicClient') as mock_anthropic:
        
        # Configure Google Places mock
        mock_google.return_value.search_places.return_value = [
            {"place_id": "test123", "name": "Test Restaurant", "rating": 4.5}
        ]
        mock_google.return_value.get_reviews.return_value = [
            {"text": "Great food!", "rating": 5, "time": "2023-01-01"}
        ]
        
        # Configure OpenAI mock
        mock_openai.return_value.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"sentiment": "positive", "topics": ["food"]}'))]
        )
        
        # Configure Anthropic mock
        mock_anthropic.return_value.messages.create.return_value = Mock(
            content=[Mock(text="Based on your reviews, focus on service quality.")]
        )
        
        yield {
            'google_places': mock_google,
            'openai': mock_openai,
            'anthropic': mock_anthropic
        }
```

## Performance Testing Guidelines

### Response Time Testing
```python
class TestPerformanceRequirements:
    """Test performance requirements are met."""
    
    @pytest.fixture
    def performance_tester(self) -> PerformanceTester:
        """Provide performance testing utilities."""
        return PerformanceTester(max_response_time=0.5)  # 500ms limit
    
    async def test_api_response_time_under_limit(
        self, 
        test_client: AsyncClient, 
        performance_tester: PerformanceTester
    ):
        """Test API response time meets requirements."""
        # Arrange
        start_time = time.time()
        
        # Act
        response = await test_client.get("/api/health")
        
        # Assert
        execution_time = time.time() - start_time
        assert execution_time < 0.5  # Must be under 500ms
        assert response.status_code == 200
    
    async def test_batch_processing_performance(
        self, 
        review_service: ReviewService, 
        performance_tester: PerformanceTester
    ):
        """Test batch processing meets performance requirements."""
        # Arrange
        reviews = [f"Test review {i}" for i in range(500)]
        
        # Act & Assert
        result = await performance_tester.measure_batch_operation(
            operation=review_service.process_batch,
            batch_size=500,
            max_batch_time=60.0,  # 60 seconds for 500 reviews
            operation_name="review_batch_processing"
        )
        
        assert result.success, f"Batch processing failed: {result.error_message}"
```

### Load Testing Patterns
```python
class TestLoadRequirements:
    """Test system under load conditions."""
    
    async def test_concurrent_api_requests(self, test_client: AsyncClient):
        """Test API handles concurrent requests properly."""
        # Arrange
        concurrent_requests = 50
        
        async def make_request():
            return await test_client.get("/api/health")
        
        # Act
        start_time = time.time()
        tasks = [make_request() for _ in range(concurrent_requests)]
        responses = await asyncio.gather(*tasks)
        execution_time = time.time() - start_time
        
        # Assert
        assert all(r.status_code == 200 for r in responses)
        assert execution_time < 5.0  # All requests complete within 5 seconds
        
        # Verify no rate limiting errors
        assert not any(r.status_code == 429 for r in responses)
```

## Test Data Management

### Factory Pattern for Test Data
```python
class ReviewDataFactory:
    """Factory for creating test review data."""
    
    @staticmethod
    def create_positive_review(
        business_id: int = 1,
        rating: int = 5,
        text: str = "Excellent food and service!"
    ) -> Review:
        """Create positive review for testing."""
        return Review(
            business_id=business_id,
            google_review_id=f"test_review_{uuid.uuid4()}",
            author_name="Test Customer",
            rating=rating,
            text=text,
            created_at=datetime.utcnow(),
            language="en"
        )
    
    @staticmethod
    def create_negative_review(
        business_id: int = 1,
        rating: int = 2,
        text: str = "Poor service and cold food."
    ) -> Review:
        """Create negative review for testing."""
        return Review(
            business_id=business_id,
            google_review_id=f"test_review_{uuid.uuid4()}",
            author_name="Disappointed Customer",
            rating=rating,
            text=text,
            created_at=datetime.utcnow(),
            language="en"
        )
    
    @staticmethod
    def create_review_batch(count: int = 10, business_id: int = 1) -> List[Review]:
        """Create batch of mixed reviews for testing."""
        reviews = []
        for i in range(count):
            if i % 3 == 0:
                reviews.append(ReviewDataFactory.create_negative_review(business_id))
            else:
                reviews.append(ReviewDataFactory.create_positive_review(business_id))
        return reviews
```

### Database Fixture Management
```python
@pytest.fixture
async def test_business_with_reviews(test_db: AsyncSession) -> Business:
    """Create business with sample reviews for testing."""
    # Create business
    business = Business(
        name="Test Restaurant",
        google_place_id="test_place_123",
        owner_id=1
    )
    test_db.add(business)
    await test_db.commit()
    await test_db.refresh(business)
    
    # Add sample reviews
    reviews = ReviewDataFactory.create_review_batch(count=20, business_id=business.id)
    for review in reviews:
        test_db.add(review)
    
    await test_db.commit()
    return business
```

## Error Handling and Edge Cases

### Exception Testing Patterns
```python
class TestErrorHandling:
    """Test error handling and edge cases."""
    
    async def test_service_handles_api_timeout(self, mock_ai_client: AsyncMock):
        """Test service handles API timeout gracefully."""
        # Arrange
        mock_ai_client.classify_review.side_effect = asyncio.TimeoutError("API timeout")
        service = ReviewClassificationService(classifier=mock_ai_client)
        
        # Act & Assert
        with pytest.raises(AIServiceException) as exc_info:
            await service.classify_review("Test review")
        
        assert "timeout" in str(exc_info.value).lower()
    
    async def test_service_handles_invalid_input(self, review_service: ReviewService):
        """Test service validates input properly."""
        # Test empty input
        with pytest.raises(ValidationError):
            await review_service.process_review("")
        
        # Test None input
        with pytest.raises(ValidationError):
            await review_service.process_review(None)
        
        # Test oversized input
        large_text = "x" * 10000  # Assuming 10k char limit
        with pytest.raises(ValidationError):
            await review_service.process_review(large_text)
```

### Edge Case Testing
```python
class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    async def test_empty_review_list_processing(self, review_service: ReviewService):
        """Test processing empty review list."""
        # Act
        result = await review_service.process_batch([])
        
        # Assert
        assert result == []
    
    async def test_single_character_review(self, review_service: ReviewService):
        """Test processing minimal review content."""
        # Act
        result = await review_service.process_review("!")
        
        # Assert
        assert result is not None
        assert result.confidence_score < 0.5  # Low confidence expected
    
    async def test_unicode_review_processing(self, review_service: ReviewService):
        """Test processing reviews with unicode characters."""
        # Arrange
        unicode_review = "Excellent food! 🍕👍 Très bon restaurant! 素晴らしい!"
        
        # Act
        result = await review_service.process_review(unicode_review)
        
        # Assert
        assert result is not None
        assert result.sentiment in ["positive", "negative", "neutral"]
```

## Code Quality Standards

### Test Method Structure
```python
def test_method_name_describes_behavior_and_expected_outcome(self, fixtures):
    """Test docstring explains what is being tested and why.
    
    Should be clear enough that someone can understand the test
    purpose without reading the implementation.
    """
    # Arrange - Set up test data and conditions
    input_data = "test input"
    expected_result = "expected output"
    
    # Act - Execute the behavior being tested
    actual_result = system_under_test.method(input_data)
    
    # Assert - Verify the outcome matches expectations
    assert actual_result == expected_result
    assert system_under_test.state_changed_correctly()
```

### Assertion Best Practices
```python
class TestAssertionPatterns:
    """Examples of good assertion patterns."""
    
    def test_with_specific_assertions(self, service: SomeService):
        """Use specific assertions rather than generic ones."""
        result = service.calculate_metrics()
        
        # Good - Specific assertions
        assert result.total_reviews == 10
        assert result.average_rating == 4.2
        assert result.sentiment_distribution["positive"] == 0.7
        
        # Avoid - Generic assertions
        # assert result is not None  # Too generic
        # assert len(result) > 0     # Not specific enough
    
    def test_with_custom_assertions(self, classification_result: ClassificationResult):
        """Use custom assertion helpers for complex validations."""
        # Use custom assertion helper
        TestAssertions.assert_classification_result(
            result=classification_result,
            expected_sentiment="positive",
            expected_topics=["food_quality", "service"],
            min_confidence=0.8
        )
        
        # Instead of multiple individual assertions
        # assert classification_result.sentiment == "positive"
        # assert "food_quality" in classification_result.topics
        # assert classification_result.confidence_score >= 0.8
```

### Test Documentation Standards
```python
class TestDocumentationExample:
    """Example of well-documented test class.
    
    This class demonstrates proper test documentation including:
    - Clear class docstring explaining test scope
    - Method docstrings explaining test purpose
    - Inline comments for complex setup or assertions
    """
    
    def test_complex_business_logic_with_multiple_conditions(self, service: BusinessService):
        """Test business logic handles multiple conditions correctly.
        
        This test verifies that the service properly calculates metrics
        when dealing with mixed review sentiments and different time periods.
        It's important because the calculation affects dashboard displays.
        """
        # Arrange - Create test data representing real-world scenario
        reviews = [
            # Recent positive reviews (should have higher weight)
            create_review(sentiment="positive", days_ago=1),
            create_review(sentiment="positive", days_ago=2),
            
            # Older negative review (should have lower weight)
            create_review(sentiment="negative", days_ago=30)
        ]
        
        # Act - Calculate weighted sentiment score
        result = service.calculate_weighted_sentiment(reviews)
        
        # Assert - Verify recent reviews have more influence
        assert result > 0.5, "Recent positive reviews should outweigh older negative ones"
        assert 0.6 <= result <= 0.8, f"Expected score between 0.6-0.8, got {result}"
```

This comprehensive guide ensures all tests follow project standards while maintaining high quality and maintainability. Remember to keep test files under 500 lines and split them when they grow too large.