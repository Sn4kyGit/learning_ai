"""
Test data factories for creating consistent test data.

This module provides comprehensive factories for creating test data objects
with realistic values and proper relationships. Supports both individual
object creation and batch operations for performance testing.

This is the main entry point that imports from specialized factory modules
to maintain backward compatibility while organizing code into focused modules.
"""

# Import all factories for backward compatibility
from .core_data_factory import CoreDataFactory
from .analytics_data_factory import AnalyticsDataFactory
from .batch_data_factory import BatchDataFactory
from .gdpr_data_factory import GDPRDataFactory
from .mock_responses import MockDataFactory

# Re-export the main factory class for backward compatibility
TestDataFactory = CoreDataFactory

# Re-export all factory classes for direct access
__all__ = [
    'TestDataFactory',
    'CoreDataFactory', 
    'AnalyticsDataFactory',
    'BatchDataFactory',
    'GDPRDataFactory',
    'MockDataFactory'
]