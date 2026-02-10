"""
Cache Manager
Handles caching for improved performance
"""

import time
import hashlib
from typing import Dict, Optional, Any
from collections import OrderedDict


class CacheManager:
    """In-memory cache with TTL support"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.metadata = {}
    
    def _generate_key(self, *args) -> str:
        """Generate cache key from arguments"""
        key_string = ':'.join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set cache value with TTL"""
        if ttl is None:
            ttl = self.default_ttl
        
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        
        self.cache[key] = value
        self.metadata[key] = {
            'timestamp': time.time(),
            'ttl': ttl,
            'expires_at': time.time() + ttl
        }
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache value if not expired"""
        if key not in self.cache:
            return None
        
        # Check expiration
        meta = self.metadata.get(key)
        if meta and time.time() > meta['expires_at']:
            # Expired - remove it
            del self.cache[key]
            del self.metadata[key]
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def delete(self, key: str):
        """Delete cache entry"""
        if key in self.cache:
            del self.cache[key]
        if key in self.metadata:
            del self.metadata[key]
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.metadata.clear()
    
    def cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, meta in self.metadata.items()
            if current_time > meta['expires_at']
        ]
        
        for key in expired_keys:
            self.delete(key)
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'usage_percent': (len(self.cache) / self.max_size) * 100,
            'oldest_entry': min(self.metadata.values(), 
                              key=lambda x: x['timestamp'])['timestamp'] if self.metadata else None,
            'newest_entry': max(self.metadata.values(),
                              key=lambda x: x['timestamp'])['timestamp'] if self.metadata else None
        }


# Global instance
cache_manager = CacheManager()
