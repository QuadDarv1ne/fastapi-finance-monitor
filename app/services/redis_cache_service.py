"""Redis cache service for storing and retrieving financial data with enhanced performance"""

import asyncio
import json
import logging
import zlib
from typing import Any, Optional, Dict, Union, Awaitable
from redis import asyncio as aioredis
import os
from datetime import datetime

# Import custom exceptions
from app.exceptions.custom_exceptions import CacheError

logger = logging.getLogger(__name__)

class RedisCacheService:
    """Enhanced service for caching financial data in Redis to improve performance"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.default_ttl = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes default
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.retry_delay = 5  # seconds
        self.last_ping = None
        self.ping_interval = 30  # seconds
        self.compression_threshold = 1024  # Compress values larger than 1KB
    
    async def connect(self) -> bool:
        """Initialize Redis connection with retry logic and enhanced configuration"""
        # Make Redis connection truly optional - only try once
        try:
            if self.redis_client:
                # Close existing connection if it exists
                await self.close()
            
            self.redis_client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # Keep as bytes for compression support
                retry_on_timeout=True,
                socket_keepalive=True,
                health_check_interval=30,
                socket_connect_timeout=5,
                socket_timeout=5,
                max_connections=20  # Limit connections
            )
            
            # Test connection
            if await self._ping():
                logger.info("Redis cache service connected successfully")
                self.connection_attempts = 0  # Reset on successful connection
                return True
            else:
                logger.warning("Redis ping failed, Redis cache will be disabled")
                await self.close()
                return False
                
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, Redis cache will be disabled")
            self.redis_client = None
            return False
    
    async def _ping(self) -> bool:
        """Ping Redis server to check connection health"""
        try:
            if not self.redis_client:
                return False
            
            result = self.redis_client.ping()
            # Handle both bool and Awaitable[bool] return types
            if isinstance(result, Awaitable):
                result = await result
            return bool(result)
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is active, but don't retry if not available"""
        try:
            # If no client, don't try to connect (Redis is optional)
            if not self.redis_client:
                return False
            
            # Ping to check connection only if we have a client
            return await self._ping()
            
        except Exception as e:
            logger.debug(f"Redis connection check failed: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache with compression support
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if not await self._ensure_connection() or not self.redis_client:
            return None
            
        try:
            value = self.redis_client.get(key)
            # Handle both str and Awaitable[str] return types
            if isinstance(value, Awaitable):
                value = await value
            if value:
                return value  # Return raw bytes for compression handling in cache_service
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            raise CacheError(f"Failed to get cache key {key}: {str(e)}")
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in Redis cache with enhanced performance features
        
        Args:
            key: Cache key
            value: Value to cache (will be stored as bytes for compression support)
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        if not await self._ensure_connection() or not self.redis_client:
            return False
            
        try:
            # Store value as bytes directly (already compressed in cache_service)
            result = self.redis_client.set(
                key, 
                value, 
                ex=ttl or self.default_ttl
            )
            # Handle both bool and Awaitable[bool] return types
            if isinstance(result, Awaitable):
                result = await result
            return bool(result)
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            raise CacheError(f"Failed to set cache key {key}: {str(e)}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from Redis cache
        
        Args:
            key: Cache key
            
        Returns:
            True if item was deleted or didn't exist, False if error occurred
        """
        if not await self._ensure_connection() or not self.redis_client:
            return False
            
        try:
            result = self.redis_client.delete(key)
            # Handle both int and Awaitable[int] return types
            if isinstance(result, Awaitable):
                result = await result
            return True
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            raise CacheError(f"Failed to delete cache key {key}: {str(e)}")
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern
        
        Args:
            pattern: Redis key pattern to match
            
        Returns:
            Number of keys deleted
        """
        if not await self._ensure_connection() or not self.redis_client:
            return 0
            
        try:
            # Get all matching keys
            keys_result = self.redis_client.keys(pattern)
            # Handle both list and Awaitable[list] return types
            if isinstance(keys_result, Awaitable):
                keys_result = await keys_result
            keys = list(keys_result) if keys_result else []
            if keys:
                # Delete all matching keys
                delete_result = self.redis_client.delete(*keys)
                # Handle both int and Awaitable[int] return types
                if isinstance(delete_result, Awaitable):
                    delete_result = await delete_result
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing pattern {pattern}: {e}")
            raise CacheError(f"Failed to clear pattern {pattern}: {str(e)}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        if not await self._ensure_connection() or not self.redis_client:
            return {}
            
        try:
            info_result = self.redis_client.info()
            # Handle both dict and Awaitable[dict] return types
            if isinstance(info_result, Awaitable):
                info_result = await info_result
            info = dict(info_result) if info_result else {}
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "used_memory_bytes": info.get("used_memory", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime": info.get("uptime_in_seconds", 0),
                "redis_version": info.get("redis_version", "unknown"),
                "last_ping": self.last_ping.isoformat() if self.last_ping else None
            }
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            raise CacheError(f"Failed to get Redis statistics: {str(e)}")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Redis cache service connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self.redis_client = None

# Global Redis cache service instance
redis_cache_service = RedisCacheService()

def get_redis_cache_service() -> RedisCacheService:
    """Get global Redis cache service instance"""
    return redis_cache_service