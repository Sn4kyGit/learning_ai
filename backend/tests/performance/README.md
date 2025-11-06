# Performance Testing Framework

This directory contains the comprehensive performance testing framework for the Local Business Intelligence Bot. The framework provides specialized tools for testing different aspects of application performance.

## Framework Components

### 1. PerformanceTester (Base Class)
The base performance testing class that provides core functionality for measuring execution times and validating performance thresholds.

**Key Features:**
- Async and sync operation measurement
- Configurable performance thresholds
- Detailed performance metrics collection
- Concurrent operation testing
- Performance summary reporting

### 2. APIPerformanceTester
Specialized tester for API endpoint performance validation.

**Features:**
- Configurable thresholds for simple operations (default: 500ms) and AI operations (default: 3s)
- HTTP method support (GET, POST, PUT, DELETE)
- Response size and status code tracking
- Concurrent API load testing

**Usage Example:**
```python
api_tester = APIPerformanceTester(max_api_response_time=0.5, max_ai_response_time=3.0)

# Test simple endpoint
result = await api_tester.measure_api_endpoint(
    client=test_client,
    method="GET",
    url="/api/health",
    endpoint_name="health_check",
    is_ai_operation=False
)

# Test AI endpoint
ai_result = await api_tester.measure_api_endpoint(
    client=test_client,
    method="POST",
    url="/api/chat/business_id",
    endpoint_name="ai_chat",
    is_ai_operation=True,
    json={"message": "How is my business performing?"},
    headers=auth_headers
)
```

### 3. DashboardPerformanceTester
Specialized tester for dashboard load times and caching validation.

**Features:**
- Cache hit/miss performance comparison
- Cache effectiveness measurement (minimum 30% improvement expected)
- Dashboard load time validation
- Cache performance summary reporting

**Usage Example:**
```python
dashboard_tester = DashboardPerformanceTester(max_dashboard_load_time=0.5)

# Test dashboard with caching
cache_results = await dashboard_tester.measure_dashboard_load_with_caching(
    client=test_client,
    dashboard_url="/api/analytics/business_id/dashboard",
    dashboard_name="business_dashboard",
    headers=auth_headers
)

# Get cache performance summary
cache_summary = dashboard_tester.get_cache_performance_summary()
```

### 4. DatabasePerformanceTester
Specialized tester for database query optimization and performance analysis.

**Features:**
- Query execution time measurement
- SQL execution plan analysis
- Optimization recommendations
- Performance threshold validation (default: 100ms)

**Usage Example:**
```python
db_tester = DatabasePerformanceTester(max_query_time=0.1)

# Test database query
result = await db_tester.measure_database_query(
    db_session=test_db_session,
    query="SELECT * FROM businesses WHERE organization_id = :org_id",
    query_name="business_lookup",
    params={"org_id": org_id},
    analyze_plan=True
)

# Get optimization recommendations
recommendations = db_tester.get_optimization_recommendations()
```

### 5. BatchOperationTester
Specialized tester for batch operations, specifically designed to validate the requirement of processing 500 reviews in 60 seconds.

**Features:**
- Batch processing performance validation
- Throughput calculation (reviews per second)
- Configurable batch sizes and time limits
- Mock data generation for testing

**Usage Example:**
```python
batch_tester = BatchOperationTester(max_batch_time=60.0)

# Test 500 reviews in 60 seconds requirement
batch_result = await batch_tester.test_review_batch_processing(
    client=test_client,
    business_id=business_id,
    batch_size=500,
    max_time=60.0,
    headers=auth_headers
)

# Get batch performance summary
summary = batch_tester.get_batch_performance_summary()
```

## Performance Requirements

The framework validates the following performance requirements:

### API Response Times
- **Simple queries**: < 500ms
- **AI operations**: < 3 seconds
- **Dashboard loads**: < 500ms (with caching improvement of at least 30%)

### Batch Operations
- **500 reviews**: Must be processed within 60 seconds
- **Throughput**: Minimum 8.33 reviews per second

### Database Queries
- **Simple queries**: < 100ms
- **Complex aggregations**: < 1 second
- **Optimization**: Automatic recommendations for slow queries

### Caching
- **Cache hits**: Should be at least 30% faster than cache misses
- **Dashboard caching**: Must show measurable performance improvement

## Test Structure

### Performance Test Categories

