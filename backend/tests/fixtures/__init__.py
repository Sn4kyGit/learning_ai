"""
Test fixtures package for Local Business Intelligence Bot.

This package provides comprehensive test data factories, fixtures, and
utilities for creating consistent test data across unit, integration,
and end-to-end tests.

Available modules:
- data_factories: Core data factory classes for creating test objects
- user_fixtures: User and authentication-related fixtures
- business_fixtures: Business and review-related fixtures  
- mock_responses: Mock API responses for external services
- database_seeding: Database seeding utilities for integration tests
"""

from .data_factories import TestDataFactory, MockDataFactory
from .database_seeding import DatabaseSeeder, SeedingPresets

__all__ = [
    "TestDataFactory",
    "MockDataFactory", 
    "DatabaseSeeder",
    "SeedingPresets"
]