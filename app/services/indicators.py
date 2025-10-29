"""Technical indicators calculation services"""

import pandas as pd
import numpy as np
from typing import List, Union


class TechnicalIndicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty else 50.0
    
    @staticmethod
    def calculate_ma(prices: pd.Series, period: int = 20) -> float:
        """Calculate Moving Average"""
        ma = prices.rolling(window=period).mean()
        return float(ma.iloc[-1]) if not ma.empty else 0.0
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int = 12) -> float:
        """Calculate Exponential Moving Average"""
        ema = prices.ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1]) if not ema.empty else 0.0
    
    @staticmethod
    def calculate_macd(prices: pd.Series) -> dict:
        """Calculate MACD indicator"""
        exp1 = prices.ewm(span=12, adjust=False).mean()
        exp2 = prices.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        
        return {
            "macd": float(macd.iloc[-1]) if not macd.empty else 0.0,
            "signal": float(signal.iloc[-1]) if not signal.empty else 0.0,
            "histogram": float(histogram.iloc[-1]) if not histogram.empty else 0.0
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            "upper": float(upper_band.iloc[-1]) if not upper_band.empty else 0.0,
            "middle": float(sma.iloc[-1]) if not sma.empty else 0.0,
            "lower": float(lower_band.iloc[-1]) if not lower_band.empty else 0.0
        }