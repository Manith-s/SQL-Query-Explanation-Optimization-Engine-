"""
Application configuration management.

Loads settings from environment variables with sensible defaults.
No secrets or file reading - just environment variable handling.
"""

import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""
    
    # Application environment
    APP_ENV: str = os.getenv("APP_ENV", "development")
    
    # Database configuration
    DB_URL: str = os.getenv("DB_URL", "postgresql://user:pass@localhost:5432/queryexpnopt")
    
    # LLM configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "dummy")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    # API configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Development settings
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    def __init__(self):
        """Initialize settings with environment variable overrides."""
        # Settings are loaded at class definition time
        # This allows for easy testing and configuration
        pass


# Global settings instance
settings = Settings()
