"""Technical indicators calculation services"""

import pandas as pd
import numpy as np
from typing import List, Union, Dict
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1]) if not rsi.empty else 50.0
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return 50.0
    
    @staticmethod
    def calculate_ma(prices: pd.Series, period: int = 20) -> float:
        """Calculate Moving Average"""
        try:
            ma = prices.rolling(window=period).mean()
            return float(ma.iloc[-1]) if not ma.empty else 0.0
        except Exception as e:
            logger.error(f"Error calculating MA: {e}")
            return 0.0
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int = 12) -> float:
        """Calculate Exponential Moving Average"""
        try:
            ema = prices.ewm(span=period, adjust=False).mean()
            return float(ema.iloc[-1]) if not ema.empty else 0.0
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return 0.0
    
    @staticmethod
    def calculate_macd(prices: pd.Series) -> Dict[str, float]:
        """Calculate MACD indicator"""
        try:
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
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        try:
            sma = prices.rolling(period).mean()
            std = prices.rolling(period).std()
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            
            return {
                "upper": float(upper_band.iloc[-1]) if not upper_band.empty else 0.0,
                "middle": float(sma.iloc[-1]) if not sma.empty else 0.0,
                "lower": float(lower_band.iloc[-1]) if not lower_band.empty else 0.0
            }
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {"upper": 0.0, "middle": 0.0, "lower": 0.0}
    
    @staticmethod
    def calculate_stochastic_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Dict[str, float]:
        """Calculate Stochastic Oscillator"""
        try:
            lowest_low = low.rolling(k_period).min()
            highest_high = high.rolling(k_period).max()
            k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            d = k.rolling(d_period).mean()
            
            return {
                "k": float(k.iloc[-1]) if not k.empty else 50.0,
                "d": float(d.iloc[-1]) if not d.empty else 50.0
            }
        except Exception as e:
            logger.error(f"Error calculating Stochastic Oscillator: {e}")
            return {"k": 50.0, "d": 50.0}
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            tr0 = abs(high - low)
            tr1 = abs(high - close.shift())
            tr2 = abs(low - close.shift())
            tr = pd.DataFrame({'tr0': tr0, 'tr1': tr1, 'tr2': tr2}).max(axis=1)
            atr = tr.rolling(period).mean()
            return float(atr.iloc[-1]) if not atr.empty else 0.0
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0.0
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> Dict[str, Union[float, Dict]]:
        """Calculate all technical indicators from a DataFrame with OHLC data"""
        try:
            close_prices = df['Close']
            high_prices = df.get('High', close_prices)
            low_prices = df.get('Low', close_prices)
            
            indicators = {
                "rsi": TechnicalIndicators.calculate_rsi(close_prices),
                "ma_20": TechnicalIndicators.calculate_ma(close_prices, 20),
                "ma_50": TechnicalIndicators.calculate_ma(close_prices, 50),
                "ema_12": TechnicalIndicators.calculate_ema(close_prices, 12),
                "ema_26": TechnicalIndicators.calculate_ema(close_prices, 26),
                "macd": TechnicalIndicators.calculate_macd(close_prices),
                "bollinger_bands": TechnicalIndicators.calculate_bollinger_bands(close_prices),
                "stochastic": TechnicalIndicators.calculate_stochastic_oscillator(high_prices, low_prices, close_prices),
                "atr": TechnicalIndicators.calculate_atr(high_prices, low_prices, close_prices)
            }
            
            return indicators
        except Exception as e:
            logger.error(f"Error calculating all indicators: {e}")
            return {}