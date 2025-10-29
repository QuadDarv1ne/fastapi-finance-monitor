"""Data fetching services for financial data"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from typing import Dict, Optional, List
import logging
import asyncio

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetch financial data from various sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    async def get_stock_data(self, symbol: str, period: str = "1d", interval: str = "5m") -> Optional[Dict]:
        """Get stock data from Yahoo Finance"""
        try:
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            
            # Run history in executor to avoid blocking
            df = await loop.run_in_executor(None, ticker.history, period, interval)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Calculate additional metrics
            current_price = float(df['Close'].iloc[-1])
            open_price = float(df['Open'].iloc[0])
            change = current_price - open_price
            change_percent = (change / open_price) * 100
            
            data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "current_price": current_price,
                "change": change,
                "change_percent": change_percent,
                "volume": int(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0,
                "open": open_price,
                "high": float(df['High'].max()) if 'High' in df.columns else current_price,
                "low": float(df['Low'].min()) if 'Low' in df.columns else current_price,
                "chart_data": [
                    {
                        "time": str(idx),
                        "open": float(row['Open']) if 'Open' in df.columns else current_price,
                        "high": float(row['High']) if 'High' in df.columns else current_price,
                        "low": float(row['Low']) if 'Low' in df.columns else current_price,
                        "close": float(row['Close']) if 'Close' in df.columns else current_price,
                        "volume": int(row['Volume']) if 'Volume' in df.columns else 0
                    }
                    for idx, row in df.tail(50).iterrows()
                ]
            }
            return data
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    async def get_crypto_data(self, coin_id: str) -> Optional[Dict]:
        """Get crypto data from CoinGecko"""
        try:
            # Current price
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_market_cap": "true"
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.session.get(url, params=params, timeout=10))
            response.raise_for_status()
            price_data = response.json()
            
            if coin_id not in price_data:
                logger.warning(f"No price data returned for {coin_id}")
                return None
            
            # Historical data
            hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            hist_params = {"vs_currency": "usd", "days": "1", "interval": "hourly"}
            hist_response = await loop.run_in_executor(None, lambda: self.session.get(hist_url, params=hist_params, timeout=10))
            hist_response.raise_for_status()
            hist_data = hist_response.json()
            
            current_price = price_data[coin_id]["usd"]
            market_cap = price_data[coin_id].get("usd_market_cap", 0)
            
            data = {
                "symbol": coin_id.upper(),
                "timestamp": datetime.now().isoformat(),
                "current_price": current_price,
                "change_percent": price_data[coin_id].get("usd_24h_change", 0),
                "volume": price_data[coin_id].get("usd_24h_vol", 0),
                "market_cap": market_cap,
                "chart_data": [
                    {
                        "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                        "price": point[1]
                    }
                    for point in hist_data.get("prices", [])[-50:]
                ]
            }
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching {coin_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {coin_id}: {e}")
            return None
    
    async def get_forex_data(self, pair: str) -> Optional[Dict]:
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
    
    async def get_multiple_assets(self, assets: List[Dict]) -> List[Dict]:
        """Fetch data for multiple assets concurrently"""
        tasks = []
        for asset in assets:
            if asset["type"] == "stock":
                task = self.get_stock_data(asset["symbol"])
            elif asset["type"] == "crypto":
                task = self.get_crypto_data(asset["symbol"])
            else:
                task = self.get_forex_data(asset["symbol"])
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None values
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {assets[i]['symbol']}: {result}")
            elif result is not None and not isinstance(result, BaseException):
                result["name"] = assets[i]["name"]
                result["type"] = assets[i]["type"]
                valid_results.append(result)
        
        return valid_results