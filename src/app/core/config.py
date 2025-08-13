"""
Application configuration management.
Loads settings from environment variables (via .env if present).
"""

import os
from typing import List
from dotenv import load_dotenv

# Load .env once at import time (real OS env still wins if set)
load_dotenv(override=False)


class Settings:
    # Application environment
    APP_ENV: str = os.getenv("APP_ENV", "development")

    # Database configuration (match your .env scheme)
    # Keep the +psycopg2 so SQLAlchemy knows the driver;
    # when using raw psycopg2, we'll strip the +psycopg2.
    DB_URL: str = os.getenv(
        "DB_URL",
        "postgresql+psycopg2://postgres:password@localhost:5432/queryexpnopt",
    )

    # LLM configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "dummy")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama2")
    LLM_TIMEOUT_S: int = int(os.getenv("LLM_TIMEOUT_S", "30"))
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # API configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Development settings
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Optimizer configuration
    OPT_MIN_ROWS_FOR_INDEX: int = int(os.getenv("OPT_MIN_ROWS_FOR_INDEX", "10000"))
    OPT_MAX_INDEX_COLS: int = int(os.getenv("OPT_MAX_INDEX_COLS", "3"))
    OPT_ALLOW_COVERING: bool = os.getenv("OPT_ALLOW_COVERING", "false").lower() == "true"
    OPT_ALLOW_PARTIAL: bool = os.getenv("OPT_ALLOW_PARTIAL", "false").lower() == "true"
    OPT_TOP_K: int = int(os.getenv("OPT_TOP_K", "10"))
    OPT_ANALYZE_DEFAULT: bool = os.getenv("OPT_ANALYZE_DEFAULT", "false").lower() == "true"
    OPT_TIMEOUT_MS_DEFAULT: int = int(os.getenv("OPT_TIMEOUT_MS_DEFAULT", "10000"))

    # Metrics configuration
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "false").lower() == "true"
    METRICS_NAMESPACE: str = os.getenv("METRICS_NAMESPACE", "qeo")
    METRICS_BUCKETS: str = os.getenv("METRICS_BUCKETS", "0.005,0.01,0.025,0.05,0.1,0.25,0.5,1,2,5")

    # SQL Linting configuration
    LARGE_TABLE_PATTERNS: List[str] = [
        s.strip() for s in os.getenv(
            "LARGE_TABLE_PATTERNS",
            "events,logs,transactions,fact_*,audit_*,metrics,analytics",
        ).split(",") if s.strip()
    ]

    NUMERIC_COLUMN_PATTERNS: List[str] = [
        s.strip() for s in os.getenv(
            "NUMERIC_COLUMN_PATTERNS",
            "_id,count,amount,price,quantity,score,rating",
        ).split(",") if s.strip()
    ]

    # ---- Convenience helpers ----
    @property
    def db_url_sqlalchemy(self) -> str:
        """Use this if you connect via SQLAlchemy/async engines."""
        return self.DB_URL

    @property
    def db_url_psycopg(self) -> str:
        """Use this if you call psycopg2.connect() directly."""
        return self.DB_URL.replace("postgresql+psycopg2://", "postgresql://")


settings = Settings()
