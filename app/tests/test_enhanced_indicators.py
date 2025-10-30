"""Tests for the enhanced technical indicators"""

import pytest
import pandas as pd
import numpy as np
from app.services.indicators import TechnicalIndicators


def test_parabolic_sar():
    """Test Parabolic SAR calculation"""
    # Create sample data
    high = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
    low = pd.Series([98, 100, 99, 101, 103, 102, 104, 106, 105, 107])
    close = pd.Series([99, 101, 100, 102, 104, 103, 105, 107, 106, 108])
    
    # Test Parabolic SAR calculation
    result = TechnicalIndicators.calculate_parabolic_sar(high, low, close)
    
    assert isinstance(result, dict)
    assert "value" in result
    assert "trend" in result
    assert "extreme_point" in result
    assert "acceleration_factor" in result
    assert isinstance(result["value"], (int, float))
    assert result["trend"] in ["bullish", "bearish"]


def test_vwap():
    """Test VWAP calculation"""
    # Create sample data
    high = pd.Series([100, 102, 101, 103, 105])
    low = pd.Series([98, 100, 99, 101, 103])
    close = pd.Series([99, 101, 100, 102, 104])
    volume = pd.Series([1000, 1200, 800, 1500, 1100])
    
    # Test VWAP calculation
    vwap = TechnicalIndicators.calculate_vwap(high, low, close, volume)
    
    assert isinstance(vwap, (int, float))
    # VWAP should be positive for positive prices
    assert vwap > 0


def test_momentum():
    """Test Momentum calculation"""
    # Create sample data
    prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
    
    # Test Momentum calculation
    momentum = TechnicalIndicators.calculate_momentum(prices)
    
    assert isinstance(momentum, (int, float))


def test_roc():
    """Test Rate of Change calculation"""
    # Create sample data
    prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
    
    # Test ROC calculation
    roc = TechnicalIndicators.calculate_roc(prices)
    
    assert isinstance(roc, (int, float))


def test_all_indicators_enhanced():
    """Test all indicators with enhanced functionality"""
    # Create sample data
    close_prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 112, 111, 113, 115])
    high_prices = pd.Series([101, 103, 102, 104, 106, 105, 107, 109, 108, 110, 111, 113, 112, 114, 116])
    low_prices = pd.Series([99, 101, 100, 102, 104, 103, 105, 107, 106, 108, 109, 111, 110, 112, 114])
    volume = pd.Series([1000, 1200, 800, 1500, 1100, 900, 1300, 1600, 1400, 1200, 1100, 1300, 1000, 1400, 1500])
    
    # Create DataFrame
    df = pd.DataFrame({
        'Close': close_prices,
        'High': high_prices,
        'Low': low_prices,
        'Volume': volume
    })
    
    # Test all indicators calculation
    indicators = TechnicalIndicators.calculate_all_indicators(df)
    
    # Check that all expected indicators are present
    expected_indicators = [
        "rsi", "ma_20", "ma_50", "ema_12", "ema_26", "macd", "bollinger_bands",
        "stochastic", "atr", "ichimoku", "adx", "williams_r", "cci", "obv",
        "parabolic_sar", "vwap", "momentum", "roc", "fibonacci"
    ]
    
    for indicator in expected_indicators:
        assert indicator in indicators, f"Missing indicator: {indicator}"
    
    # Check specific indicator types
    assert isinstance(indicators["rsi"], (int, float))
    assert isinstance(indicators["macd"], dict)
    assert isinstance(indicators["bollinger_bands"], dict)
    assert isinstance(indicators["parabolic_sar"], dict)
    assert isinstance(indicators["fibonacci"], dict)


def test_parabolic_sar_edge_cases():
    """Test Parabolic SAR with edge cases"""
    # Test with minimal data
    high = pd.Series([100, 101])
    low = pd.Series([99, 100])
    close = pd.Series([99.5, 100.5])
    
    result = TechnicalIndicators.calculate_parabolic_sar(high, low, close)
    
    assert isinstance(result, dict)
    assert "value" in result
    assert "trend" in result


def test_vwap_edge_cases():
    """Test VWAP with edge cases"""
    # Test with minimal data
    high = pd.Series([100])
    low = pd.Series([99])
    close = pd.Series([99.5])
    volume = pd.Series([1000])
    
    vwap = TechnicalIndicators.calculate_vwap(high, low, close, volume)
    
    assert isinstance(vwap, (int, float))


if __name__ == "__main__":
    test_parabolic_sar()
    test_vwap()
    test_momentum()
    test_roc()
    test_all_indicators_enhanced()
    test_parabolic_sar_edge_cases()
    test_vwap_edge_cases()
    print("All enhanced indicators tests passed!")