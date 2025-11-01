"""LRU Cache implementation with size limitations"""

from collections import OrderedDict
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class LRUCache:
    """LRU кэш с ограничением размера"""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize LRU cache
        
        Args:
            max_size: Maximum number of items to store in cache
        """
        self.cache = OrderedDict()
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache and move to end (mark as recently used)
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if key in self.cache:
            # Move to end to mark as recently used
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self.cache:
            # Move to end to mark as recently used
            self.cache.move_to_end(key)
        self.cache[key] = value
        
        # Remove oldest item if we've exceeded max size
        if len(self.cache) > self.max_size:
            # popitem(last=False) removes the first (oldest) item
            self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
    
    def remove(self, key: str) -> bool:
        """
        Remove specific key from cache
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was removed, False if key was not found
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "current_size": len(self.cache),
            "max_size": self.max_size,
            "usage_percentage": round(len(self.cache) / self.max_size * 100, 2) if self.max_size > 0 else 0
        }