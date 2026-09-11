"""Django Plugin for recall-cache."""

from typing import Optional, Callable, Any

from recall.cache import CacheBackend, MemoryBackend


class DjangoCache:
    """
    Django plugin for recall-cache.
    
    Usage:
        # settings.py
        CACHES = {
            'default': {
                'BACKEND': 'recall.plugins.django_plugin.RecallCache',
                'LOCATION': 'recall-cache',
                'OPTIONS': {
                    'MAX_ENTRIES': 1000,
                    'CULL_FREQUENCY': 3,
                }
            }
        }
        
        # views.py
        from django.core.cache import cache
        
        cache.set('key', 'value', timeout=300)
        value = cache.get('key')
    """
    
    def __init__(self, backend: Optional[CacheBackend] = None, prefix: str = "django:"):
        self.backend = backend or MemoryBackend()
        self.prefix = prefix
    
    def _prefixed_key(self, key: str) -> str:
        return f"{self.prefix}{key}"
    
    def get(self, key: str, default: Any = None, version: Optional[str] = None) -> Any:
        """Get a value from cache."""
        result = self.backend.get(self._prefixed_key(key))
        if result is not None:
            _, value = result
            return value
        return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None, version: Optional[str] = None):
        """Set a value in cache."""
        ttl = timeout or 300
        self.backend.set(self._prefixed_key(key), value, ttl)
    
    def delete(self, key: str, version: Optional[str] = None):
        """Delete a key from cache."""
        self.backend.delete(self._prefixed_key(key))
    
    def get_many(self, keys: list, version: Optional[str] = None) -> dict:
        """Get multiple values."""
        result = {}
        for key in keys:
            value = self.get(key, version=version)
            if value is not None:
                result[key] = value
        return result
    
    def set_many(self, data: dict, timeout: Optional[int] = None, version: Optional[str] = None):
        """Set multiple values."""
        ttl = timeout or 300
        for key, value in data.items():
            self.set(key, value, ttl, version=version)
    
    def delete_many(self, keys: list, version: Optional[str] = None):
        """Delete multiple keys."""
        for key in keys:
            self.delete(key, version=version)
    
    def clear(self):
        """Clear all cache."""
        self.backend.clear()
    
    def has_key(self, key: str, version: Optional[str] = None) -> bool:
        """Check if key exists."""
        return self.backend.get(self._prefixed_key(key)) is not None
    
    def incr(self, key: str, delta: int = 1, version: Optional[str] = None) -> int:
        """Increment a value."""
        value = self.get(key, 0, version=version)
        value += delta
        self.set(key, value, version=version)
        return value
    
    def decr(self, key: str, delta: int = 1, version: Optional[str] = None) -> int:
        """Decrement a value."""
        value = self.get(key, 0, version=version)
        value -= delta
        self.set(key, value, version=version)
        return value
    
    def touch(self, key: str, timeout: Optional[int] = None, version: Optional[str] = None) -> bool:
        """Update TTL of a key."""
        result = self.backend.get(self._prefixed_key(key))
        if result:
            _, value = result
            self.set(key, value, timeout, version=version)
            return True
        return False
    
    def get_backend(self) -> CacheBackend:
        """Get the underlying backend."""
        return self.backend


class RecallCache(DjangoCache):
    """
    Django cache backend class.
    
    Usage in settings.py:
        CACHES = {
            'default': {
                'BACKEND': 'recall.plugins.django_plugin.RecallCache',
                'LOCATION': 'recall-cache',
            }
        }
    """
    pass
