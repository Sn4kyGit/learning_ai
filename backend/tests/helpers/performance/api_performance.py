"""
API performance testing utilities.

This module contains specialized performance testing classes
for API endpoint testing.
"""

from .base_performance import PerformanceTester, PerformanceResult


class APIPerformanceTester(PerformanceTester):
    """Specialized performance tester for API endpoints."""
    
    def __init__(self, max_response_time: float = 0.5):
        super().__init__(max_response_time)
        self.api_thresholds = {
            "simple_query": 0.5,
            "ai_operation": 3.0,
            "batch_operation": 60.0
        }
    
    async def test_endpoint_performance(
        self,
        client,
        endpoint: str,
        method: str = "GET",
        data: dict = None,
        headers: dict = None,
        expected_threshold: str = "simple_query"
    ) -> PerformanceResult:
        """Test API endpoint performance with appropriate thresholds."""
        threshold = self.api_thresholds.get(expected_threshold, self.max_response_time)
        
        async def make_request():
            if method.upper() == "GET":
                return await client.get(endpoint, headers=headers)
            elif method.upper() == "POST":
                return await client.post(endpoint, json=data, headers=headers)
            elif method.upper() == "PUT":
                return await client.put(endpoint, json=data, headers=headers)
            elif method.upper() == "DELETE":
                return await client.delete(endpoint, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Temporarily adjust threshold for this test
        original_threshold = self.max_response_time
        self.max_response_time = threshold
        
        try:
            result = await self.measure_async_operation(
                make_request,
                f"{method.upper()} {endpoint}"
            )
            return result
        finally:
            self.max_response_time = original_threshold