1. **Unit Performance Tests** (`test_performance_framework.py`)
   - Individual component performance validation
   - Threshold testing
   - Metrics collection validation

2. **Integration Performance Tests** (`test_performance_integration.py`)
   - End-to-end performance validation
   - Multi-component performance testing
   - Real-world scenario simulation

3. **Load Testing** (`load_testing.py`)
   - High concurrency testing
   - Stress testing
   - Scalability validation

### Running Performance Tests

```bash
# Run all performance tests
pytest backend/tests/performance/ -v

# Run specific performance test category
pytest backend/tests/performance/test_performance_framework.py -v

# Run with performance markers
pytest -m performance -v

# Run batch operation tests specifically
pytest backend/tests/performance/test_performance_framework.py::TestBatchOperationFramework -v
```

## Performance Metrics

### Collected Metrics

Each performance test collects the following metrics:

- **Execution Time**: Actual time taken for the operation
- **Success Status**: Whether the operation met performance thresholds
- **Additional Metrics**: Operation-specific data (throughput, cache hit rates, etc.)
- **Error Information**: Detailed error messages for failed operations

### Performance Results Structure

```python
@dataclass
class PerformanceResult:
    operation_name: str
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    additional_metrics: Optional[Dict[str, Any]] = None
```

### Performance Summary

Each tester provides a comprehensive summary:

```python
{
    "total_tests": int,
    "successful_tests": int,
    "success_rate": float,
    "average_execution_time": float,
    "fastest_operation": PerformanceResult,
    "slowest_operation": PerformanceResult,
    "failed_operations": List[PerformanceResult]
}
```

## Optimization Recommendations

### Database Query Optimization

The `DatabasePerformanceTester` automatically analyzes SQL execution plans and provides recommendations:

- **Sequential Scan Detection**: Suggests adding indexes
- **Slow Nested Loops**: Recommends join optimization
- **Disk-based Sorting**: Suggests memory configuration improvements
- **General Slow Queries**: Provides optimization guidance

### API Performance Optimization

- **Response Time Monitoring**: Identifies slow endpoints
- **Concurrent Load Testing**: Validates scalability
- **Resource Usage Tracking**: Monitors memory and CPU usage

### Caching Optimization

- **Cache Hit Rate Analysis**: Measures caching effectiveness
- **Cache Performance Validation**: Ensures proper cache implementation
- **Cache Invalidation Testing**: Validates cache consistency

## Best Practices

### Writing Performance Tests

1. **Use Appropriate Testers**: Choose the right specialized tester for your use case
2. **Set Realistic Thresholds**: Configure thresholds based on actual requirements
3. **Test Real Scenarios**: Use realistic data volumes and user patterns
4. **Monitor Trends**: Track performance over time, not just absolute values
5. **Include Error Handling**: Test performance under error conditions

### Performance Test Maintenance

1. **Regular Updates**: Update performance thresholds as the system evolves
2. **Environment Consistency**: Ensure test environments match production characteristics
3. **Data Management**: Use consistent test data for reproducible results
4. **Continuous Monitoring**: Integrate performance tests into CI/CD pipelines

### Interpreting Results

1. **Trend Analysis**: Look for performance degradation over time
2. **Threshold Violations**: Investigate any performance threshold failures
3. **Resource Utilization**: Monitor memory, CPU, and database performance
4. **Optimization Opportunities**: Act on automated recommendations

## Integration with CI/CD

The performance testing framework is designed to integrate with continuous integration:

```yaml
# Example GitHub Actions integration
- name: Run Performance Tests
  run: |
    pytest backend/tests/performance/ --json-report --json-report-file=performance-report.json
    
- name: Check Performance Thresholds
  run: |
    python scripts/check_performance_thresholds.py performance-report.json
```

## Troubleshooting

### Common Issues

1. **Test Timeouts**: Increase timeout values for slow operations
2. **Database Connection Issues**: Ensure proper test database setup
3. **Mock Configuration**: Verify external service mocks are properly configured
4. **Environment Differences**: Account for performance variations between environments

### Performance Debugging

1. **Enable Detailed Logging**: Use verbose output for debugging
2. **Profile Slow Operations**: Use profiling tools for detailed analysis
3. **Check Resource Usage**: Monitor system resources during tests
4. **Analyze Execution Plans**: Review database query execution plans

This performance testing framework provides comprehensive coverage of all performance requirements and enables continuous performance validation throughout the development lifecycle.