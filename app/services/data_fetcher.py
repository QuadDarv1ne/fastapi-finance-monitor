"""Data fetching services for financial data with enhanced reliability and caching"""

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
from functools import wraps

# Import custom exceptions
from app.exceptions.custom_exceptions import DataFetchError, RateLimitError, DataValidationError, NetworkError, TimeoutError

# Import cache service
from app.services.cache_service import get_cache_service

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=5, delay=1, backoff_factor=2, exceptions=(Exception,)):
    """Decorator to retry function calls on failure with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        # Calculate delay with exponential backoff and jitter
                        sleep_time = delay * (backoff_factor ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {sleep_time:.2f} seconds...")
                        await asyncio.sleep(sleep_time)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
            raise last_exception
        return wrapper
    return decorator

class DataFetcher:
    """Fetch financial data from various sources with enhanced reliability and caching"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        self.rate_limit_delay = 0.2  # Increased delay between requests to avoid rate limiting
        self.max_retries = 5  # Increased maximum number of retry attempts
        self.cache_service = get_cache_service()
        self.request_timestamps = []  # Track request timing for rate limiting
        self.max_requests_per_minute = 50  # Reduced requests per minute to be more conservative
        self.data_sources = {
            'yahoo_finance': self._fetch_from_yahoo_finance,
            'coingecko': self._fetch_from_coingecko,
            'mock': self._fetch_from_mock
        }
        # Semaphore to limit concurrent requests
        self.semaphore = asyncio.Semaphore(5)  # Reduced to 5 concurrent requests for better reliability
        # Cache warming patterns for frequently accessed data
        self.frequently_accessed_assets = {
            'stock_AAPL_1d_5m': None,
            'stock_GOOG_1d_5m': None,
            'stock_MSFT_1d_5m': None,
            'crypto_bitcoin': None,
            'crypto_ethereum': None
        }
        
    async def initialize_cache_warming(self):
        """Initialize cache warming for frequently accessed assets"""
        logger.info("Initializing cache warming for frequently accessed assets")
        try:
            # Fetch initial data for frequently accessed assets
            warm_data = {}
            for asset_key in self.frequently_accessed_assets.keys():
                if asset_key.startswith('stock_'):
                    parts = asset_key.split('_')
                    symbol = parts[1]
                    try:
                        data = await self.get_stock_data(symbol)
                        if data:
                            warm_data[asset_key] = data
                    except Exception as e:
                        logger.warning(f"Failed to warm cache for {asset_key}: {e}")
                elif asset_key.startswith('crypto_'):
                    coin_id = asset_key.split('_')[1]
                    try:
                        data = await self.get_crypto_data(coin_id)
                        if data:
                            warm_data[asset_key] = data
                    except Exception as e:
                        logger.warning(f"Failed to warm cache for {asset_key}: {e}")
            
            # Warm the cache
            warmed_count = await self.cache_service.warm_cache(warm_data)
            logger.info(f"Cache warming completed. Warmed {warmed_count} items.")
        except Exception as e:
            logger.error(f"Error during cache warming initialization: {e}")
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting with more conservative approach"""
        now = time.time()
        # Remove timestamps older than 1 minute
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            # Calculate sleep time to maintain rate limit with additional buffer
            oldest = min(self.request_timestamps)
            sleep_time = 70 - (now - oldest)  # Extra 10 seconds buffer
            if sleep_time > 0:
                logger.warning(f"Rate limit approaching, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
        
        # Add current timestamp
        self.request_timestamps.append(now)
    
    def _validate_data(self, data: Dict, required_fields: List[str]) -> bool:
        """Validate that data contains all required fields"""
        try:
            for field in required_fields:
                if field not in data or data[field] is None:
                    logger.warning(f"Missing required field '{field}' in data")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error validating data: {e}")
            return False
    
    @retry_on_failure(max_retries=5, delay=1, backoff_factor=2, exceptions=(DataFetchError, RateLimitError))
    async def get_stock_data(self, symbol: str, period: str = "1d", interval: str = "5m") -> Optional[Dict]:
        """Get stock data from Yahoo Finance with enhanced error handling and validation"""
        try:
            data = await self._fetch_from_yahoo_finance(symbol, period, interval)
            if data:
                # Validate the data
                required_fields = ["symbol", "current_price", "change_percent", "chart_data"]
                if self._validate_data(data, required_fields):
                    return data
                else:
                    logger.warning(f"Invalid data received for {symbol}, falling back to mock data")
                    raise DataValidationError(f"Invalid data structure for {symbol}")
            else:
                logger.warning(f"No data received for {symbol} from Yahoo Finance")
                raise DataFetchError(f"No data returned for {symbol}")
        except DataValidationError:
            # Fallback to mock data
            return await self._fetch_from_mock(symbol, "stock")
        except DataFetchError:
            # Fallback to mock data
            return await self._fetch_from_mock(symbol, "stock")
        except Exception as e:
            logger.error(f"Failed to fetch stock data for {symbol} from Yahoo Finance: {e}")
            # Fallback to mock data
            return await self._fetch_from_mock(symbol, "stock")
    
    async def _fetch_from_yahoo_finance(self, symbol: str, period: str = "1d", interval: str = "5m") -> Optional[Dict]:
        """Fetch data from Yahoo Finance with enhanced error handling and validation"""
        # Check cache first
        cache_key = f"stock_{symbol}_{period}_{interval}"
        cached_data = await self.cache_service.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {symbol}")
            return cached_data
        
        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            # Enforce rate limiting
            await self._check_rate_limit()
            
            loop = asyncio.get_event_loop()
            try:
                ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
                
                # Run history in executor to avoid blocking
                df = await loop.run_in_executor(None, ticker.history, period, interval)
                
                if df is None or df.empty:
                    logger.warning(f"No data returned for {symbol}")
                    return None
                
                # Validate that we have the required columns
                required_columns = ['Close', 'Open']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    logger.warning(f"Missing required columns {missing_columns} for {symbol}")
                    raise DataValidationError(f"Missing required columns: {missing_columns}")
                
                # Calculate additional metrics
                current_price = float(df['Close'].iloc[-1])
                open_price = float(df['Open'].iloc[0])
                change = current_price - open_price
                change_percent = (change / open_price) * 100 if open_price != 0 else 0
                
                # Limit chart data to last 100 points to reduce payload
                chart_data_limit = 100
                chart_data_full = []
                
                # Process data row by row with validation
                for idx, row in df.iterrows():
                    try:
                        chart_point = {
                            "time": str(idx),
                            "open": float(row['Open']) if 'Open' in df.columns and not pd.isna(row['Open']) else current_price,
                            "high": float(row['High']) if 'High' in df.columns and not pd.isna(row['High']) else current_price,
                            "low": float(row['Low']) if 'Low' in df.columns and not pd.isna(row['Low']) else current_price,
                            "close": float(row['Close']) if 'Close' in df.columns and not pd.isna(row['Close']) else current_price,
                            "volume": int(row['Volume']) if 'Volume' in df.columns and not pd.isna(row['Volume']) else 0
                        }
                        chart_data_full.append(chart_point)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping invalid data point for {symbol} at {idx}: {e}")
                        continue
                
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
                    "volume": int(df['Volume'].iloc[-1]) if 'Volume' in df.columns and not pd.isna(df['Volume'].iloc[-1]) else 0,
                    "open": open_price,
                    "high": float(df['High'].max()) if 'High' in df.columns and not pd.isna(df['High'].max()) else current_price,
                    "low": float(df['Low'].min()) if 'Low' in df.columns and not pd.isna(df['Low'].min()) else current_price,
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
            except DataValidationError:
                raise
            except Exception as e:
                logger.error(f"Error fetching data for {symbol} from Yahoo Finance: {e}")
                raise DataFetchError(f"Failed to fetch data for {symbol}: {str(e)}")
    
    @retry_on_failure(max_retries=5, delay=1, backoff_factor=2, exceptions=(DataFetchError, RateLimitError))
    async def get_crypto_data(self, coin_id: str) -> Optional[Dict]:
        """Get crypto data from CoinGecko with enhanced error handling and validation"""
        try:
            data = await self._fetch_from_coingecko(coin_id)
            if data:
                # Validate the data
                required_fields = ["symbol", "current_price", "change_percent", "chart_data"]
                if self._validate_data(data, required_fields):
                    return data
                else:
                    logger.warning(f"Invalid data received for {coin_id}, falling back to mock data")
                    raise DataValidationError(f"Invalid data structure for {coin_id}")
            else:
                logger.warning(f"No data received for {coin_id} from CoinGecko")
                raise DataFetchError(f"No data returned for {coin_id}")
        except DataValidationError:
            # Fallback to mock data
            return await self._fetch_from_mock(coin_id, "crypto")
        except DataFetchError:
            # Fallback to mock data
            return await self._fetch_from_mock(coin_id, "crypto")
        except Exception as e:
            logger.error(f"Failed to fetch crypto data for {coin_id} from CoinGecko: {e}")
            # Fallback to mock data
            return await self._fetch_from_mock(coin_id, "crypto")
    
    async def _fetch_from_coingecko(self, coin_id: str) -> Optional[Dict]:
        """Fetch data from CoinGecko with enhanced error handling and validation"""
        # Check cache first
        cache_key = f"crypto_{coin_id}"
        cached_data = await self.cache_service.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {coin_id}")
            return cached_data
        
        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            # Enforce rate limiting
            await self._check_rate_limit()
            
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
            try:
                response = await loop.run_in_executor(None, lambda: self.session.get(url, params=params, timeout=15))
                
                # Handle rate limiting
                if response.status_code == 429:
                    logger.warning(f"Rate limit exceeded for {coin_id}")
                    raise RateLimitError(f"Rate limit exceeded for {coin_id}")
                
                # Handle other HTTP errors
                if response.status_code != 200:
                    logger.warning(f"HTTP {response.status_code} error for {coin_id}: {response.text}")
                    raise DataFetchError(f"HTTP {response.status_code} error for {coin_id}")
                
                response.raise_for_status()
                price_data = response.json()
                
                if not price_data or coin_id not in price_data:
                    logger.warning(f"No price data returned for {coin_id}")
                    return None
                
                # Validate price data
                coin_data = price_data[coin_id]
                if "usd" not in coin_data:
                    logger.warning(f"Missing USD price data for {coin_id}")
                    raise DataValidationError(f"Missing USD price data for {coin_id}")
                
                # Historical data
                hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                hist_params = {"vs_currency": "usd", "days": "1", "interval": "hourly"}
                hist_response = await loop.run_in_executor(None, lambda: self.session.get(hist_url, params=hist_params, timeout=15))
                
                # Handle rate limiting for historical data
                if hist_response.status_code == 429:
                    logger.warning(f"Rate limit exceeded for {coin_id} historical data")
                    raise RateLimitError(f"Rate limit exceeded for {coin_id} historical data")
                
                # Handle other HTTP errors for historical data
                if hist_response.status_code != 200:
                    logger.warning(f"HTTP {hist_response.status_code} error for {coin_id} historical data: {hist_response.text}")
                    # Don't raise an error here, we can still return basic data
                
                current_price = coin_data["usd"]
                market_cap = coin_data.get("usd_market_cap", 0)
                
                chart_data = []
                if hist_response.status_code == 200:
                    try:
                        hist_response.raise_for_status()
                        hist_data = hist_response.json()
                        
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
                                if len(point) >= 2 and point[1] is not None
                            ]
                        else:
                            chart_data = [
                                {
                                    "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                                    "price": point[1]
                                }
                                for point in raw_chart_data
                                if len(point) >= 2 and point[1] is not None
                            ]
                    except Exception as e:
                        logger.warning(f"Error processing historical data for {coin_id}: {e}")
                        # Continue with empty chart data
                
                data = {
                    "symbol": coin_id.upper(),
                    "timestamp": datetime.now().isoformat(),
                    "current_price": current_price,
                    "change_percent": coin_data.get("usd_24h_change", 0),
                    "volume": coin_data.get("usd_24h_vol", 0),
                    "market_cap": market_cap,
                    "chart_data": chart_data
                }
                
                # Cache the data with adaptive TTL (crypto markets are 24/7)
                ttl = 30  # 30 seconds for crypto data
                
                await self.cache_service.set(cache_key, data, ttl=ttl)
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                return data
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout error fetching data for {coin_id} from CoinGecko: {e}")
                raise TimeoutError(f"Timeout error for {coin_id}: {str(e)}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error fetching data for {coin_id} from CoinGecko: {e}")
                raise NetworkError(f"Network error for {coin_id}: {str(e)}")
            except (DataValidationError, RateLimitError):
                raise
            except Exception as e:
                logger.error(f"Error fetching data for {coin_id} from CoinGecko: {e}")
                raise DataFetchError(f"Failed to fetch data for {coin_id}: {str(e)}")
    
    async def get_crypto_historical_data(self, coin_id: str, days: int = 30) -> Optional[Dict]:
        """Get historical crypto data from CoinGecko with enhanced error handling"""
        # Check cache first
        cache_key = f"crypto_hist_{coin_id}_{days}"
        cached_data = await self.cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            # Enforce rate limiting
            await self._check_rate_limit()
            
            try:
                # Historical data
                hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                hist_params = {"vs_currency": "usd", "days": str(days), "interval": "daily"}
                loop = asyncio.get_event_loop()
                hist_response = await loop.run_in_executor(None, lambda: self.session.get(hist_url, params=hist_params, timeout=15))
                
                # Handle rate limiting
                if hist_response.status_code == 429:
                    logger.warning(f"Rate limit exceeded for {coin_id} historical data")
                    raise RateLimitError(f"Rate limit exceeded for {coin_id} historical data")
                
                # Handle other HTTP errors
                if hist_response.status_code != 200:
                    logger.warning(f"HTTP {hist_response.status_code} error for {coin_id} historical data: {hist_response.text}")
                    raise DataFetchError(f"HTTP {hist_response.status_code} error for {coin_id} historical data")
                
                hist_response.raise_for_status()
                hist_data = hist_response.json()
                
                if not hist_data or not hist_data.get("prices"):
                    logger.warning(f"No historical data returned for {coin_id}")
                    raise DataFetchError(f"No historical data returned for {coin_id}")
                
                # Extract price data with limit
                chart_data_limit = 100
                raw_chart_data = hist_data.get("prices", [])
                chart_data = []
                
                if len(raw_chart_data) > chart_data_limit:
                    step = len(raw_chart_data) // chart_data_limit
                    chart_data = [
                        {
                            "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                            "price": point[1]
                        }
                        for point in raw_chart_data[::step][:chart_data_limit]
                        if len(point) >= 2 and point[1] is not None
                    ]
                else:
                    chart_data = [
                        {
                            "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                            "price": point[1]
                        }
                        for point in raw_chart_data
                        if len(point) >= 2 and point[1] is not None
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
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout error fetching historical data for {coin_id}: {e}")
                raise TimeoutError(f"Timeout error for {coin_id}: {str(e)}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error fetching historical data for {coin_id}: {e}")
                raise NetworkError(f"Network error for {coin_id}: {str(e)}")
            except (DataFetchError, RateLimitError):
                raise
            except Exception as e:
                logger.error(f"Error fetching historical data for {coin_id}: {e}")
                raise DataFetchError(f"Failed to fetch historical data for {coin_id}: {str(e)}")
    
    async def get_forex_data(self, pair: str) -> Optional[Dict]:
        """Get forex data with enhanced reliability"""
        # Check cache first
        cache_key = f"forex_{pair}"
        cached_data = await self.cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        # Use semaphore to limit concurrent requests
        async with self.semaphore:
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
                raise DataFetchError(f"Failed to fetch forex data for {pair}: {str(e)}")
    
    async def _fetch_from_mock(self, symbol: str, asset_type: str) -> Optional[Dict]:
        """Generate mock data for fallback with enhanced realism"""
        logger.info(f"Generating mock data for {symbol} ({asset_type})")
        
        # Base prices for consistency
        base_prices = {
            'AAPL': 175.50, 'GOOGL': 2750.00, 'MSFT': 330.00, 'TSLA': 250.00,
            'AMZN': 3200.00, 'META': 320.00, 'NVDA': 450.00, 'NFLX': 400.00,
            'bitcoin': 45000.00, 'ethereum': 3000.00, 'solana': 100.00,
            'GC=F': 1950.00, 'CL=F': 85.00, 'EURUSD': 1.08
        }
        
        base_price = base_prices.get(symbol, 100.0)
        
        # Generate random price movement with more realistic constraints
        change_percent = random.uniform(-3, 3)  # Reduced range for more realistic changes
        current_price = base_price * (1 + change_percent / 100)
        
        # Generate chart data (last 24 points)
        chart_data = []
        for i in range(24):
            time_point = (datetime.now() - timedelta(minutes=i*5)).isoformat()
            # Add some correlation between points for more realistic chart
            if i == 0:
                price_point = current_price
            else:
                # Small random movement from previous point
                prev_price = chart_data[-1]["price"]
                price_change = prev_price * random.uniform(-0.01, 0.01)  # ±1% change
                price_point = prev_price + price_change
            chart_data.append({
                "time": time_point,
                "price": round(price_point, 2)
            })
        
        # For stocks, generate OHLC data
        if asset_type == 'stock':
            chart_data = []
            for i in range(24):
                time_point = (datetime.now() - timedelta(minutes=i*5)).isoformat()
                # Generate realistic OHLC data
                if i == 0:
                    base = current_price
                else:
                    # Small random movement from previous close
                    prev_close = chart_data[-1]["close"]
                    base = prev_close * (1 + random.uniform(-0.005, 0.005))  # ±0.5% change
                
                open_price = base * (1 + random.uniform(-0.002, 0.002))  # ±0.2% from base
                high_price = max(open_price, base) * (1 + random.uniform(0, 0.005))  # Up to 0.5% higher
                low_price = min(open_price, base) * (1 - random.uniform(0, 0.005))  # Up to 0.5% lower
                close_price = base
                chart_data.append({
                    "time": time_point,
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2)
                })
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "current_price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
            "open": round(current_price * (1 - random.uniform(-0.5, 0.5) / 100), 2),
            "high": round(current_price * (1 + random.uniform(0, 1) / 100), 2),
            "low": round(current_price * (1 - random.uniform(0, 1) / 100), 2),
            "volume": random.randint(1000000, 100000000),
            "market_cap": random.randint(1000000000, 1000000000000) if asset_type == 'stock' else None,
            "chart_data": chart_data
        }
    
    async def get_multiple_assets(self, assets: List[Dict]) -> List[Dict]:
        """Fetch data for multiple assets concurrently with enhanced error handling and validation"""
        # Group assets by type for batch processing
        stock_assets = [asset for asset in assets if asset["type"] == "stock"]
        crypto_assets = [asset for asset in assets if asset["type"] == "crypto"]
        other_assets = [asset for asset in assets if asset["type"] not in ["stock", "crypto"]]
        
        results = []
        
        # Process stocks in smaller batches to avoid API limits
        batch_size = 3  # Reduced batch size for better reliability
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
            
            # Increased delay between batches to avoid rate limiting
            if i + batch_size < len(stock_assets):
                await asyncio.sleep(1.0)
        
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