"""Core cache decorator and backends for recall."""

import functools
import hashlib
import json
import os
import pickle
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Union


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[tuple[float, Any]]:
        """Return (expire_time, value) or None."""
        ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float) -> None:
        """Store value with TTL in seconds."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a key."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        ...


class MemoryBackend(CacheBackend):
    """In-memory cache with TTL and maxsize (LRU eviction)."""

    def __init__(self, maxsize: int = 1000):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._access: dict[str, float] = {}
        self.maxsize = maxsize

    def get(self, key: str) -> Optional[tuple[float, Any]]:
        if key in self._cache:
            expire_time, value = self._cache[key]
            if expire_time > time.time():
                self._access[key] = time.time()
                return (expire_time, value)
            else:
                del self._cache[key]
                del self._access[key]
        return None

    def set(self, key: str, value: Any, ttl: float) -> None:
        if len(self._cache) >= self.maxsize and key not in self._cache:
            self._evict()
        self._cache[key] = (time.time() + ttl, value)
        self._access[key] = time.time()

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)
        self._access.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()
        self._access.clear()

    def _evict(self):
        """Evict least recently used item."""
        if self._access:
            oldest = min(self._access, key=self._access.get)
            del self._cache[oldest]
            del self._access[oldest]


class DiskBackend(CacheBackend):
    """Persistent disk cache using pickle files."""

    def __init__(self, directory: str = ".recall_cache"):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def _path(self, key: str) -> str:
        safe = hashlib.sha256(key.encode()).hexdigest()[:16]
        return os.path.join(self.directory, f"{safe}.cache")

    def get(self, key: str) -> Optional[tuple[float, Any]]:
        path = self._path(key)
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    expire_time, value = pickle.load(f)
                if expire_time > time.time():
                    return (expire_time, value)
                else:
                    os.remove(path)
            except (pickle.PickleError, OSError):
                pass
        return None

    def set(self, key: str, value: Any, ttl: float) -> None:
        path = self._path(key)
        with open(path, "wb") as f:
            pickle.dump((time.time() + ttl, value), f)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)

    def clear(self) -> None:
        for f in os.listdir(self.directory):
            if f.endswith(".cache"):
                os.remove(os.path.join(self.directory, f))


class RedisBackend(CacheBackend):
    """Redis cache backend."""

    def __init__(self, url: str = "redis://localhost:6379", prefix: str = "recall:"):
        import redis
        self.client = redis.from_url(url)
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[tuple[float, Any]]:
        raw = self.client.get(self._key(key))
        if raw:
            return pickle.loads(raw)
        return None

    def set(self, key: str, value: Any, ttl: float) -> None:
        data = pickle.dumps((time.time() + ttl, value))
        self.client.setex(self._key(key), int(ttl), data)

    def delete(self, key: str) -> None:
        self.client.delete(self._key(key))

    def clear(self) -> None:
        keys = self.client.keys(f"{self.prefix}*")
        if keys:
            self.client.delete(*keys)


def _make_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """Generate a unique cache key from function and arguments."""
    key_data = json.dumps({
        "func": f"{func.__module__}.{func.__qualname__}",
        "args": args,
        "kwargs": kwargs,
    }, sort_keys=True, default=str)
    return hashlib.sha256(key_data.encode()).hexdigest()


def cache(
    ttl: Union[str, float] = "1h",
    maxsize: int = 1000,
    backend: Optional[CacheBackend] = None,
    key_fn: Optional[Callable] = None,
):
    """
    Decorator that caches function results with TTL.

    Args:
        ttl: Time-to-live in seconds, or shorthand like "1h", "30m", "7d".
        maxsize: Maximum number of cached items (memory backend only).
        backend: Custom backend (MemoryBackend, DiskBackend, RedisBackend).
        key_fn: Custom key function f(func, args, kwargs) -> str.

    Usage:
        @cache(ttl="1h")
        def get_user(user_id):
            return db.query(user_id)

        @cache(ttl=300, backend=DiskBackend("/tmp/cache"))
        def expensive_computation(x, y):
            return x ** y
    """
    # Parse TTL shorthand
    if isinstance(ttl, str):
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        ttl = float(ttl[:-1]) * multipliers.get(ttl[-1].lower(), 1)

    if backend is None:
        backend = MemoryBackend(maxsize=maxsize)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if key_fn:
                k = key_fn(func, args, kwargs)
            else:
                k = _make_key(func, args, kwargs)

            result = backend.get(k)
            if result is not None:
                _, value = result
                return value

            value = func(*args, **kwargs)
            backend.set(k, value, ttl)
            return value

        # Attach cache management methods
        wrapper.cache_backend = backend
        wrapper.cache_clear = backend.clear

        def _cache_delete(*a, **kw):
            k = key_fn(func, a, kw) if key_fn else _make_key(func, a, kw)
            backend.delete(k)

        wrapper.cache_delete = _cache_delete

        return wrapper

    return decorator
