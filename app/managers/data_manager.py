"""Data manager for handling asset data retrieval and caching"""

from typing import Dict, List, Optional, Any, Union
import logging
from datetime import datetime, timedelta
import asyncio
import random
import yfinance as yf

from app.services.lru_cache import LRUCache
from app.services.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)

# Expanded list of financial instruments
FINANCIAL_INSTRUMENTS = {
    # Stocks - US Companies
    'AAPL': {'name': 'Apple Inc.', 'type': 'stock'},
    'GOOGL': {'name': 'Alphabet Inc.', 'type': 'stock'},
    'MSFT': {'name': 'Microsoft Corp.', 'type': 'stock'},
    'TSLA': {'name': 'Tesla Inc.', 'type': 'stock'},
    'AMZN': {'name': 'Amazon.com Inc.', 'type': 'stock'},
    'META': {'name': 'Meta Platforms Inc.', 'type': 'stock'},
    'NVDA': {'name': 'NVIDIA Corp.', 'type': 'stock'},
    'NFLX': {'name': 'Netflix Inc.', 'type': 'stock'},
    'bitcoin': {'name': 'Bitcoin', 'type': 'crypto'},
    'ethereum': {'name': 'Ethereum', 'type': 'crypto'},
    'solana': {'name': 'Solana', 'type': 'crypto'},
    'GC=F': {'name': 'Gold Futures', 'type': 'commodity'},
    'CL=F': {'name': 'Crude Oil Futures', 'type': 'commodity'},
    'EURUSD': {'name': 'Euro/US Dollar', 'type': 'forex'},
}

class DataManager:
    """Управление получением и кэшированием данных"""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize data manager
        
        Args:
            metrics_collector: Metrics collector instance (optional)
        """
        self.cache = LRUCache(max_size=2000)  # Increased cache size for better hit ratio
        if metrics_collector is None:
            from app.services.metrics_collector import MetricsCollector
            metrics_collector = MetricsCollector.get_instance()
        self.metrics = metrics_collector
        # Semaphore to limit concurrent data fetches
        self.data_semaphore = asyncio.Semaphore(100)  # Increased from 20 to 100 for better throughput
    
    async def get_asset_data(self, symbol: str) -> Optional[Dict]:
        """
        Get data for a single asset with caching
        
        Args:
            symbol: Asset symbol
            
        Returns:
            Asset data dictionary or None if error
        """
        try:
            # Try to get from cache first
            cached_data = self.cache.get(symbol)
            if cached_data:
                if self.metrics:
                    self.metrics.record_cache_hit()
                return cached_data
            
            if self.metrics:
                self.metrics.record_cache_miss()
            
            # Get instrument info
            if symbol in FINANCIAL_INSTRUMENTS:
                instrument_info = FINANCIAL_INSTRUMENTS[symbol]
            else:
                instrument_info = {'name': symbol, 'type': 'asset'}
            
            # Generate mock data for demonstration
            asset_data = self._generate_mock_asset_data(symbol, instrument_info)
            
            # Cache the data
            self.cache.set(symbol, asset_data)
            return asset_data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    async def get_assets_data(self, symbols: List[str]) -> List[Dict]:
        """
        Get data for multiple assets with semaphore for concurrency control
        
        Args:
            symbols: List of asset symbols
            
        Returns:
            List of asset data dictionaries
        """
        assets_data = []
        
        # Use semaphore to limit concurrent data fetches
        async with self.data_semaphore:
            # Process symbols in optimized batches to improve throughput
            batch_size = 20  # Increased from 5 to 20 for better throughput
            # Reduce delay between batches for better performance
            batch_delay = 0.01  # Reduced from 0.1 to 0.01
            
            # Process all batches concurrently for better performance
            batch_tasks = []
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                task = self._get_batch_data(batch)
                batch_tasks.append(task)
            
            # Gather all batch results concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(batch_results):
                try:
                    if isinstance(result, Exception):
                        logger.error(f"Error processing batch {i + 1}: {result}")
                        continue
                    elif result is not None and not isinstance(result, BaseException):
                        assets_data.extend(result)
                except Exception as e:
                    logger.error(f"Error processing batch result {i + 1}: {e}")
                    continue
        
        return assets_data
    
    async def _get_batch_data(self, symbols: List[str]) -> List[Dict]:
        """
        Get data for a batch of symbols
        
        Args:
            symbols: List of asset symbols
            
        Returns:
            List of asset data dictionaries
        """
        batch_data = []
        
        # Create tasks for concurrent fetching
        tasks = []
        for symbol in symbols:
            task = self.get_asset_data(symbol)
            tasks.append(task)
        
        # Gather results with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            try:
                if isinstance(result, Exception):
                    logger.error(f"Error fetching data for {symbols[i]}: {result}")
                    # Add error data to maintain structure
                    batch_data.append({
                        "symbol": symbols[i],
                        "name": symbols[i],
                        "type": "error",
                        "error": str(result)
                    })
                elif result is not None and not isinstance(result, BaseException):
                    batch_data.append(result)
            except Exception as e:
                logger.error(f"Error processing result for {symbols[i]}: {e}")
        
        return batch_data
    
    def _generate_mock_asset_data(self, symbol: str, instrument_info: Dict) -> Dict:
        """
        Generate mock asset data for demonstration
        
        Args:
            symbol: Asset symbol
            instrument_info: Instrument information
            
        Returns:
            Asset data dictionary
        """
        # Base price based on symbol (for consistency)
        base_prices = {
            'AAPL': 175.50, 'GOOGL': 2750.00, 'MSFT': 330.00, 'TSLA': 250.00,
            'AMZN': 3200.00, 'META': 320.00, 'NVDA': 450.00, 'NFLX': 400.00,
            'bitcoin': 45000.00, 'ethereum': 3000.00, 'solana': 100.00,
            'GC=F': 1950.00, 'CL=F': 85.00, 'EURUSD': 1.08
        }
        
        base_price = base_prices.get(symbol, 100.0)
        
        # Generate random price movement
        change_percent = random.uniform(-5, 5)
        current_price = base_price * (1 + change_percent / 100)
        
        # Generate chart data (last 24 points)
        chart_data = []
        for i in range(24):
            time_point = (datetime.now() - timedelta(minutes=i*5)).isoformat()
            price_point = current_price * (1 + random.uniform(-0.5, 0.5) / 100)
            chart_data.append({
                "time": time_point,
                "price": round(price_point, 2)
            })
        
        # For stocks, generate OHLC data
        if instrument_info['type'] == 'stock':
            chart_data = []
            for i in range(24):
                time_point = (datetime.now() - timedelta(minutes=i*5)).isoformat()
                base = current_price * (1 + random.uniform(-1, 1) / 100)
                open_price = base * (1 + random.uniform(-0.2, 0.2) / 100)
                high_price = max(open_price, base) * (1 + random.uniform(0, 0.5) / 100)
                low_price = min(open_price, base) * (1 - random.uniform(0, 0.5) / 100)
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
            "name": instrument_info['name'],
            "type": instrument_info['type'],
            "current_price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
            "open": round(current_price * (1 - random.uniform(-1, 1) / 100), 2),
            "high": round(current_price * (1 + random.uniform(0, 2) / 100), 2),
            "low": round(current_price * (1 - random.uniform(0, 2) / 100), 2),
            "volume": random.randint(1000000, 100000000),
            "market_cap": random.randint(1000000000, 1000000000000) if instrument_info['type'] == 'stock' else None,
            "chart_data": chart_data
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache.get_stats()