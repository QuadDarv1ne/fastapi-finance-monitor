"""Tests for the cache manager service"""

import pytest
import time
from app.services.cache_manager import CacheManager


class TestCacheManager:
    """Test suite for CacheManager"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.cache_manager = CacheManager(ttl_seconds=1)  # Short TTL for testing
    
    def test_cache_manager_initialization(self):
        """Test CacheManager initialization"""
        assert isinstance(self.cache_manager.cache, dict)
        assert self.cache_manager.ttl == 1
    
    def test_set_and_get(self):
        """Test setting and getting values from cache"""
        key = "test_key"
        value = "test_value"
        
        # Set a value
        self.cache_manager.set(key, value)
        
        # Get the value
        result = self.cache_manager.get(key)
        assert result == value
    
    def test_get_nonexistent_key(self):
        """Test getting a non-existent key"""
        result = self.cache_manager.get("nonexistent_key")
        assert result is None
    
    def test_cache_expiration(self):
        """Test cache expiration"""
        key = "expiring_key"
        value = "expiring_value"
        
        # Set a value with short TTL
        self.cache_manager.set(key, value)
        
        # Value should be available immediately
        result = self.cache_manager.get(key)
        assert result == value
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Value should no longer be available
        result = self.cache_manager.get(key)
        assert result is None
    
    def test_cache_invalidation(self):
        """Test manual cache invalidation"""
        key1 = "key1"
        key2 = "key2"
        value1 = "value1"
        value2 = "value2"
        
        # Set multiple values
        self.cache_manager.set(key1, value1)
        self.cache_manager.set(key2, value2)
        
        # Verify they exist
        assert self.cache_manager.get(key1) == value1
        assert self.cache_manager.get(key2) == value2
        
        # Invalidate old cache entries
        self.cache_manager.invalidate_old()
        
        # With short TTL and no wait, entries might still be valid
        # But after waiting, they should be invalidated
        time.sleep(1.1)
        self.cache_manager.invalidate_old()
        
        # Verify they are gone
        assert self.cache_manager.get(key1) is None
        assert self.cache_manager.get(key2) is None
    
    def test_clear_cache(self):
        """Test clearing all cache"""
        key1 = "key1"
        key2 = "key2"
        value1 = "value1"
        value2 = "value2"
        
        # Set multiple values
        self.cache_manager.set(key1, value1)
        self.cache_manager.set(key2, value2)
        
        # Verify they exist
        assert self.cache_manager.get(key1) == value1
        assert self.cache_manager.get(key2) == value2
        
        # Clear cache
        self.cache_manager.clear()
        
        # Verify all are gone
        assert self.cache_manager.get(key1) is None
        assert self.cache_manager.get(key2) is None
    
    def test_get_stats(self):
        """Test getting cache statistics"""
        # Initially empty
        stats = self.cache_manager.get_stats()
        assert stats["total_items"] == 0
        assert stats["ttl_seconds"] == 1
        
        # Add some items
        self.cache_manager.set("key1", "value1")
        self.cache_manager.set("key2", "value2")
        
        # Check stats
        stats = self.cache_manager.get_stats()
        assert stats["total_items"] == 2
        assert stats["ttl_seconds"] == 1


if __name__ == "__main__":
    pytest.main([__file__])