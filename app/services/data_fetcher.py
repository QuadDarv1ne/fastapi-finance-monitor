"""Data fetching services for financial data"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
import asyncio
import time
import random
import aiohttp

# Custom exceptions
class DataFetchError(Exception):
    """Custom exception for data fetching errors"""
    pass

class RateLimitError(DataFetchError):
    """Exception for rate limiting errors"""
    pass

# Import cache service
from app.services.cache_service import get_cache_service

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetch financial data from various sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.rate_limit_delay = 0.1  # Delay between requests to avoid rate limiting
        self.max_retries = 3  # Maximum number of retry attempts
        self.cache_service = get_cache_service()
        self.request_timestamps = []  # Track request timing for rate limiting
        self.max_requests_per_minute = 60  # Limit requests per minute
        
    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = time.time()
        # Remove timestamps older than 1 minute
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            # Calculate sleep time to maintain rate limit
            oldest = min(self.request_timestamps)
            sleep_time = 60 - (now - oldest)
            if sleep_time > 0:
                logger.warning(f"Rate limit approaching, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
        
        # Add current timestamp
        self.request_timestamps.append(now)
    
    async def get_stock_data(self, symbol: str, period: str = "1d", interval: str = "5m") -> Optional[Dict]:
        """Get stock data from Yahoo Finance with improved error handling"""
        # Check cache first
        cache_key = f"stock_{symbol}_{period}_{interval}"
        cached_data = await self.cache_service.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {symbol}")
            return cached_data
        
        # Enforce rate limiting
        await self._check_rate_limit()
        
        # Try multiple times with exponential backoff
        for attempt in range(self.max_retries):
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
                
                # Limit chart data to last 100 points to reduce payload
                chart_data_limit = 100
                chart_data_full = [
                    {
                        "time": str(idx),
                        "open": float(row['Open']) if 'Open' in df.columns else current_price,
                        "high": float(row['High']) if 'High' in df.columns else current_price,
                        "low": float(row['Low']) if 'Low' in df.columns else current_price,
                        "close": float(row['Close']) if 'Close' in df.columns else current_price,
                        "volume": int(row['Volume']) if 'Volume' in df.columns else 0
                    }
                    for idx, row in df.iterrows()
                ]
                
                # Limit chart data size
                if len(chart_data_full) > chart_data_limit:
                    step = len(chart_data_full) // chart_data_limit
                    chart_data = chart_data_full[::step][:chart_data_limit]
                else:
                    chart_data = chart_data_full
                
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
                    "chart_data": chart_data
                }
                
                # Cache the data with adaptive TTL based on market hours
                now = datetime.now()
                is_market_hours = 9 <= now.hour <= 16 and now.weekday() < 5  # US market hours
                ttl = 30 if is_market_hours else 300  # 30s during market hours, 5min otherwise
                
                await self.cache_service.set(cache_key, data, ttl=ttl)
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                return data
            
            except yf.YFPricesError as e:
                logger.error(f"Yahoo Finance prices error for {symbol}: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying {symbol} in {delay:.2f} seconds (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise DataFetchError(f"Failed to fetch data for {symbol} after {self.max_retries} attempts: {e}")
            
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error fetching {symbol}: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying {symbol} in {delay:.2f} seconds (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise DataFetchError(f"Failed to connect to data source for {symbol} after {self.max_retries} attempts: {e}")
            
            except Exception as e:
                logger.error(f"Unexpected error fetching {symbol}: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying {symbol} in {delay:.2f} seconds (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise DataFetchError(f"Unexpected error fetching data for {symbol} after {self.max_retries} attempts: {e}")
        
        return None
    
    async def get_crypto_data(self, coin_id: str) -> Optional[Dict]:
        """Get crypto data from CoinGecko with improved error handling"""
        # Check cache first
        cache_key = f"crypto_{coin_id}"
        cached_data = await self.cache_service.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {coin_id}")
            return cached_data
        
        # Enforce rate limiting
        await self._check_rate_limit()
        
        # Try multiple times with exponential backoff
        for attempt in range(self.max_retries):
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
                
                # Handle rate limiting
                if response.status_code == 429:
                    logger.warning(f"Rate limit exceeded for {coin_id}")
                    if attempt < self.max_retries - 1:
                        # Exponential backoff with jitter
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        logger.info(f"Rate limited, retrying {coin_id} in {delay:.2f} seconds (attempt {attempt + 1})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise RateLimitError(f"Rate limit exceeded for {coin_id} after {self.max_retries} attempts")
                
                response.raise_for_status()
                price_data = response.json()
                
                if coin_id not in price_data:
                    logger.warning(f"No price data returned for {coin_id}")
                    return None
                
                # Historical data
                hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                hist_params = {"vs_currency": "usd", "days": "1", "interval": "hourly"}
                hist_response = await loop.run_in_executor(None, lambda: self.session.get(hist_url, params=hist_params, timeout=10))
                
                # Handle rate limiting for historical data
                if hist_response.status_code == 429:
                    logger.warning(f"Rate limit exceeded for {coin_id} historical data")
                    if attempt < self.max_retries - 1:
                        # Exponential backoff with jitter
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        logger.info(f"Rate limited, retrying {coin_id} historical data in {delay:.2f} seconds (attempt {attempt + 1})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise RateLimitError(f"Rate limit exceeded for {coin_id} historical data after {self.max_retries} attempts")
                
                hist_response.raise_for_status()
                hist_data = hist_response.json()
                
                current_price = price_data[coin_id]["usd"]
                market_cap = price_data[coin_id].get("usd_market_cap", 0)
                
                # Limit historical data points
                chart_data_limit = 50
                raw_chart_data = hist_data.get("prices", [])
                if len(raw_chart_data) > chart_data_limit:
                    step = len(raw_chart_data) // chart_data_limit
                    chart_data = [
                        {
                            "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                            "price": point[1]
                        }
                        for point in raw_chart_data[::step][:chart_data_limit]
                    ]
                else:
                    chart_data = [
                        {
                            "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                            "price": point[1]
                        }
                        for point in raw_chart_data
                    ]
                
                data = {
                    "symbol": coin_id.upper(),
                    "timestamp": datetime.now().isoformat(),
                    "current_price": current_price,
                    "change_percent": price_data[coin_id].get("usd_24h_change", 0),
                    "volume": price_data[coin_id].get("usd_24h_vol", 0),
                    "market_cap": market_cap,
                    "chart_data": chart_data
                }
                
                # Cache the data with adaptive TTL (crypto markets are 24/7)
                ttl = 30  # 30 seconds for crypto data
                
                await self.cache_service.set(cache_key, data, ttl=ttl)
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                return data
            
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error fetching {coin_id}: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying {coin_id} in {delay:.2f} seconds (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise DataFetchError(f"Failed to connect to data source for {coin_id} after {self.max_retries} attempts: {e}")
            
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout error fetching {coin_id}: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying {coin_id} in {delay:.2f} seconds (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise DataFetchError(f"Timeout error fetching data for {coin_id} after {self.max_retries} attempts: {e}")
            
            except Exception as e:
                logger.error(f"Unexpected error fetching {coin_id}: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying {coin_id} in {delay:.2f} seconds (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise DataFetchError(f"Unexpected error fetching data for {coin_id} after {self.max_retries} attempts: {e}")
        
        return None
    
    async def get_crypto_historical_data(self, coin_id: str, days: int = 30) -> Optional[Dict]:
        """Get historical crypto data from CoinGecko"""
        # Check cache first
        cache_key = f"crypto_hist_{coin_id}_{days}"
        cached_data = await self.cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        # Enforce rate limiting
        await self._check_rate_limit()
        
        try:
            # Historical data
            hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            hist_params = {"vs_currency": "usd", "days": str(days), "interval": "daily"}
            loop = asyncio.get_event_loop()
            hist_response = await loop.run_in_executor(None, lambda: self.session.get(hist_url, params=hist_params, timeout=10))
            hist_response.raise_for_status()
            hist_data = hist_response.json()
            
            if not hist_data.get("prices"):
                logger.warning(f"No historical data returned for {coin_id}")
                return None
            
            # Extract price data with limit
            chart_data_limit = 100
            raw_chart_data = hist_data.get("prices", [])
            if len(raw_chart_data) > chart_data_limit:
                step = len(raw_chart_data) // chart_data_limit
                chart_data = [
                    {
                        "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                        "price": point[1]
                    }
                    for point in raw_chart_data[::step][:chart_data_limit]
                ]
            else:
                chart_data = [
                    {
                        "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                        "price": point[1]
                    }
                    for point in raw_chart_data
                ]
            
            # Get current price if available
            current_price = chart_data[-1]["price"] if chart_data else 0
            
            data = {
                "symbol": coin_id.upper(),
                "timestamp": datetime.now().isoformat(),
                "current_price": current_price,
                "chart_data": chart_data
            }
            
            # Cache the data for 5 minutes
            await self.cache_service.set(cache_key, data, ttl=300)
            
            # Add a small delay to avoid rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching historical data for {coin_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching historical data for {coin_id}: {e}")
            return None
    
    async def get_forex_data(self, pair: str) -> Optional[Dict]:
        """Get forex data - placeholder for future implementation"""
        # Check cache first
        cache_key = f"forex_{pair}"
        cached_data = await self.cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        # Enforce rate limiting
        await self._check_rate_limit()
        
        try:
            # This is a simplified example - in reality, you'd use a forex API
            # For now, we'll return mock data with some realistic values
            import random
            
            # Generate realistic forex data
            base_price = 1.0 + random.uniform(-0.5, 0.5)
            change_percent = random.uniform(-2, 2)
            current_price = base_price * (1 + change_percent / 100)
            
            # Generate chart data
            chart_data = []
            for i in range(50):
                time_point = (datetime.now() - timedelta(minutes=i*5)).isoformat()
                price_point = current_price * (1 + random.uniform(-0.1, 0.1) / 100)
                chart_data.append({
                    "time": time_point,
                    "price": round(price_point, 6)
                })
            
            data = {
                "symbol": pair,
                "timestamp": datetime.now().isoformat(),
                "current_price": round(current_price, 6),
                "change_percent": round(change_percent, 4),
                "volume": random.randint(1000000, 100000000),
                "chart_data": chart_data
            }
            
            # Cache the data for 30 seconds
            await self.cache_service.set(cache_key, data, ttl=30)
            
            # Add a small delay to avoid rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            return data
        except Exception as e:
            logger.error(f"Error fetching forex data for {pair}: {e}")
            return None
    
    async def get_multiple_assets(self, assets: List[Dict]) -> List[Dict]:
        """Fetch data for multiple assets concurrently with improved error handling"""
        # Group assets by type for batch processing
        stock_assets = [asset for asset in assets if asset["type"] == "stock"]
        crypto_assets = [asset for asset in assets if asset["type"] == "crypto"]
        other_assets = [asset for asset in assets if asset["type"] not in ["stock", "crypto"]]
        
        results = []
        
        # Process stocks in smaller batches to avoid API limits
        batch_size = 5
        for i in range(0, len(stock_assets), batch_size):
            batch = stock_assets[i:i + batch_size]
            batch_tasks = []
            for asset in batch:
                task = self.get_stock_data(asset["symbol"])
                batch_tasks.append(task)
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching {batch[j]['symbol']}: {result}")
                elif isinstance(result, DataFetchError):
                    logger.error(f"Data fetch error for {batch[j]['symbol']}: {result}")
                elif result is not None and not isinstance(result, BaseException):
                    result["name"] = batch[j]["name"]
                    result["type"] = batch[j]["type"]
                    results.append(result)
                else:
                    logger.warning(f"No data returned for {batch[j]['symbol']}")
            
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(stock_assets):
                await asyncio.sleep(0.5)
        
        # Process crypto assets
        if crypto_assets:
            crypto_tasks = []
            for asset in crypto_assets:
                task = self.get_crypto_data(asset["symbol"])
                crypto_tasks.append(task)
            
            crypto_results = await asyncio.gather(*crypto_tasks, return_exceptions=True)
            for j, result in enumerate(crypto_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching {crypto_assets[j]['symbol']}: {result}")
                elif isinstance(result, DataFetchError):
                    logger.error(f"Data fetch error for {crypto_assets[j]['symbol']}: {result}")
                elif result is not None and not isinstance(result, BaseException):
                    result["name"] = crypto_assets[j]["name"]
                    result["type"] = crypto_assets[j]["type"]
                    results.append(result)
                else:
                    logger.warning(f"No data returned for {crypto_assets[j]['symbol']}")
        
        # Process other assets
        if other_assets:
            other_tasks = []
            for asset in other_assets:
                if asset["type"] == "forex":
                    task = self.get_forex_data(asset["symbol"])
                else:
                    task = self.get_forex_data(asset["symbol"])
                other_tasks.append(task)
            
            other_results = await asyncio.gather(*other_tasks, return_exceptions=True)
            for j, result in enumerate(other_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching {other_assets[j]['symbol']}: {result}")
                elif isinstance(result, DataFetchError):
                    logger.error(f"Data fetch error for {other_assets[j]['symbol']}: {result}")
                elif result is not None and not isinstance(result, BaseException):
                    result["name"] = other_assets[j]["name"]
                    result["type"] = other_assets[j]["type"]
                    results.append(result)
                else:
                    logger.warning(f"No data returned for {other_assets[j]['symbol']}")
        
        return results