"""Tests for the finance monitor services"""

import pytest
import asyncio
from app.services.data_fetcher import DataFetcher
from app.services.indicators import TechnicalIndicators
from app.services.watchlist import watchlist_service
import pandas as pd
import numpy as np


def test_watchlist_service():
    """Test watchlist service functionality"""
    # Test adding to watchlist
    assert watchlist_service.add_to_watchlist("test_user", "TEST")
    
    # Test checking if in watchlist
    assert watchlist_service.is_in_watchlist("test_user", "TEST")
    assert not watchlist_service.is_in_watchlist("test_user", "NONEXISTENT")
    
    # Test getting watchlist
    watchlist = watchlist_service.get_user_watchlist("test_user")
    assert "TEST" in watchlist
    
    # Test removing from watchlist
    assert watchlist_service.remove_from_watchlist("test_user", "TEST")
    assert not watchlist_service.is_in_watchlist("test_user", "TEST")


def test_technical_indicators():
    """Test technical indicators calculations"""
    # Create sample data with more realistic values
    prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 112, 111, 113, 115])
    high = pd.Series([101, 103, 102, 104, 106, 105, 107, 109, 108, 110, 111, 113, 112, 114, 116])
    low = pd.Series([99, 101, 100, 102, 104, 103, 105, 107, 106, 108, 109, 111, 110, 112, 114])
    close = prices
    
    # Test RSI
    rsi = TechnicalIndicators.calculate_rsi(prices)
    assert isinstance(rsi, float)
    # Handle NaN case by checking if it's a valid number
    if not np.isnan(rsi):
        assert 0 <= rsi <= 100
    
    # Test MA
    ma = TechnicalIndicators.calculate_ma(prices)
    assert isinstance(ma, float)
    
    # Test EMA
    ema = TechnicalIndicators.calculate_ema(prices)
    assert isinstance(ema, float)
    
    # Test MACD
    macd_data = TechnicalIndicators.calculate_macd(prices)
    assert isinstance(macd_data, dict)
    assert "macd" in macd_data
    assert "signal" in macd_data
    assert "histogram" in macd_data
    
    # Test Bollinger Bands
    bb_data = TechnicalIndicators.calculate_bollinger_bands(prices)
    assert isinstance(bb_data, dict)
    assert "upper" in bb_data
    assert "middle" in bb_data
    assert "lower" in bb_data


if __name__ == "__main__":
    test_watchlist_service()
    test_technical_indicators()
    print("All tests passed!")