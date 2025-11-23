"""Type definitions for financial data structures

This module provides TypedDict definitions for structured financial data
to improve type safety and IDE autocomplete throughout the application.

Usage:
    from app.utils.types import AssetData, ChartPointOHLC
    
    def process_asset(data: AssetData) -> None:
        price = data["current_price"]  # Type-safe access
"""

from typing import TypedDict, List, Optional, Literal


class ChartPointPrice(TypedDict, total=False):
    """Chart data point with price and timestamp (for crypto/forex)"""
    time: str
    price: float


class ChartPointOHLC(TypedDict, total=False):
    """Chart data point with OHLC data (for stocks)"""
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int]


class AssetData(TypedDict, total=False):
    """Complete asset data structure"""
    symbol: str
    name: str
    type: Literal["stock", "crypto", "forex", "commodity", "asset", "error"]
    timestamp: str
    current_price: float
    change: Optional[float]
    change_percent: float
    open: float
    high: float
    low: float
    volume: int
    market_cap: Optional[int]
    chart_data: List[ChartPointOHLC | ChartPointPrice]
    error: Optional[str]


class AlertCondition(TypedDict, total=False):
    """Alert condition structure"""
    type: str
    threshold: float
    extra_params: Optional[dict]


class UserInfo(TypedDict):
    """User information from JWT token"""
    user_id: int
    username: str


class CacheStats(TypedDict, total=False):
    """Cache statistics structure"""
    memory_total_items: int
    memory_expired_items: int
    memory_active_items: int
    memory_usage_bytes: int
    hits: int
    misses: int
    errors: int
    hit_ratio: float
    redis_stats: dict
    partition_stats: dict
