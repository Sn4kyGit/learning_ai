"""
Async test helper utilities for handling async operations in tests.
"""

import asyncio
import time
from typing import Any, Awaitable, TypeVar, Callable
from unittest.mock import AsyncMock

T = TypeVar('T')


class AsyncTestHelper:
    """Helper class for async test operations."""
    
    @staticmethod
    async def run_with_timeout(coro: Awaitable[T], timeout: float = 5.0) -> T:
        """Run coroutine with timeout for performance testing."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise AssertionError(f"Operation timed out after {timeout} seconds")
    
    @staticmethod
    def create_async_mock_with_return(return_value: Any) -> AsyncMock:
        """Create AsyncMock with specific return value."""
        mock = AsyncMock()
        mock.return_value = return_value
        return mock
    
    @staticmethod
    def create_async_mock_with_side_effect(side_effect: Callable) -> AsyncMock:
        """Create AsyncMock with side effect function."""
        mock = AsyncMock()
        mock.side_effect = side_effect
        return mock
    
    @staticmethod
    async def measure_execution_time(coro: Awaitable[T]) -> tuple[T, float]:
        """Measure execution time of async operation."""
        start_time = time.time()
        result = await coro
        execution_time = time.time() - start_time
        return result, execution_time
    
    @staticmethod
    def assert_async_mock_called_with(mock: AsyncMock, *args, **kwargs):
        """Assert that async mock was called with specific arguments."""
        mock.assert_called_with(*args, **kwargs)
    
    @staticmethod
    def assert_async_mock_call_count(mock: AsyncMock, expected_count: int):
        """Assert that async mock was called expected number of times."""
        assert mock.call_count == expected_count, f"Expected {expected_count} calls, got {mock.call_count}"