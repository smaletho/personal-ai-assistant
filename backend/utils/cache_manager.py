"""
Cache management utility for API responses.
Implements LRU (Least Recently Used) cache eviction strategy with TTL support.
"""
import datetime
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Manages cache for API responses with size limits and LRU eviction strategy.
    
    This class provides a generic caching mechanism with the following features:
    - Time-based expiration (Time To Live - TTL)
    - Size-limited cache with LRU eviction
    - Cache invalidation by keys or patterns
    - Usage tracking for LRU implementation
    
    Usage example:
    ```python
    # Create a cache with max 100 items and 5 minute TTL
    calendar_cache = CacheManager(max_items=100, ttl_seconds=300)
    
    # Store an item
    calendar_cache.set('calendar:primary', calendar_data)
    
    # Retrieve an item (returns None if missing or expired)
    data = calendar_cache.get('calendar:primary')
    
    # Invalidate cache entries by pattern
    calendar_cache.invalidate(pattern='events:')
    ```
    """
    
    def __init__(self, max_items: int = 100, ttl_seconds: int = 300):
        """
        Initialize cache manager with size limits and TTL.
        
        Args:
            max_items: Maximum number of items to store in the cache
            ttl_seconds: Time to live for cache entries in seconds
        """
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: Dict[str, float] = {}
        self.access_history: Dict[str, float] = {}  # Track usage timestamp for LRU
        self.max_items = max_items
        self.ttl = ttl_seconds
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get a cached item if it exists and is still valid.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            The cached value if found and valid, otherwise None
        """
        if key not in self.cache:
            return None
            
        if not self._is_valid(key):
            logger.debug(f"Cache expired for key: {key}")
            self._remove(key)
            return None
            
        # Update access history for LRU
        self._update_access(key)
        logger.debug(f"Cache hit for key: {key}")
        return self.cache[key]
        
    def set(self, key: str, value: Any) -> Any:
        """
        Set a cached item with expiration time.
        If cache is full, evict least recently used item.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            The cached value
        """
        # Check if we need to evict items
        if len(self.cache) >= self.max_items and key not in self.cache:
            self._evict_lru()
            
        self.cache[key] = value
        self.cache_expiry[key] = datetime.datetime.now().timestamp() + self.ttl
        self._update_access(key)
        logger.debug(f"Cache set for key: {key}")
        return value
        
    def invalidate(self, key: Optional[str] = None, pattern: Optional[str] = None):
        """
        Invalidate cache entries by key or pattern or clear all if both None.
        
        Args:
            key: Specific key to invalidate
            pattern: String pattern to match keys against for invalidation
        """
        if key is not None:
            # Invalidate specific key
            self._remove(key)
            logger.debug(f"Cache invalidated for key: {key}")
            return
        
        if pattern is not None:
            # Invalidate by pattern
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for k in keys_to_remove:
                self._remove(k)
            logger.debug(f"Cache invalidated {len(keys_to_remove)} items matching pattern: {pattern}")
            return
        
        # Invalidate all
        self.cache.clear()
        self.cache_expiry.clear()
        self.access_history.clear()
        logger.debug("Cache completely cleared")
    
    def _is_valid(self, key: str) -> bool:
        """
        Check if a cache entry is still valid (not expired).
        
        Args:
            key: Cache key to check
            
        Returns:
            True if the cache entry is still valid, False otherwise
        """
        if key not in self.cache_expiry:
            return False
        return datetime.datetime.now().timestamp() < self.cache_expiry[key]
    
    def _update_access(self, key: str):
        """
        Update the access history for a key for LRU tracking.
        
        Args:
            key: Cache key that was accessed
        """
        self.access_history[key] = datetime.datetime.now().timestamp()
    
    def _remove(self, key: str):
        """
        Remove a key from all dictionaries.
        
        Args:
            key: Cache key to remove
        """
        if key in self.cache:
            del self.cache[key]
        if key in self.cache_expiry:
            del self.cache_expiry[key]
        if key in self.access_history:
            del self.access_history[key]
    
    def _evict_lru(self):
        """
        Evict the least recently used item from the cache.
        """
        if not self.access_history:
            return
            
        # Find the key with the oldest access timestamp
        lru_key = min(self.access_history.items(), key=lambda x: x[1])[0]
        logger.debug(f"Evicting LRU cache item: {lru_key}")
        self._remove(lru_key)
