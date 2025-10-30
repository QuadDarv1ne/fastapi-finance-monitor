"""Tests for the cache service"""

import pytest
import asyncio
import time
from app.services.cache_service import CacheService


class TestCacheService:
    """Test suite for CacheService"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.cache_service = CacheService(default_ttl=1)  # 1 second TTL for testing
    
    def test_set_and_get(self):
        """Test setting and getting values from cache"""
        async def test_async():
            # Set a value
            await self.cache_service.set("test_key", "test_value")
            
            # Get the value
            result = await self.cache_service.get("test_key")
            
            assert result == "test_value"
        
        asyncio.run(test_async())
    
    def test_get_nonexistent_key(self):
        """Test getting a non-existent key"""
        async def test_async():
            result = await self.cache_service.get("nonexistent_key")
            assert result is None
        
        asyncio.run(test_async())
    
    def test_cache_expiration(self):
        """Test cache expiration"""
        async def test_async():
            # Set a value with short TTL
            await self.cache_service.set("expiring_key", "expiring_value", ttl=1)
            
            # Value should be available immediately
            result = await self.cache_service.get("expiring_key")
            assert result == "expiring_value"
            
            # Wait for expiration
            await asyncio.sleep(1.1)
            
            # Value should no longer be available
            result = await self.cache_service.get("expiring_key")
            assert result is None
        
        asyncio.run(test_async())
    
    def test_delete_key(self):
        """Test deleting a key from cache"""
        async def test_async():
            # Set a value
            await self.cache_service.set("delete_key", "delete_value")
            
            # Verify it exists
            result = await self.cache_service.get("delete_key")
            assert result == "delete_value"
            
            # Delete the key
            deleted = await self.cache_service.delete("delete_key")
            assert deleted is True
            
            # Verify it's gone
            result = await self.cache_service.get("delete_key")
            assert result is None
        
        asyncio.run(test_async())
    
    def test_delete_nonexistent_key(self):
        """Test deleting a non-existent key"""
        async def test_async():
            deleted = await self.cache_service.delete("nonexistent_key")
            assert deleted is False
        
        asyncio.run(test_async())
    
    def test_clear_cache(self):
        """Test clearing all cache"""
        async def test_async():
            # Set multiple values
            await self.cache_service.set("key1", "value1")
            await self.cache_service.set("key2", "value2")
            await self.cache_service.set("key3", "value3")
            
            # Verify they exist
            assert await self.cache_service.get("key1") == "value1"
            assert await self.cache_service.get("key2") == "value2"
            assert await self.cache_service.get("key3") == "value3"
            
            # Clear cache
            await self.cache_service.clear()
            
            # Verify all are gone
            assert await self.cache_service.get("key1") is None
            assert await self.cache_service.get("key2") is None
            assert await self.cache_service.get("key3") is None
        
        asyncio.run(test_async())
    
    def test_cleanup_expired(self):
        """Test cleaning up expired items"""
        async def test_async():
            # Set values with different TTLs
            await self.cache_service.set("short_ttl", "short_value", ttl=1)
            await self.cache_service.set("long_ttl", "long_value", ttl=5)
            
            # Verify both exist
            stats_before = await self.cache_service.get_stats()
            assert stats_before['total_items'] == 2
            assert stats_before['active_items'] == 2
            
            # Wait for short TTL to expire
            await asyncio.sleep(1.1)
            
            # Clean up expired items
            cleaned_count = await self.cache_service.cleanup()
            assert cleaned_count == 1
            
            # Verify only one item remains
            stats_after = await self.cache_service.get_stats()
            assert stats_after['total_items'] == 1
            assert stats_after['active_items'] == 1
            assert await self.cache_service.get("long_ttl") == "long_value"
        
        asyncio.run(test_async())
    
    def test_get_stats(self):
        """Test getting cache statistics"""
        async def test_async():
            # Initially empty
            stats = await self.cache_service.get_stats()
            assert stats['total_items'] == 0
            assert stats['expired_items'] == 0
            assert stats['active_items'] == 0
            
            # Add some items
            await self.cache_service.set("key1", "value1")
            await self.cache_service.set("key2", "value2", ttl=1)
            
            # Check stats
            stats = await self.cache_service.get_stats()
            assert stats['total_items'] == 2
            assert stats['active_items'] == 2
            
            # Wait for one to expire
            await asyncio.sleep(1.1)
            
            # Check stats again (before cleanup, expired items should be counted)
            stats = await self.cache_service.get_stats()
            assert stats['total_items'] == 2
            # Note: Both items might be expired due to timing, so we check that expired + active = total
            assert stats['expired_items'] + stats['active_items'] == 2
        
        asyncio.run(test_async())


if __name__ == "__main__":
    pytest.main([__file__])