"""Technical indicators calculation services"""

import pandas as pd
import numpy as np
from typing import List, Union, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1]) if not rsi.empty and not np.isnan(rsi.iloc[-1]) else 50.0
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return 50.0
    
    @staticmethod
    def calculate_ma(prices: pd.Series, period: int = 20) -> float:
        """Calculate Moving Average"""
        try:
            if len(prices) < period:
                return float(prices.iloc[-1]) if not prices.empty else 0.0
            
            ma = prices.rolling(window=period).mean()
            return float(ma.iloc[-1]) if not ma.empty and not np.isnan(ma.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating MA: {e}")
            return 0.0
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int = 12) -> float:
        """Calculate Exponential Moving Average"""
        try:
            if len(prices) < period:
                return float(prices.iloc[-1]) if not prices.empty else 0.0
            
            ema = prices.ewm(span=period, adjust=False).mean()
            return float(ema.iloc[-1]) if not ema.empty and not np.isnan(ema.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return 0.0
    
    @staticmethod
    def calculate_macd(prices: pd.Series) -> Dict[str, float]:
        """Calculate MACD indicator"""
        try:
            if len(prices) < 26:
                return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
            
            exp1 = prices.ewm(span=12, adjust=False).mean()
            exp2 = prices.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            
            macd_val = float(macd.iloc[-1]) if not macd.empty and not np.isnan(macd.iloc[-1]) else 0.0
            signal_val = float(signal.iloc[-1]) if not signal.empty and not np.isnan(signal.iloc[-1]) else 0.0
            histogram_val = float(histogram.iloc[-1]) if not histogram.empty and not np.isnan(histogram.iloc[-1]) else 0.0
            
            return {
                "macd": macd_val,
                "signal": signal_val,
                "histogram": histogram_val
            }
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        try:
            if len(prices) < period:
                current_price = float(prices.iloc[-1]) if not prices.empty else 0.0
                return {"upper": current_price, "middle": current_price, "lower": current_price}
            
            sma = prices.rolling(period).mean()
            std = prices.rolling(period).std()
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            
            upper_val = float(upper_band.iloc[-1]) if not upper_band.empty and not np.isnan(upper_band.iloc[-1]) else 0.0
            middle_val = float(sma.iloc[-1]) if not sma.empty and not np.isnan(sma.iloc[-1]) else 0.0
            lower_val = float(lower_band.iloc[-1]) if not lower_band.empty and not np.isnan(lower_band.iloc[-1]) else 0.0
            
            return {
                "upper": upper_val,
                "middle": middle_val,
                "lower": lower_val
            }
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            current_price = float(prices.iloc[-1]) if not prices.empty else 0.0
            return {"upper": current_price, "middle": current_price, "lower": current_price}
    
    @staticmethod
    def calculate_stochastic_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Dict[str, float]:
        """Calculate Stochastic Oscillator"""
        try:
            if len(high) < k_period or len(low) < k_period or len(close) < k_period:
                return {"k": 50.0, "d": 50.0}
            
            lowest_low = low.rolling(k_period).min()
            highest_high = high.rolling(k_period).max()
            k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            d = k.rolling(d_period).mean()
            
            k_val = float(k.iloc[-1]) if not k.empty and not np.isnan(k.iloc[-1]) else 50.0
            d_val = float(d.iloc[-1]) if not d.empty and not np.isnan(d.iloc[-1]) else 50.0
            
            return {
                "k": k_val,
                "d": d_val
            }
        except Exception as e:
            logger.error(f"Error calculating Stochastic Oscillator: {e}")
            return {"k": 50.0, "d": 50.0}
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            if len(high) < period or len(low) < period or len(close) < period:
                return 0.0
            
            tr0 = abs(high - low)
            tr1 = abs(high - close.shift())
            tr2 = abs(low - close.shift())
            tr = pd.DataFrame({'tr0': tr0, 'tr1': tr1, 'tr2': tr2}).max(axis=1)
            atr = tr.rolling(period).mean()
            return float(atr.iloc[-1]) if not atr.empty and not np.isnan(atr.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0.0
    
    @staticmethod
    def calculate_ichimoku_cloud(high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, float]:
        """Calculate Ichimoku Cloud indicators"""
        try:
            if len(high) < 9 or len(low) < 9 or len(close) < 9:
                return {
                    "tenkan_sen": 0.0,
                    "kijun_sen": 0.0,
                    "senkou_span_a": 0.0,
                    "senkou_span_b": 0.0,
                    "chikou_span": 0.0
                }
            
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
            
            tenkan_val = float(tenkan_sen.iloc[-1]) if not tenkan_sen.empty and not np.isnan(tenkan_sen.iloc[-1]) else 0.0
            kijun_val = float(kijun_sen.iloc[-1]) if not kijun_sen.empty and not np.isnan(kijun_sen.iloc[-1]) else 0.0
            senkou_a_val = float(senkou_span_a.iloc[-1]) if not senkou_span_a.empty and not np.isnan(senkou_span_a.iloc[-1]) else 0.0
            senkou_b_val = float(senkou_span_b.iloc[-1]) if not senkou_span_b.empty and not np.isnan(senkou_span_b.iloc[-1]) else 0.0
            chikou_val = float(chikou_span.iloc[0]) if not chikou_span.empty and not np.isnan(chikou_span.iloc[0]) else 0.0
            
            return {
                "tenkan_sen": tenkan_val,
                "kijun_sen": kijun_val,
                "senkou_span_a": senkou_a_val,
                "senkou_span_b": senkou_b_val,
                "chikou_span": chikou_val
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
            if high <= low:
                return {
                    "23.6%": low,
                    "38.2%": low,
                    "50.0%": low,
                    "61.8%": low,
                    "78.6%": low
                }
            
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
            if len(high) < period + 1 or len(low) < period + 1 or len(close) < period + 1:
                return 0.0
            
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
            
            return float(adx.iloc[-1]) if not adx.empty and not np.isnan(adx.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating ADX: {e}")
            return 0.0
    
    @staticmethod
    def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Williams %R"""
        try:
            if len(high) < period or len(low) < period or len(close) < period:
                return 0.0
            
            highest_high = high.rolling(period).max()
            lowest_low = low.rolling(period).min()
            williams_r = -100 * ((highest_high - close) / (highest_high - lowest_low))
            return float(williams_r.iloc[-1]) if not williams_r.empty and not np.isnan(williams_r.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating Williams %R: {e}")
            return 0.0
    
    @staticmethod
    def calculate_cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> float:
        """Calculate Commodity Channel Index"""
        try:
            if len(high) < period or len(low) < period or len(close) < period:
                return 0.0
            
            # Calculate typical price
            tp = (high + low + close) / 3
            
            # Calculate SMA of typical price
            sma_tp = tp.rolling(period).mean()
            
            # Calculate mean deviation
            mean_dev = tp.rolling(period).apply(lambda x: abs(x - x.mean()).mean())
            
            # Calculate CCI
            cci = (tp - sma_tp) / (0.015 * mean_dev)
            
            return float(cci.iloc[-1]) if not cci.empty and not np.isnan(cci.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating CCI: {e}")
            return 0.0
    
    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> float:
        """Calculate On-Balance Volume"""
        try:
            if len(close) < 2 or len(volume) < 2:
                return float(volume.iloc[-1]) if not volume.empty else 0.0
            
            # Calculate OBV
            obv = pd.Series(index=close.index, dtype=float)
            obv.iloc[0] = volume.iloc[0]
            
            for i in range(1, len(close)):
                if close.iloc[i] > close.iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
                elif close.iloc[i] < close.iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i-1]
            
            return float(obv.iloc[-1]) if not obv.empty and not np.isnan(obv.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating OBV: {e}")
            return float(volume.iloc[-1]) if not volume.empty else 0.0
    
    @staticmethod
    def calculate_parabolic_sar(high: pd.Series, low: pd.Series, close: pd.Series, 
                              acceleration: float = 0.02, maximum: float = 0.2) -> Dict[str, Union[float, str]]:
        """Calculate Parabolic SAR (Stop and Reverse)"""
        try:
            if len(high) < 2 or len(low) < 2 or len(close) < 2:
                return {
                    "value": float(close.iloc[-1]) if not close.empty else 0.0,
                    "trend": "bullish",
                    "extreme_point": float(high.iloc[-1]) if not high.empty else 0.0,
                    "acceleration_factor": acceleration
                }
            
            # Initialize arrays
            sar = pd.Series(index=close.index, dtype=float)
            trend = pd.Series(index=close.index, dtype=str)
            ep = pd.Series(index=close.index, dtype=float)  # Extreme point
            af = pd.Series(index=close.index, dtype=float)  # Acceleration factor
            
            # Initialize first values
            sar.iloc[0] = low.iloc[0]
            trend.iloc[0] = 'bullish'
            ep.iloc[0] = high.iloc[0]
            af.iloc[0] = acceleration
            
            for i in range(1, len(close)):
                # Update SAR based on previous trend
                sar.iloc[i] = sar.iloc[i-1] + af.iloc[i-1] * (ep.iloc[i-1] - sar.iloc[i-1])
                
                if trend.iloc[i-1] == 'bullish':
                    # Update for bullish trend
                    if low.iloc[i] < sar.iloc[i]:
                        # Trend reversal
                        trend.iloc[i] = 'bearish'
                        sar.iloc[i] = ep.iloc[i-1]
                        ep.iloc[i] = low.iloc[i]
                        af.iloc[i] = acceleration
                    else:
                        # Continue bullish trend
                        trend.iloc[i] = 'bullish'
                        if high.iloc[i] > ep.iloc[i-1]:
                            ep.iloc[i] = high.iloc[i]
                            af.iloc[i] = min(af.iloc[i-1] + acceleration, maximum)
                        else:
                            ep.iloc[i] = ep.iloc[i-1]
                            af.iloc[i] = af.iloc[i-1]
                else:
                    # Update for bearish trend
                    if high.iloc[i] > sar.iloc[i]:
                        # Trend reversal
                        trend.iloc[i] = 'bullish'
                        sar.iloc[i] = ep.iloc[i-1]
                        ep.iloc[i] = high.iloc[i]
                        af.iloc[i] = acceleration
                    else:
                        # Continue bearish trend
                        trend.iloc[i] = 'bearish'
                        if low.iloc[i] < ep.iloc[i-1]:
                            ep.iloc[i] = low.iloc[i]
                            af.iloc[i] = min(af.iloc[i-1] + acceleration, maximum)
                        else:
                            ep.iloc[i] = ep.iloc[i-1]
                            af.iloc[i] = af.iloc[i-1]
            
            sar_val = float(sar.iloc[-1]) if not sar.empty and not np.isnan(sar.iloc[-1]) else 0.0
            trend_val = str(trend.iloc[-1]) if not trend.empty else 'bullish'
            ep_val = float(ep.iloc[-1]) if not ep.empty and not np.isnan(ep.iloc[-1]) else 0.0
            af_val = float(af.iloc[-1]) if not af.empty and not np.isnan(af.iloc[-1]) else acceleration
            
            return {
                "value": sar_val,
                "trend": trend_val,
                "extreme_point": ep_val,
                "acceleration_factor": af_val
            }
        except Exception as e:
            logger.error(f"Error calculating Parabolic SAR: {e}")
            return {
                "value": float(close.iloc[-1]) if not close.empty else 0.0,
                "trend": "bullish",
                "extreme_point": float(high.iloc[-1]) if not high.empty else 0.0,
                "acceleration_factor": acceleration
            }
    
    @staticmethod
    def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, 
                      volume: pd.Series, period: int = 20) -> float:
        """Calculate Volume Weighted Average Price"""
        try:
            if len(high) < period or len(low) < period or len(close) < period or len(volume) < period:
                # Calculate simple average if not enough data
                typical_price = (high.iloc[-1] + low.iloc[-1] + close.iloc[-1]) / 3
                return float(typical_price)
            
            # Calculate typical price
            typical_price = (high + low + close) / 3
            
            # Calculate VWAP
            vwap = (typical_price * volume).rolling(period).sum() / volume.rolling(period).sum()
            
            return float(vwap.iloc[-1]) if not vwap.empty and not np.isnan(vwap.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            # Fallback to simple average
            if not high.empty and not low.empty and not close.empty:
                typical_price = (high.iloc[-1] + low.iloc[-1] + close.iloc[-1]) / 3
                return float(typical_price)
            return 0.0
    
    @staticmethod
    def calculate_momentum(prices: pd.Series, period: int = 10) -> float:
        """Calculate Momentum indicator"""
        try:
            if len(prices) < period + 1:
                return 0.0
            
            momentum = prices - prices.shift(period)
            return float(momentum.iloc[-1]) if not momentum.empty and not np.isnan(momentum.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating Momentum: {e}")
            return 0.0
    
    @staticmethod
    def calculate_roc(prices: pd.Series, period: int = 12) -> float:
        """Calculate Rate of Change"""
        try:
            if len(prices) < period + 1:
                return 0.0
            
            roc = ((prices - prices.shift(period)) / prices.shift(period)) * 100
            return float(roc.iloc[-1]) if not roc.empty and not np.isnan(roc.iloc[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculating ROC: {e}")
            return 0.0
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> Dict[str, Union[float, Dict]]:
        """Calculate all technical indicators from a DataFrame with OHLC data"""
        try:
            if df.empty:
                return {}
            
            close_prices = df['Close']
            high_prices = df.get('High', close_prices)
            low_prices = df.get('Low', close_prices)
            volume = df.get('Volume', pd.Series([0] * len(df)))
            
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
                "adx": TechnicalIndicators.calculate_adx(high_prices, low_prices, close_prices),
                "williams_r": TechnicalIndicators.calculate_williams_r(high_prices, low_prices, close_prices),
                "cci": TechnicalIndicators.calculate_cci(high_prices, low_prices, close_prices),
                "obv": TechnicalIndicators.calculate_obv(close_prices, volume),
                "parabolic_sar": TechnicalIndicators.calculate_parabolic_sar(high_prices, low_prices, close_prices),
                "vwap": TechnicalIndicators.calculate_vwap(high_prices, low_prices, close_prices, volume),
                "momentum": TechnicalIndicators.calculate_momentum(close_prices),
                "roc": TechnicalIndicators.calculate_roc(close_prices)
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