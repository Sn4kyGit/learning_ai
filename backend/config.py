"""
Configuration management for Local Business Intelligence Bot.

This module handles environment variables and application settings
using Pydantic for validation and type safety.
"""

# Removed unused import
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application settings
    environment: str = "development"
    debug: bool = False
    secret_key: str = "your-secret-key-change-in-production"

    # Database settings
    database_url: str = "sqlite+aiosqlite:///./businessbot.db"
    database_test_url: str = "sqlite+aiosqlite:///./businessbot_test.db"

    # Redis settings
    redis_url: str = "redis://localhost:6379/0"

    # AI Service settings
    openai_api_key: str = ""
    openai_model_name: str = "gpt-4o-mini"  # Using available model instead of gpt-5-nano
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.1
    
    anthropic_api_key: str = ""
    anthropic_model_name: str = "claude-3-haiku-20240307"
    anthropic_max_tokens: int = 1000
    anthropic_temperature: float = 0.1
    
    # AI service timeouts and retries
    ai_request_timeout: int = 30  # seconds
    ai_max_retries: int = 3
    ai_retry_delay: float = 1.0  # seconds

    # Google Places API
    google_places_api_key: str = ""

    # Email settings
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # SMS settings (optional)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # CORS settings
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Cost tracking
    default_monthly_cost_limit: float = 100.0
    cost_warning_threshold: float = 0.8  # 80%

    # Logging
    log_level: str = "INFO"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
