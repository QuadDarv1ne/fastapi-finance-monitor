"""Cache service for storing and retrieving financial data"""

import asyncio
import time
from typing import Any, Optional, Dict
import logging

# Import Redis cache service
from app.services.redis_cache_service import get_redis_cache_service

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching financial data to improve performance"""
    
    def __init__(self, default_ttl: int = 60):
        """
        Initialize cache service
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.default_ttl = default_ttl
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.redis_cache = get_redis_cache_service()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (Redis first, then memory)
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        # Try Redis first
        redis_value = await self.redis_cache.get(key)
        if redis_value is not None:
            logger.debug(f"Redis cache hit for key: {key}")
            return redis_value
        
        # Fall back to memory cache
        async with self.lock:
            if key in self.memory_cache:
                item = self.memory_cache[key]
                if time.time() < item['expires_at']:
                    logger.debug(f"Memory cache hit for key: {key}")
                    return item['value']
                else:
                    # Remove expired item
                    del self.memory_cache[key]
                    logger.debug(f"Memory cache miss (expired) for key: {key}")
            else:
                logger.debug(f"Memory cache miss for key: {key}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache (both Redis and memory)
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl_to_use = ttl or self.default_ttl
        
        # Set in Redis
        await self.redis_cache.set(key, value, ttl_to_use)
        
        # Set in memory cache
        async with self.lock:
            expires_at = time.time() + ttl_to_use
            self.memory_cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
            logger.debug(f"Set cache for key: {key} with TTL: {ttl_to_use}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if item was deleted, False if not found
        """
        # Delete from Redis
        redis_result = await self.redis_cache.delete(key)
        
        # Delete from memory cache
        async with self.lock:
            if key in self.memory_cache:
                del self.memory_cache[key]
                logger.debug(f"Deleted memory cache for key: {key}")
                return True
            return redis_result
    
    async def clear(self) -> None:
        """Clear all cache"""
        # Clear Redis cache (pattern matching all keys)
        await self.redis_cache.clear_pattern("*")
        
        # Clear memory cache
        async with self.lock:
            self.memory_cache.clear()
            logger.debug("Cleared all cache")
    
    async def cleanup(self) -> int:
        """
        Remove expired items from memory cache
        
        Returns:
            Number of items removed
        """
        async with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, item in self.memory_cache.items()
                if current_time >= item['expires_at']
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired memory cache items")
            
            return len(expired_keys)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        # Get Redis stats
        redis_stats = await self.redis_cache.get_stats()
        
        # Get memory cache stats
        async with self.lock:
            current_time = time.time()
            total_items = len(self.memory_cache)
            expired_items = sum(
                1 for item in self.memory_cache.values()
                if current_time >= item['expires_at']
            )
            
            return {
                'memory_total_items': total_items,
                'memory_expired_items': expired_items,
                'memory_active_items': total_items - expired_items,
                'redis_stats': redis_stats
            }


# Global cache service instance
cache_service = CacheService()


def get_cache_service() -> CacheService:
    """Get global cache service instance"""
    return cache_service