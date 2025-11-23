"""Configuration settings for the finance monitor"""

import os
import secrets
from typing import ClassVar


class SecurityConfig:
    """Security configuration settings"""

    # JWT Configuration
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        # Generate a secure random key if not set
        # WARNING: This will change on each restart if not set in environment
        SECRET_KEY = secrets.token_urlsafe(32)

    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Rate Limiting Configuration
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_ATTEMPT_WINDOW = 300  # 5 minutes in seconds

    MAX_REGISTRATION_ATTEMPTS = 3
    REGISTRATION_ATTEMPT_WINDOW = 3600  # 1 hour in seconds

    MAX_PASSWORD_RESET_ATTEMPTS = 3
    PASSWORD_RESET_ATTEMPT_WINDOW = 3600  # 1 hour in seconds

    # Password Requirements
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    BCRYPT_MAX_BYTES = 72  # bcrypt limitation

    # JWT Token Settings
    JWT_AUDIENCE = "finance-monitor"
    JWT_ISSUER = "finance-monitor-api"
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24


class CacheConfig:
    """Cache configuration settings"""

    # Compression threshold (bytes) - compress data larger than this
    COMPRESSION_THRESHOLD = 2048

    # TTL (Time To Live) settings in seconds
    DEFAULT_TTL = 60  # Base TTL for all cached items
    MARKET_HOURS_TTL = 30  # During market hours
    OFF_HOURS_TTL = 300  # Outside market hours
    REDIS_TTL_MULTIPLIER = 2  # Redis stores data longer than memory cache

    # LRU Cache settings
    LRU_MAX_SIZE = 500  # Reduced from 2000 for better memory efficiency
    LRU_EXPECTED_SYMBOLS = 100  # Expected number of unique symbols


class Config:
    # Application settings
    APP_NAME = "FastAPI Finance Monitor"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Update settings
    UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "30"))  # seconds
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

    # API settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    # Default assets to monitor
    DEFAULT_ASSETS: ClassVar[list[dict]] = [
        {"type": "stock", "symbol": "AAPL", "name": "Apple"},
        {"type": "stock", "symbol": "GOOGL", "name": "Google"},
        {"type": "stock", "symbol": "MSFT", "name": "Microsoft"},
        {"type": "stock", "symbol": "TSLA", "name": "Tesla"},
        {"type": "stock", "symbol": "GC=F", "name": "Gold"},
        {"type": "crypto", "symbol": "bitcoin", "name": "Bitcoin"},
        {"type": "crypto", "symbol": "ethereum", "name": "Ethereum"},
        {"type": "crypto", "symbol": "solana", "name": "Solana"},
    ]

    # Watchlist settings
    DEFAULT_WATCHLIST: ClassVar[list[str]] = [
        "AAPL",
        "GOOGL",
        "MSFT",
        "TSLA",
        "GC=F",
        "bitcoin",
        "ethereum",
        "solana",
    ]


config = Config()
