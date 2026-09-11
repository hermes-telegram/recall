"""HTTP Caching (ETag, Cache-Control) for recall-cache."""

import hashlib
import time
import functools
from typing import Optional, Any, Callable

from recall.cache import CacheBackend


class HTTPCache:
    """
    HTTP Caching with ETag and Cache-Control headers.
    
    Usage:
        from recall.http_cache import HTTPCache
        
        http_cache = HTTPCache(backend)
        
        @http_cache.etag(ttl="1h")
        def get_user(user_id):
            return {"id": user_id, "name": "Ali"}
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def etag(self, ttl: float = 300, key_fn: Callable = None):
        """Decorator for ETag-based caching."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = key_fn(*args, **kwargs) if key_fn else f"{func.__name__}:{args}:{kwargs}"
                
                result = self.backend.get(key)
                if result:
                    _, value = result
                    etag = hashlib.md5(str(value).encode()).hexdigest()
                    return {"value": value, "etag": etag, "cached": True}
                
                value = func(*args, **kwargs)
                self.backend.set(key, value, ttl)
                etag = hashlib.md5(str(value).encode()).hexdigest()
                return {"value": value, "etag": etag, "cached": False}
            
            return wrapper
        return decorator
    
    def check_none_match(self, key: str, if_none_match: str) -> bool:
        """Check if client's ETag matches."""
        result = self.backend.get(key)
        if result:
            _, value = result
            etag = hashlib.md5(str(value).encode()).hexdigest()
            return etag == if_none_match
        return False


class CacheControl:
    """
    Cache-Control header support.
    
    Usage:
        from recall.http_cache import CacheControl
        
        cc = CacheControl(backend)
        
        @cc.cached(max_age=3600, stale_while_revalidate=60)
        def get_data(key):
            return fetch(key)
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def cached(self, max_age: int = 300, stale_while_revalidate: int = 0, must_revalidate: bool = False):
        """Decorator with Cache-Control directives."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = f"{func.__name__}:{args}:{kwargs}"
                
                result = self.backend.get(key)
                if result:
                    expire_time, value = result
                    remaining = expire_time - time.time()
                    
                    if remaining > 0:
                        headers = {
                            "Cache-Control": f"max-age={max_age}",
                            "X-Cache": "HIT",
                            "X-Cache-TTL": str(int(remaining)),
                        }
                        if stale_while_revalidate > 0:
                            headers["Cache-Control"] += f", stale-while-revalidate={stale_while_revalidate}"
                        if must_revalidate:
                            headers["Cache-Control"] += ", must-revalidate"
                        
                        return {"value": value, "headers": headers}
                
                value = func(*args, **kwargs)
                ttl = max_age + stale_while_revalidate
                self.backend.set(key, value, ttl)
                
                headers = {
                    "Cache-Control": f"max-age={max_age}",
                    "X-Cache": "MISS",
                }
                return {"value": value, "headers": headers}
            
            return wrapper
        return decorator
