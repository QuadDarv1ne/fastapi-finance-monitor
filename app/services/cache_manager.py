"""Cache management service for application-level caching with TTL"""

from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Управление кэшем с TTL"""
    
    def __init__(self, ttl_seconds: int = 30):
        """
        Initialize cache manager
        
        Args:
            ttl_seconds: Time-to-live in seconds
        """
        self.cache: Dict[str, tuple[datetime, Any]] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key in self.cache:
            timestamp, value = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return value
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self.cache[key] = (datetime.now(), value)
    
    def invalidate_old(self) -> None:
        """Очистить устаревший кэш"""
        now = datetime.now()
        expired = [
            k for k, (ts, _) in self.cache.items() 
            if now - ts > timedelta(seconds=self.ttl)
        ]
        for k in expired:
            del self.cache[k]
    
    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "total_items": len(self.cache),
            "ttl_seconds": self.ttl
        }