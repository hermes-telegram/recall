"""FastAPI Plugin for recall-cache."""

from typing import Optional, Callable, Any

from recall.cache import CacheBackend, MemoryBackend


class FastAPICache:
    """
    FastAPI plugin for recall-cache.
    
    Usage:
        from fastapi import FastAPI
        from recall.plugins.fastapi import FastAPICache
        
        app = FastAPI()
        cache = FastAPICache(app, backend=MemoryBackend())
        
        @app.get("/users/{user_id}")
        @cache.route(ttl="5m")
        def get_user(user_id: int):
            return {"user": user_id}
    """
    
    def __init__(
        self,
        app=None,
        backend: Optional[CacheBackend] = None,
        prefix: str = "api:",
        default_ttl: str = "5m",
    ):
        self.backend = backend or MemoryBackend()
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.app = app
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with FastAPI app."""
        self.app = app
        
        @app.get("/cache/stats")
        def cache_stats():
            return self.backend.health()
        
        @app.get("/cache/keys")
        def cache_keys():
            return {"keys": self.backend.keys()}
        
        @app.delete("/cache/clear")
        def cache_clear():
            self.backend.clear()
            return {"status": "ok"}
    
    def route(self, ttl: Optional[str] = None, key_fn: Optional[Callable] = None):
        """
        Decorator for caching FastAPI route responses.
        
        Usage:
            @app.get("/users/{user_id}")
            @cache.route(ttl="5m")
            def get_user(user_id: int):
                return {"user": user_id}
        """
        from recall.cache import cache
        
        def decorator(func):
            cached_func = cache(
                ttl=ttl or self.default_ttl,
                backend=self.backend,
                prefix=self.prefix,
                key_fn=key_fn or self._default_key_fn,
            )(func)
            
            return cached_func
        
        return decorator
    
    def _default_key_fn(self, func, args, kwargs):
        """Default key function for routes."""
        return f"{func.__name__}:{args}:{kwargs}"
