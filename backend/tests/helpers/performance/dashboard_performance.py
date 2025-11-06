"""
Dashboard performance testing utilities.

This module contains specialized performance testing classes
for dashboard load times and caching validation.
"""

from .base_performance import PerformanceTester


class DashboardPerformanceTester(PerformanceTester):
    """Specialized performance tester for dashboard load times and caching validation."""
    
    def __init__(self, max_response_time: float = 0.5):
        super().__init__(max_response_time)
        self.cache_hit_threshold = 0.1  # Cached responses should be under 100ms