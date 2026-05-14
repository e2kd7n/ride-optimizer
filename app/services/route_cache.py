"""
Route Cache Service

Manages caching of route data in memory and on disk.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class RouteCache:
    """
    In-memory cache for route data with TTL support.
    
    Caches route data in memory to avoid repeated disk reads. Supports
    time-to-live (TTL) to ensure data freshness.
    """
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize RouteCache.
        
        Args:
            ttl_seconds: Time-to-live for cached items in seconds (default: 1 hour)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_cache_key(self, identifier: str) -> str:
        """
        Generate a cache key from an identifier.
        
        Args:
            identifier: Unique identifier for the cached item
            
        Returns:
            Cache key
        """
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def set(self, key: str, value: List[Dict[str, Any]]) -> None:
        """
        Store a value in the cache with TTL.
        
        Args:
            key: Cache key
            value: Data to cache
        """
        cache_key = self._get_cache_key(key)
        self._cache[cache_key] = {
            'value': value,
            'timestamp': datetime.now(),
            'ttl': self.ttl_seconds
        }
        logger.debug(f"Cached {len(value)} items with key={key}")
    
    def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve a value from the cache if it exists and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        cache_key = self._get_cache_key(key)
        
        if cache_key not in self._cache:
            logger.debug(f"Cache miss: {key}")
            return None
        
        cached_item = self._cache[cache_key]
        timestamp = cached_item['timestamp']
        ttl = cached_item['ttl']
        
        # Check if cache has expired
        if datetime.now() > timestamp + timedelta(seconds=ttl):
            logger.debug(f"Cache expired: {key}")
            del self._cache[cache_key]
            return None
        
        logger.debug(f"Cache hit: {key}")
        return cached_item['value']
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was cached, False otherwise
        """
        cache_key = self._get_cache_key(key)
        
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"Invalidated cache: {key}")
            return True
        
        return False
    
    def clear(self) -> None:
        """
        Clear all cached data.
        """
        count = len(self._cache)
        self._cache.clear()
        logger.debug(f"Cleared {count} cache entries")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'size': len(self._cache),
            'ttl_seconds': self.ttl_seconds,
            'keys': list(self._cache.keys())
        }
