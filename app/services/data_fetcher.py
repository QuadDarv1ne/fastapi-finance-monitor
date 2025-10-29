"""Data fetching services for financial data"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetch financial data from various sources"""
    
    @staticmethod
    async def get_stock_data(symbol: str, period: str = "1d", interval: str = "5m") -> Optional[Dict]:
        """Get stock data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "current_price": float(df['Close'].iloc[-1]),
                "change": float(df['Close'].iloc[-1] - df['Close'].iloc[0]),
                "change_percent": float((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100),
                "volume": int(df['Volume'].iloc[-1]),
                "chart_data": [
                    {
                        "time": str(idx),
                        "open": float(row['Open']),
                        "high": float(row['High']),
                        "low": float(row['Low']),
                        "close": float(row['Close']),
                        "volume": int(row['Volume'])
                    }
                    for idx, row in df.tail(50).iterrows()
                ]
            }
            return data
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    @staticmethod
    async def get_crypto_data(coin_id: str) -> Optional[Dict]:
        """Get crypto data from CoinGecko"""
        try:
            # Current price
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            }
            response = requests.get(url, params=params, timeout=5)
            price_data = response.json()
            
            if coin_id not in price_data:
                logger.warning(f"No price data returned for {coin_id}")
                return None
            
            # Historical data
            hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            hist_params = {"vs_currency": "usd", "days": "1", "interval": "hourly"}
            hist_response = requests.get(hist_url, params=hist_params, timeout=5)
            hist_data = hist_response.json()
            
            current_price = price_data[coin_id]["usd"]
            
            data = {
                "symbol": coin_id.upper(),
                "timestamp": datetime.now().isoformat(),
                "current_price": current_price,
                "change_percent": price_data[coin_id].get("usd_24h_change", 0),
                "volume": price_data[coin_id].get("usd_24h_vol", 0),
                "chart_data": [
                    {
                        "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                        "price": point[1]
                    }
                    for point in hist_data.get("prices", [])[-50:]
                ]
            }
            return data
        except Exception as e:
            logger.error(f"Error fetching {coin_id}: {e}")
            return None
    
    @staticmethod
    async def get_forex_data(pair: str) -> Optional[Dict]:
        """Get forex data - placeholder for future implementation"""
        try:
            # This is a simplified example - in reality, you'd use a forex API
            # For now, we'll return mock data
            data = {
                "symbol": pair,
                "timestamp": datetime.now().isoformat(),
                "current_price": 1.0,  # Placeholder
                "change_percent": 0.0,  # Placeholder
                "volume": 0,  # Placeholder
                "chart_data": []
            }
            return data
        except Exception as e:
            logger.error(f"Error fetching forex data for {pair}: {e}")
            return None