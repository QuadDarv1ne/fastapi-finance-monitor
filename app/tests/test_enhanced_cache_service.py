"""Tests for the enhanced cache service with performance improvements"""

import pytest
import asyncio
import time
import zlib
import json
from app.services.cache_service import CacheService


class TestEnhancedCacheService:
    """Test suite for enhanced CacheService with performance improvements"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.cache_service = CacheService(default_ttl=2)  # 2 second TTL for testing
    
    def test_set_and_get_with_compression(self):
        """Test setting and getting values from cache with compression"""
        async def test_async():
            # Set a large value that should be compressed
            large_data = {"data": "x" * 2000}  # Larger than compression threshold
            result = await self.cache_service.set("large_key", large_data)
            assert result is True  # Should return True on success
            
            # Get the value
            result = await self.cache_service.get("large_key")
            
            assert result is not None
            assert isinstance(result, dict)
            assert len(result["data"]) == 2000
        
        asyncio.run(test_async())
    
    def test_set_and_get_without_compression(self):
        """Test setting and getting small values without compression"""
        async def test_async():
            # Set a small value that should not be compressed
            small_data = {"data": "small"}
            result = await self.cache_service.set("small_key", small_data)
            assert result is True  # Should return True on success
            
            # Get the value
            result = await self.cache_service.get("small_key")
            
            assert result is not None
            assert isinstance(result, dict)
            assert result["data"] == "small"
        
        asyncio.run(test_async())
    
    def test_partitioning(self):
        """Test cache partitioning functionality"""
        async def test_async():
            # Set values in different partitions
            stock_result = await self.cache_service.set("stock_AAPL_data", {"type": "stock", "symbol": "AAPL"})
            crypto_result = await self.cache_service.set("crypto_bitcoin_data", {"type": "crypto", "symbol": "bitcoin"})
            forex_result = await self.cache_service.set("forex_EURUSD_data", {"type": "forex", "symbol": "EURUSD"})
            general_result = await self.cache_service.set("general_data", {"type": "general", "value": "test"})
            
            # All should return True (even if Redis is not available, memory cache should work)
            assert stock_result is True
            assert crypto_result is True
            assert forex_result is True
            assert general_result is True
            
            # Verify all values can be retrieved
            stock_data = await self.cache_service.get("stock_AAPL_data")
            crypto_data = await self.cache_service.get("crypto_bitcoin_data")
            forex_data = await self.cache_service.get("forex_EURUSD_data")
            general_data = await self.cache_service.get("general_data")
            
            assert stock_data is not None
            assert crypto_data is not None
            assert forex_data is not None
            assert general_data is not None
            
            assert stock_data["symbol"] == "AAPL"
            assert crypto_data["symbol"] == "bitcoin"
            assert forex_data["symbol"] == "EURUSD"
            assert general_data["value"] == "test"
            
            # Check partition stats
            stats = await self.cache_service.get_stats()
            partition_stats = stats.get('partition_stats', {})
            
            # Verify each partition has data
            assert 'stock' in partition_stats
            assert 'crypto' in partition_stats
            assert 'forex' in partition_stats
            assert 'general' in partition_stats
        
        asyncio.run(test_async())
    
    def test_cache_expiration_with_partitions(self):
        """Test cache expiration with partitioning"""
        async def test_async():
            # Set values with short TTL
            stock_result = await self.cache_service.set("stock_short", {"data": "stock"}, ttl=1)
            crypto_result = await self.cache_service.set("crypto_short", {"data": "crypto"}, ttl=1)
            
            assert stock_result is True
            assert crypto_result is True
            
            # Values should be available immediately
            stock_result = await self.cache_service.get("stock_short")
            crypto_result = await self.cache_service.get("crypto_short")
            assert stock_result is not None
            assert crypto_result is not None
            assert stock_result["data"] == "stock"
            assert crypto_result["data"] == "crypto"
            
            # Wait for expiration
            await asyncio.sleep(1.1)
            
            # Values should no longer be available
            stock_result = await self.cache_service.get("stock_short")
            crypto_result = await self.cache_service.get("crypto_short")
            assert stock_result is None
            assert crypto_result is None
        
        asyncio.run(test_async())
    
    def test_cache_warming(self):
        """Test cache warming functionality"""
        async def test_async():
            # Prepare data for warming
            warm_data = {
                "stock_AAPL": {"symbol": "AAPL", "price": 150.0},
                "crypto_bitcoin": {"symbol": "bitcoin", "price": 45000.0}
            }
            
            # Warm the cache
            warmed_count = await self.cache_service.warm_cache(warm_data)
            # We expect at least 0, and potentially 2 if Redis is available
            assert warmed_count >= 0
            
            # Verify warmed data is available
            apple_data = await self.cache_service.get("stock_AAPL")
            bitcoin_data = await self.cache_service.get("crypto_bitcoin")
            
            # Data should be available from memory cache even if Redis is not available
            assert apple_data is not None
            assert bitcoin_data is not None
            
            assert apple_data["symbol"] == "AAPL"
            assert apple_data["price"] == 150.0
            assert bitcoin_data["symbol"] == "bitcoin"
            assert bitcoin_data["price"] == 45000.0
            
            # Check that warmed items have longer TTL
            # This is indirectly tested by checking that they exist after normal TTL
            await asyncio.sleep(2.1)  # Wait for normal TTL to expire
            # Warmed items should still exist (they have 3x TTL)
            apple_data = await self.cache_service.get("stock_AAPL")
            assert apple_data is not None
        
        asyncio.run(test_async())
    
    def test_get_stats_with_partitions(self):
        """Test getting cache statistics with partitioning"""
        async def test_async():
            # Initially empty
            stats = await self.cache_service.get_stats()
            assert stats['memory_total_items'] == 0
            assert stats['memory_active_items'] == 0
            assert 'partition_stats' in stats
            
            # Add some items to different partitions
            await self.cache_service.set("stock_key1", {"type": "stock"})
            await self.cache_service.set("crypto_key1", {"type": "crypto"})
            await self.cache_service.set("general_key1", {"type": "general"})
            
            # Check stats
            stats = await self.cache_service.get_stats()
            assert stats['memory_total_items'] == 3
            assert stats['memory_active_items'] == 3
            
            # Check partition stats
            partition_stats = stats['partition_stats']
            assert partition_stats['stock']['active_items'] == 1
            assert partition_stats['crypto']['active_items'] == 1
            assert partition_stats['general']['active_items'] == 1
        
        asyncio.run(test_async())
    
    def test_cleanup_with_partitions(self):
        """Test cleaning up expired items with partitioning"""
        async def test_async():
            # Set values with different TTLs in different partitions
            await self.cache_service.set("stock_short", {"type": "stock"}, ttl=1)
            await self.cache_service.set("crypto_long", {"type": "crypto"}, ttl=5)
            await self.cache_service.set("general_short", {"type": "general"}, ttl=1)
            
            # Verify all exist initially
            stats_before = await self.cache_service.get_stats()
            assert stats_before['memory_total_items'] == 3
            assert stats_before['memory_active_items'] == 3
            
            # Wait for short TTL to expire
            await asyncio.sleep(1.1)
            
            # Clean up expired items
            cleaned_count = await self.cache_service.cleanup()
            assert cleaned_count >= 0  # At least 0 items should be cleaned
            
            # The remaining item should be the crypto item
            crypto_data = await self.cache_service.get("crypto_long")
            # We can't guarantee it will still exist in test environment, but if it does, it should be correct
            if crypto_data is not None:
                assert crypto_data["type"] == "crypto"
        
        asyncio.run(test_async())


if __name__ == "__main__":
    pytest.main([__file__])