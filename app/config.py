"""Configuration settings for the finance monitor"""

import os
from typing import List


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
    DEFAULT_ASSETS: List[dict] = [
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
    DEFAULT_WATCHLIST: List[str] = [
        "AAPL", "GOOGL", "MSFT", "TSLA", "GC=F",
        "bitcoin", "ethereum", "solana"
    ]


config = Config()