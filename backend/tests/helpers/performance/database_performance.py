"""
Database performance testing utilities.

This module contains specialized performance testing classes
for database query optimization.
"""

from .base_performance import PerformanceTester


class DatabasePerformanceTester(PerformanceTester):
    """Specialized performance tester for database query optimization."""
    
    def __init__(self, max_response_time: float = 0.1):
        super().__init__(max_response_time)  # Database queries should be fast