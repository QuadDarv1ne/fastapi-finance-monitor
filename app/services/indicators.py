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
    def calculate_ichimoku_cloud(high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, float]:
        """Calculate Ichimoku Cloud indicators"""
        try:
            # Tenkan-sen (Conversion Line)
            tenkan_sen = (high.rolling(9).max() + low.rolling(9).min()) / 2
            
            # Kijun-sen (Base Line)
            kijun_sen = (high.rolling(26).max() + low.rolling(26).min()) / 2
            
            # Senkou Span A (Leading Span A)
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
            
            # Senkou Span B (Leading Span B)
            senkou_span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
            
            # Chikou Span (Lagging Span)
            chikou_span = close.shift(-26)
            
            return {
                "tenkan_sen": float(tenkan_sen.iloc[-1]) if not tenkan_sen.empty else 0.0,
                "kijun_sen": float(kijun_sen.iloc[-1]) if not kijun_sen.empty else 0.0,
                "senkou_span_a": float(senkou_span_a.iloc[-1]) if not senkou_span_a.empty else 0.0,
                "senkou_span_b": float(senkou_span_b.iloc[-1]) if not senkou_span_b.empty else 0.0,
                "chikou_span": float(chikou_span.iloc[0]) if not chikou_span.empty else 0.0
            }
        except Exception as e:
            logger.error(f"Error calculating Ichimoku Cloud: {e}")
            return {
                "tenkan_sen": 0.0,
                "kijun_sen": 0.0,
                "senkou_span_a": 0.0,
                "senkou_span_b": 0.0,
                "chikou_span": 0.0
            }
    
    @staticmethod
    def calculate_fibonacci_retracement(high: float, low: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        try:
            diff = high - low
            
            levels = {
                "23.6%": high - (diff * 0.236),
                "38.2%": high - (diff * 0.382),
                "50.0%": high - (diff * 0.5),
                "61.8%": high - (diff * 0.618),
                "78.6%": high - (diff * 0.786)
            }
            
            return {key: float(value) for key, value in levels.items()}
        except Exception as e:
            logger.error(f"Error calculating Fibonacci retracement: {e}")
            return {
                "23.6%": 0.0,
                "38.2%": 0.0,
                "50.0%": 0.0,
                "61.8%": 0.0,
                "78.6%": 0.0
            }
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Average Directional Index"""
        try:
            # Calculate True Range
            tr = pd.DataFrame({
                'h-l': abs(high - low),
                'h-pc': abs(high - close.shift()),
                'l-pc': abs(low - close.shift())
            }).max(axis=1)
            
            # Calculate +DM and -DM
            plus_dm = high.diff()
            minus_dm = low.diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm > 0] = 0
            
            # Calculate +DI and -DI
            tr_smooth = tr.rolling(period).sum()
            plus_dm_smooth = plus_dm.rolling(period).sum()
            minus_dm_smooth = minus_dm.rolling(period).sum()
            
            plus_di = 100 * (plus_dm_smooth / tr_smooth)
            minus_di = 100 * (minus_dm_smooth.abs() / tr_smooth)
            
            # Calculate DX
            dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
            
            # Calculate ADX
            adx = dx.rolling(period).mean()
            
            return float(adx.iloc[-1]) if not adx.empty else 0.0
        except Exception as e:
            logger.error(f"Error calculating ADX: {e}")
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
                "atr": TechnicalIndicators.calculate_atr(high_prices, low_prices, close_prices),
                "ichimoku": TechnicalIndicators.calculate_ichimoku_cloud(high_prices, low_prices, close_prices),
                "adx": TechnicalIndicators.calculate_adx(high_prices, low_prices, close_prices)
            }
            
            # Add Fibonacci retracement if we have high and low values
            if len(high_prices) > 0 and len(low_prices) > 0:
                indicators["fibonacci"] = TechnicalIndicators.calculate_fibonacci_retracement(
                    float(high_prices.max()), 
                    float(low_prices.min())
                )
            
            return indicators
        except Exception as e:
            logger.error(f"Error calculating all indicators: {e}")
            return {}