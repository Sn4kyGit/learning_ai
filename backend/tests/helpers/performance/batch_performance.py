"""
Batch operation performance testing utilities.

This module contains specialized performance testing classes
for batch operations like processing 500 reviews in 60 seconds.
"""

from .base_performance import PerformanceTester


class BatchOperationTester(PerformanceTester):
    """Specialized tester for batch operations like processing 500 reviews in 60 seconds."""
    
    def __init__(self, max_response_time: float = 60.0):
        super().__init__(max_response_time)  # Batch operations can take longer