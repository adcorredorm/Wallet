"""
Application configuration module.

Provides configuration classes for different environments (development, testing, production).
"""

import os
from typing import Any


class Config:
    """Base configuration with common settings."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://wallet_user:wallet_password@localhost:5432/wallet_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    # pool_pre_ping validates connections before use — required for Neon serverless
    # which closes idle connections when the compute node scales to zero.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Internal cron auth
    CRON_SECRET_TOKEN = os.getenv("CRON_SECRET_TOKEN", "")

    # CORS
    # Docker compose sets FLASK_CORS_ORIGINS; local dev falls back to localhost defaults.
    CORS_ORIGINS = os.getenv("FLASK_CORS_ORIGINS", os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")).split(",")

    # Pagination
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))

    # JSON
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True

    # Authentication
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret-change-in-production")
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    REFRESH_TOKEN_EXPIRY_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRY_DAYS", "90"))
    REFRESH_TOKEN_GRACE_SECONDS = int(os.getenv("REFRESH_TOKEN_GRACE_SECONDS", "120"))


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://wallet_user:wallet_password@db:5432/wallet_test_db"
    )
    # Fixed secrets for tests — independent of .env so tests always pass
    # regardless of the production JWT_SECRET value.
    JWT_SECRET = "test-jwt-secret-for-testing-only"
    GOOGLE_CLIENT_ID = "test-google-client-id"


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False

    @classmethod
    def validate(cls) -> None:
        """Validate that all required production environment variables are set.

        Raises:
            ValueError: If a required environment variable is missing.
        """
        if not os.getenv("SECRET_KEY"):
            raise ValueError("SECRET_KEY must be set in production environment")
        if not os.getenv("JWT_SECRET"):
            raise ValueError("JWT_SECRET must be set in production environment")
        if not os.getenv("GOOGLE_CLIENT_ID"):
            raise ValueError("GOOGLE_CLIENT_ID must be set in production environment")


def get_config(config_name: str = "development") -> type[Config]:
    """
    Get configuration class based on environment name.

    Args:
        config_name: Environment name (development, testing, production)

    Returns:
        Configuration class for the specified environment

    Raises:
        ValueError: If config_name is not recognized
    """
    configs = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }

    config = configs.get(config_name)
    if not config:
        raise ValueError(
            f"Invalid config name: {config_name}. "
            f"Valid options: {', '.join(configs.keys())}"
        )

    return config
