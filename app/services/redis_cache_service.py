"""Redis cache service for storing and retrieving financial data"""

import asyncio
import json
import logging
from typing import Any, Optional, Dict, Union, Awaitable
from redis import asyncio as aioredis
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class RedisCacheService:
    """Service for caching financial data in Redis to improve performance"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.default_ttl = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes default
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.retry_delay = 5  # seconds
        self.last_ping = None
        self.ping_interval = 30  # seconds
    
    async def connect(self) -> bool:
        """Initialize Redis connection with retry logic"""
        while self.connection_attempts < self.max_connection_attempts:
            try:
                if self.redis_client:
                    # Close existing connection if it exists
                    await self.close()
                
                self.redis_client = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    health_check_interval=30,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                
                # Test connection
                if await self._ping():
                    logger.info("Redis cache service connected successfully")
                    self.connection_attempts = 0  # Reset on successful connection
                    return True
                    
            except Exception as e:
                self.connection_attempts += 1
                logger.warning(f"Failed to connect to Redis (attempt {self.connection_attempts}/{self.max_connection_attempts}): {e}")
                if self.connection_attempts < self.max_connection_attempts:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to connect to Redis after {self.max_connection_attempts} attempts")
                    self.redis_client = None
                    return False
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
        """Ensure Redis connection is active, reconnect if needed"""
        try:
            # Check if we need to ping (to avoid excessive pings)
            if self.last_ping:
                time_since_last_ping = (datetime.now() - self.last_ping).seconds
                if time_since_last_ping < self.ping_interval:
                    return self.redis_client is not None
            
            # If no client, try to connect
            if not self.redis_client:
                return await self.connect()
            
            # Ping to check connection
            return await self._ping()
            
        except Exception as e:
            logger.warning(f"Redis connection check failed: {e}")
            return await self.connect()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache
        
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
                # Try to parse as JSON, if fails return as string
                try:
                    return json.loads(str(value))
                except json.JSONDecodeError:
                    return str(value)
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in Redis cache
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        if not await self._ensure_connection() or not self.redis_client:
            return False
            
        try:
            # Serialize value to JSON string
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            # Set with TTL
            result = self.redis_client.set(
                key, 
                serialized_value, 
                ex=ttl or self.default_ttl
            )
            # Handle both bool and Awaitable[bool] return types
            if isinstance(result, Awaitable):
                result = await result
            return bool(result)
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
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
            return False
    
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
            return 0
    
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
            return {}
    
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