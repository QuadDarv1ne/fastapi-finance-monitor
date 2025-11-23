"""Cache service for storing and retrieving financial data with enhanced performance

This module implements a dual-layer caching system that combines Redis and in-memory
caching to provide high-performance data storage and retrieval. It features automatic
compression for large data, partitioning for better organization, and comprehensive
statistics tracking.

The cache service implements a two-tier approach:
1. Redis cache (persistent, shared across instances)
2. Memory cache (fast, instance-local)

Key Features:
- Dual-layer caching (Redis + memory)
- Automatic data compression for large values
- Cache partitioning by data type
- TTL (Time To Live) management
- Statistics tracking (hits, misses, errors)
- Pre-warming for frequently accessed data

Classes:
    CacheService: Main cache service implementation
"""

import asyncio
import json
import logging
import time
import zlib
from typing import Any, TypeVar

# Import cache configuration
from app.config import CacheConfig

# Import custom exceptions
from app.exceptions.custom_exceptions import CacheError

# Import Redis cache service
from app.services.redis_cache_service import get_redis_cache_service

# Import types
from app.utils.types import CacheStats

logger = logging.getLogger(__name__)

# Generic type for cache values
T = TypeVar("T")


class CacheService:
    """Enhanced service for caching financial data to improve performance

    Implements a dual-layer caching system with Redis as the primary storage
    and in-memory cache as a fast secondary layer. Features include automatic
    compression, partitioning, and comprehensive statistics tracking.
    """

    def __init__(self, default_ttl: int | None = None):
        """
        Initialize cache service with enhanced performance features

        Sets up both Redis and memory cache layers, configures compression
        thresholds using centralized configuration.

        Args:
            default_ttl (int): Default time-to-live in seconds for cached items (uses CacheConfig.DEFAULT_TTL if None)
        """
        self.default_ttl = default_ttl or CacheConfig.DEFAULT_TTL
        self.memory_cache: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.redis_cache = get_redis_cache_service()
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.compression_threshold = CacheConfig.COMPRESSION_THRESHOLD
        # Pre-warmed cache for frequently accessed data
        self.pre_warmed = False

    def _compress_value(self, value: Any) -> bytes:
        """Compress value if it's large enough"""
        try:
            serialized = json.dumps(value, default=str)
            if len(serialized) > self.compression_threshold:
                return zlib.compress(serialized.encode("utf-8"))
            return serialized.encode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to compress value: {e}")
            return json.dumps(value, default=str).encode("utf-8")

    def _decompress_value(self, data: bytes | str) -> Any:
        """Decompress value if it's compressed"""
        try:
            if isinstance(data, bytes):
                # Try to decompress first
                try:
                    decompressed = zlib.decompress(data)
                    return json.loads(decompressed.decode("utf-8"))
                except zlib.error:
                    # Not compressed, treat as regular string
                    return json.loads(data.decode("utf-8"))
            else:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to decompress value: {e}")
            return data

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache (Redis first, then memory) with enhanced performance

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
                # Decompress if needed
                return self._decompress_value(redis_value)

            # Fall back to memory cache
            async with self.lock:
                if key in self.memory_cache:
                    item = self.memory_cache[key]
                    if time.time() < item["expires_at"]:
                        self.hits += 1
                        logger.debug(f"Memory cache hit for key: {key}")
                        return item["value"]
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
                        if time.time() < item["expires_at"]:
                            return item["value"]
            except Exception as fallback_error:
                logger.error(f"Error in cache fallback for key {key}: {fallback_error}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set value in cache (both Redis and memory) with enhanced performance

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if successful (at least one cache layer succeeded), False otherwise
        """
        ttl_to_use = ttl or self.default_ttl
        redis_success = False
        memory_success = False

        # Compress large values
        compressed_value = self._compress_value(value)

        try:
            # Set in Redis with compression
            redis_success = await self.redis_cache.set(key, compressed_value, ttl_to_use)
            if redis_success:
                logger.debug(f"Set Redis cache for key: {key} with TTL: {ttl_to_use}")
        except Exception as e:
            self.errors += 1
            logger.error(f"Error setting Redis cache key {key}: {e}")

        try:
            # Set in memory cache
            async with self.lock:
                expires_at = time.time() + ttl_to_use
                self.memory_cache[key] = {
                    "value": value,  # Store original value in memory
                    "expires_at": expires_at,
                    "created_at": time.time(),
                    "size": len(compressed_value),
                }
                memory_success = True
                logger.debug(
                    f"Set memory cache for key: {key} with TTL: {ttl_to_use}, Size: {len(compressed_value)} bytes"
                )
        except Exception as e:
            self.errors += 1
            logger.error(f"Error setting memory cache key {key}: {e}")

        # Return True if at least one cache layer succeeded
        return redis_success or memory_success

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
            removed_count = 0
            current_time = time.time()

            async with self.lock:
                expired_keys = [
                    key
                    for key, item in self.memory_cache.items()
                    if current_time >= item["expires_at"]
                ]

                for key in expired_keys:
                    del self.memory_cache[key]
                    removed_count += 1

            if removed_count > 0:
                logger.debug(f"Cleaned up {removed_count} expired memory cache items")

            return removed_count
        except Exception as e:
            self.errors += 1
            logger.error(f"Error cleaning up memory cache: {e}")
            return 0

    async def warm_cache(self, key_patterns: dict[str, Any]) -> int:
        """
        Proactively warm cache with frequently accessed data

        Args:
            key_patterns: Dictionary of key patterns and their data

        Returns:
            Number of items warmed
        """
        warmed_count = 0
        try:
            for key, data in key_patterns.items():
                # Set with longer TTL for warmed cache items
                ttl = self.default_ttl * 3  # 3x default TTL for warmed items
                if await self.set(key, data, ttl=ttl):
                    warmed_count += 1
                    logger.debug(f"Warmed cache for key: {key}")

            logger.info(f"Cache warming completed. Warmed {warmed_count} items.")
            return warmed_count
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            raise CacheError(f"Failed to warm cache: {e!s}")

    async def get_stats(self) -> CacheStats:
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
            current_time = time.time()

            async with self.lock:
                total_items = len(self.memory_cache)
                expired_items = sum(
                    1 for item in self.memory_cache.values() if current_time >= item["expires_at"]
                )
                active_items = total_items - expired_items
                memory_usage = sum(item.get("size", 0) for item in self.memory_cache.values())

            # Calculate hit ratio
            total_requests = self.hits + self.misses
            hit_ratio = self.hits / total_requests if total_requests > 0 else 0

            return {
                "memory_total_items": total_items,
                "memory_expired_items": expired_items,
                "memory_active_items": active_items,
                "memory_usage_bytes": memory_usage,
                "hits": self.hits,
                "misses": self.misses,
                "errors": self.errors,
                "hit_ratio": round(hit_ratio, 4),
                "redis_stats": redis_stats,
            }
        except Exception as e:
            self.errors += 1
            logger.error(f"Error getting cache stats: {e}")
            raise CacheError(f"Failed to get cache statistics: {e!s}")


# Global cache service instance
cache_service = CacheService()


def get_cache_service() -> CacheService:
    """Get global cache service instance"""
    return cache_service
