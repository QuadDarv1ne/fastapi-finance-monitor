"""Cache service for storing and retrieving financial data"""

import asyncio
import time
from typing import Any, Optional, Dict
import logging
import json
from datetime import datetime

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
        self.hits = 0
        self.misses = 0
        self.errors = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (Redis first, then memory)
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        try:
            # Try Redis first
            redis_value = await self.redis_cache.get(key)
            if redis_value is not None:
                self.hits += 1
                logger.debug(f"Redis cache hit for key: {key}")
                return redis_value
            
            # Fall back to memory cache
            async with self.lock:
                if key in self.memory_cache:
                    item = self.memory_cache[key]
                    if time.time() < item['expires_at']:
                        self.hits += 1
                        logger.debug(f"Memory cache hit for key: {key}")
                        return item['value']
                    else:
                        # Remove expired item
                        del self.memory_cache[key]
                        logger.debug(f"Memory cache miss (expired) for key: {key}")
                else:
                    logger.debug(f"Memory cache miss for key: {key}")
                
                self.misses += 1
                return None
        except Exception as e:
            self.errors += 1
            logger.error(f"Error getting cache key {key}: {e}")
            # Try to get from memory cache as fallback
            try:
                async with self.lock:
                    if key in self.memory_cache:
                        item = self.memory_cache[key]
                        if time.time() < item['expires_at']:
                            return item['value']
            except Exception as fallback_error:
                logger.error(f"Error in cache fallback for key {key}: {fallback_error}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache (both Redis and memory)
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        ttl_to_use = ttl or self.default_ttl
        success = True
        
        try:
            # Set in Redis
            redis_success = await self.redis_cache.set(key, value, ttl_to_use)
            if not redis_success:
                success = False
        except Exception as e:
            self.errors += 1
            logger.error(f"Error setting Redis cache key {key}: {e}")
            success = False
        
        try:
            # Set in memory cache
            async with self.lock:
                expires_at = time.time() + ttl_to_use
                self.memory_cache[key] = {
                    'value': value,
                    'expires_at': expires_at,
                    'created_at': time.time()
                }
                logger.debug(f"Set cache for key: {key} with TTL: {ttl_to_use}")
        except Exception as e:
            self.errors += 1
            logger.error(f"Error setting memory cache key {key}: {e}")
            success = False
            
        return success
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if item was deleted, False if not found
        """
        redis_result = False
        memory_result = False
        
        try:
            # Delete from Redis
            redis_result = await self.redis_cache.delete(key)
        except Exception as e:
            self.errors += 1
            logger.error(f"Error deleting Redis cache key {key}: {e}")
        
        try:
            # Delete from memory cache
            async with self.lock:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    logger.debug(f"Deleted memory cache for key: {key}")
                    memory_result = True
        except Exception as e:
            self.errors += 1
            logger.error(f"Error deleting memory cache key {key}: {e}")
            
        return redis_result or memory_result
    
    async def clear(self) -> None:
        """Clear all cache"""
        try:
            # Clear Redis cache (pattern matching all keys)
            await self.redis_cache.clear_pattern("*")
        except Exception as e:
            self.errors += 1
            logger.error(f"Error clearing Redis cache: {e}")
        
        try:
            # Clear memory cache
            async with self.lock:
                self.memory_cache.clear()
                logger.debug("Cleared all memory cache")
        except Exception as e:
            self.errors += 1
            logger.error(f"Error clearing memory cache: {e}")
            
        logger.debug("Cleared all cache")
    
    async def cleanup(self) -> int:
        """
        Remove expired items from memory cache
        
        Returns:
            Number of items removed
        """
        try:
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
        except Exception as e:
            self.errors += 1
            logger.error(f"Error cleaning up memory cache: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            # Get Redis stats
            redis_stats = await self.redis_cache.get_stats()
        except Exception as e:
            self.errors += 1
            logger.error(f"Error getting Redis stats: {e}")
            redis_stats = {}
        
        try:
            # Get memory cache stats
            async with self.lock:
                current_time = time.time()
                total_items = len(self.memory_cache)
                expired_items = sum(
                    1 for item in self.memory_cache.values()
                    if current_time >= item['expires_at']
                )
                
                # Calculate hit ratio
                total_requests = self.hits + self.misses
                hit_ratio = self.hits / total_requests if total_requests > 0 else 0
                
                # Calculate memory usage
                memory_usage = sum(
                    len(json.dumps(item.get('value', ''), default=str)) 
                    for item in self.memory_cache.values()
                )
                
                return {
                    'memory_total_items': total_items,
                    'memory_expired_items': expired_items,
                    'memory_active_items': total_items - expired_items,
                    'memory_usage_bytes': memory_usage,
                    'hits': self.hits,
                    'misses': self.misses,
                    'errors': self.errors,
                    'hit_ratio': round(hit_ratio, 4),
                    'redis_stats': redis_stats
                }
        except Exception as e:
            self.errors += 1
            logger.error(f"Error getting cache stats: {e}")
            return {
                'memory_total_items': 0,
                'memory_expired_items': 0,
                'memory_active_items': 0,
                'memory_usage_bytes': 0,
                'hits': self.hits,
                'misses': self.misses,
                'errors': self.errors,
                'hit_ratio': 0,
                'redis_stats': redis_stats
            }

# Global cache service instance
cache_service = CacheService()

def get_cache_service() -> CacheService:
    """Get global cache service instance"""
    return cache_service