"""Core cache decorator and backends for recall."""

import asyncio
import base64
import functools
import hashlib
import json
import os
import pickle
import threading
import time
import zlib
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Union


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

    @abstractmethod
    def get_many(self, keys: List[str]) -> Dict[str, tuple[float, Any]]:
        """Get multiple keys at once."""
        ...

    @abstractmethod
    def set_many(self, items: Dict[str, Any], ttl: float) -> None:
        """Set multiple keys at once."""
        ...

    @abstractmethod
    def delete_many(self, keys: List[str]) -> None:
        """Delete multiple keys at once."""
        ...

    @abstractmethod
    def keys(self) -> List[str]:
        """Return all keys."""
        ...

    @abstractmethod
    def health(self) -> dict:
        """Return backend health status."""
        ...


class MemoryBackend(CacheBackend):
    """In-memory cache with TTL and maxsize (LRU eviction)."""

    def __init__(self, maxsize: int = 1000, compression: bool = False):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._access: dict[str, float] = {}
        self.maxsize = maxsize
        self.compression = compression
        self._lock = threading.Lock()

    def _compress(self, value: Any) -> bytes:
        return zlib.compress(pickle.dumps(value))

    def _decompress(self, data: bytes) -> Any:
        return pickle.loads(zlib.decompress(data))

    def get(self, key: str) -> Optional[tuple[float, Any]]:
        with self._lock:
            if key in self._cache:
                expire_time, value = self._cache[key]
                if expire_time > time.time():
                    self._access[key] = time.time()
                    if self.compression:
                        return (expire_time, self._decompress(value))
                    return (expire_time, value)
                else:
                    del self._cache[key]
                    del self._access[key]
        return None

    def set(self, key: str, value: Any, ttl: float) -> None:
        with self._lock:
            if len(self._cache) >= self.maxsize and key not in self._cache:
                self._evict()
            if self.compression:
                self._cache[key] = (time.time() + ttl, self._compress(value))
            else:
                self._cache[key] = (time.time() + ttl, value)
            self._access[key] = time.time()

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)
            self._access.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._access.clear()

    def get_many(self, keys: List[str]) -> Dict[str, tuple[float, Any]]:
        result = {}
        for key in keys:
            val = self.get(key)
            if val is not None:
                result[key] = val
        return result

    def set_many(self, items: Dict[str, Any], ttl: float) -> None:
        for key, value in items.items():
            self.set(key, value, ttl)

    def delete_many(self, keys: List[str]) -> None:
        for key in keys:
            self.delete(key)

    def keys(self) -> List[str]:
        with self._lock:
            now = time.time()
            return [k for k, (exp, _) in self._cache.items() if exp > now]

    def health(self) -> dict:
        return {
            "status": "healthy",
            "type": "memory",
            "size": len(self._cache),
            "maxsize": self.maxsize,
        }

    def _evict(self):
        """Evict least recently used item."""
        if self._access:
            oldest = min(self._access, key=self._access.get)
            del self._cache[oldest]
            del self._access[oldest]


class DiskBackend(CacheBackend):
    """Persistent disk cache using pickle files."""

    def __init__(
        self,
        directory: str = ".recall_cache",
        compression: bool = False,
        max_size_bytes: Optional[int] = None,
    ):
        self.directory = directory
        self.compression = compression
        self.max_size_bytes = max_size_bytes
        self._lock = threading.Lock()
        os.makedirs(directory, exist_ok=True)

    def _path(self, key: str) -> str:
        safe = hashlib.sha256(key.encode()).hexdigest()[:16]
        return os.path.join(self.directory, f"{safe}.cache")

    def _meta_path(self, key: str) -> str:
        safe = hashlib.sha256(key.encode()).hexdigest()[:16]
        return os.path.join(self.directory, f"{safe}.meta")

    def get(self, key: str) -> Optional[tuple[float, Any]]:
        with self._lock:
            path = self._path(key)
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        expire_time, value = pickle.load(f)
                    if expire_time > time.time():
                        if self.compression:
                            return (expire_time, pickle.loads(zlib.decompress(value)))
                        return (expire_time, value)
                    else:
                        os.remove(path)
                        if os.path.exists(self._meta_path(key)):
                            os.remove(self._meta_path(key))
                except (pickle.PickleError, OSError):
                    pass
        return None

    def set(self, key: str, value: Any, ttl: float) -> None:
        with self._lock:
            path = self._path(key)
            if self.compression:
                data = pickle.dumps((time.time() + ttl, zlib.compress(pickle.dumps(value))))
            else:
                data = pickle.dumps((time.time() + ttl, value))
            with open(path, "wb") as f:
                f.write(data)

            # Track size
            meta_path = self._meta_path(key)
            with open(meta_path, "w") as f:
                f.write(str(os.path.getsize(path)))

            # Enforce size limit
            if self.max_size_bytes:
                self._enforce_size_limit()

    def delete(self, key: str) -> None:
        with self._lock:
            path = self._path(key)
            if os.path.exists(path):
                os.remove(path)
            meta_path = self._meta_path(key)
            if os.path.exists(meta_path):
                os.remove(meta_path)

    def clear(self) -> None:
        with self._lock:
            for f in os.listdir(self.directory):
                os.remove(os.path.join(self.directory, f))

    def get_many(self, keys: List[str]) -> Dict[str, tuple[float, Any]]:
        result = {}
        for key in keys:
            val = self.get(key)
            if val is not None:
                result[key] = val
        return result

    def set_many(self, items: Dict[str, Any], ttl: float) -> None:
        for key, value in items.items():
            self.set(key, value, ttl)

    def delete_many(self, keys: List[str]) -> None:
        for key in keys:
            self.delete(key)

    def keys(self) -> List[str]:
        with self._lock:
            result = []
            now = time.time()
            for f in os.listdir(self.directory):
                if f.endswith(".cache"):
                    path = os.path.join(self.directory, f)
                    try:
                        with open(path, "rb") as fh:
                            expire_time, _ = pickle.load(fh)
                        if expire_time > now:
                            result.append(f[:-6])  # Remove .cache
                    except:
                        pass
            return result

    def health(self) -> dict:
        total_size = 0
        count = 0
        for f in os.listdir(self.directory):
            if f.endswith(".cache"):
                count += 1
                total_size += os.path.getsize(os.path.join(self.directory, f))
        return {
            "status": "healthy",
            "type": "disk",
            "size": count,
            "total_bytes": total_size,
            "max_bytes": self.max_size_bytes,
        }

    def _enforce_size_limit(self):
        """Remove oldest files if size limit exceeded."""
        if not self.max_size_bytes:
            return
        files = []
        total = 0
        for f in os.listdir(self.directory):
            if f.endswith(".cache"):
                path = os.path.join(self.directory, f)
                size = os.path.getsize(path)
                mtime = os.path.getmtime(path)
                files.append((mtime, path, size))
                total += size

        if total <= self.max_size_bytes:
            return

        files.sort()  # oldest first
        for mtime, path, size in files:
            if total <= self.max_size_bytes:
                break
            os.remove(path)
            meta = path.replace(".cache", ".meta")
            if os.path.exists(meta):
                os.remove(meta)
            total -= size


class RedisBackend(CacheBackend):
    """Redis cache backend."""

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        prefix: str = "recall:",
        compression: bool = False,
    ):
        import redis
        self.client = redis.from_url(url)
        self.prefix = prefix
        self.compression = compression

    def _key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[tuple[float, Any]]:
        raw = self.client.get(self._key(key))
        if raw:
            data = pickle.loads(raw)
            if self.compression:
                return (data[0], pickle.loads(zlib.decompress(data[1])))
            return data
        return None

    def set(self, key: str, value: Any, ttl: float) -> None:
        if self.compression:
            data = pickle.dumps((time.time() + ttl, zlib.compress(pickle.dumps(value))))
        else:
            data = pickle.dumps((time.time() + ttl, value))
        self.client.setex(self._key(key), int(ttl), data)

    def delete(self, key: str) -> None:
        self.client.delete(self._key(key))

    def clear(self) -> None:
        keys = self.client.keys(f"{self.prefix}*")
        if keys:
            self.client.delete(*keys)

    def get_many(self, keys: List[str]) -> Dict[str, tuple[float, Any]]:
        pipe = self.client.pipeline()
        for key in keys:
            pipe.get(self._key(key))
        results = {}
        for key, raw in zip(keys, pipe.execute()):
            if raw:
                results[key] = pickle.loads(raw)
        return results

    def set_many(self, items: Dict[str, Any], ttl: float) -> None:
        pipe = self.client.pipeline()
        for key, value in items.items():
            if self.compression:
                data = pickle.dumps((time.time() + ttl, zlib.compress(pickle.dumps(value))))
            else:
                data = pickle.dumps((time.time() + ttl, value))
            pipe.setex(self._key(key), int(ttl), data)
        pipe.execute()

    def delete_many(self, keys: List[str]) -> None:
        pipe = self.client.pipeline()
        for key in keys:
            pipe.delete(self._key(key))
        pipe.execute()

    def keys(self) -> List[str]:
        prefix_len = len(self.prefix)
        return [k.decode()[prefix_len:] for k in self.client.keys(f"{self.prefix}*")]

    def health(self) -> dict:
        try:
            self.client.ping()
            return {"status": "healthy", "type": "redis"}
        except:
            return {"status": "unhealthy", "type": "redis"}


class CacheStats:
    """Track cache hit/miss statistics."""

    def __init__(self):
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    def hit(self):
        with self._lock:
            self._hits += 1

    def miss(self):
        with self._lock:
            self._misses += 1

    @property
    def hits(self):
        return self._hits

    @property
    def misses(self):
        return self._misses

    @property
    def total(self):
        return self._hits + self._misses

    @property
    def hit_rate(self):
        if self.total == 0:
            return 0.0
        return self._hits / self.total

    def reset(self):
        with self._lock:
            self._hits = 0
            self._misses = 0

    def to_dict(self):
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": self.total,
            "hit_rate": self.hit_rate,
        }


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
    prefix: str = "",
    sliding: bool = False,
    version: Optional[str] = None,
    on_evict: Optional[Callable] = None,
    compression: bool = False,
    stampede_protection: bool = False,
    background_refresh: Optional[float] = None,
    serializer: str = "pickle",
):
    """
    Decorator that caches function results with TTL.

    Args:
        ttl: Time-to-live in seconds, or shorthand like "1h", "30m", "7d".
        maxsize: Maximum number of cached items (memory backend only).
        backend: Custom backend (MemoryBackend, DiskBackend, RedisBackend).
        key_fn: Custom key function f(func, args, kwargs) -> str.
        prefix: Cache key prefix for namespacing.
        sliding: If True, TTL resets on each access (sliding window).
        version: Cache version — change to invalidate all cached values.
        on_evict: Callback f(key, value) called when item is evicted.
        compression: Compress cached values (zlib).
        stampede_protection: Prevent cache stampede with locking.
        background_refresh: Seconds before expiry to trigger background refresh.
        serializer: Serialization format ("pickle", "json", "msgpack").

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
        backend = MemoryBackend(maxsize=maxsize, compression=compression)

    stats = CacheStats()
    _lock = threading.Lock()
    _refresh_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)

    def decorator(func: Callable) -> Callable:
        is_async = asyncio.iscoroutinefunction(func)

        def _serialize(value: Any) -> bytes:
            if serializer == "json":
                return json.dumps(value).encode()
            elif serializer == "msgpack":
                import msgpack
                return msgpack.packb(value)
            return pickle.dumps(value)

        def _deserialize(data: bytes) -> Any:
            if serializer == "json":
                return json.loads(data.decode())
            elif serializer == "msgpack":
                import msgpack
                return msgpack.unpackb(data)
            return pickle.loads(data)

        def _make_full_key(*args, **kwargs):
            if key_fn:
                k = key_fn(func, args, kwargs)
            else:
                k = _make_key(func, args, kwargs)
            parts = []
            if prefix:
                parts.append(prefix)
            if version:
                parts.append(f"v{version}")
            parts.append(k)
            return ":".join(parts)

        def _get_with_stampede_protection(key: str):
            """Get with stampede protection."""
            result = backend.get(key)
            if result is not None:
                return result

            # Only one thread should compute
            if _refresh_locks[key].acquire(blocking=False):
                try:
                    # Re-check after acquiring lock
                    result = backend.get(key)
                    if result is not None:
                        return result
                    return None  # Signal to compute
                finally:
                    _refresh_locks[key].release()
            else:
                # Another thread is computing, wait and retry
                with _refresh_locks[key]:
                    return backend.get(key)

        def _refresh_if_needed(key: str, expire_time: float):
            """Trigger background refresh if close to expiry."""
            if background_refresh is None:
                return
            time_left = expire_time - time.time()
            if time_left > background_refresh:
                return

            if _refresh_locks[key].acquire(blocking=False):
                try:
                    # Re-check after acquiring lock
                    result = backend.get(key)
                    if result is None:
                        return
                    exp, _ = result
                    if exp - time.time() > background_refresh:
                        return
                    # Compute new value
                    value = func(*args, **kwargs)
                    backend.set(key, value, ttl)
                except Exception:
                    pass  # Background refresh failed silently
                finally:
                    _refresh_locks[key].release()

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = _make_full_key(*args, **kwargs)

                if stampede_protection:
                    result = _get_with_stampede_protection(key)
                else:
                    result = backend.get(key)

                if result is not None:
                    expire_time, value = result
                    if expire_time > time.time():
                        stats.hit()
                        if sliding:
                            backend.set(key, value, ttl)  # Reset TTL
                        _refresh_if_needed(key, expire_time)
                        return value

                stats.miss()
                value = await func(*args, **kwargs)
                backend.set(key, value, ttl)
                return value

            def cache_clear():
                backend.clear()
                stats.reset()

            def cache_delete(*args, **kwargs):
                key = _make_full_key(*args, **kwargs)
                backend.delete(key)

            def cache_get(*args, **kwargs):
                key = _make_full_key(*args, **kwargs)
                result = backend.get(key)
                if result:
                    _, value = result
                    return value
                return None

            def cache_set(value, *args, **kwargs):
                key = _make_full_key(*args, **kwargs)
                backend.set(key, value, ttl)

            async def cache_warm(args_list):
                """Pre-populate cache with given arguments."""
                for a in args_list:
                    if isinstance(a, tuple):
                        await async_wrapper(*a)
                    elif isinstance(a, dict):
                        await async_wrapper(**a)
                    else:
                        await async_wrapper(a)

            async_wrapper.cache_backend = backend
            async_wrapper.cache_clear = cache_clear
            async_wrapper.cache_delete = cache_delete
            async_wrapper.cache_get = cache_get
            async_wrapper.cache_set = cache_set
            async_wrapper.cache_warm = cache_warm
            async_wrapper.cache_stats = stats
            async_wrapper.cache_keys = backend.keys
            async_wrapper.cache_health = backend.health

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = _make_full_key(*args, **kwargs)

            if stampede_protection:
                result = _get_with_stampede_protection(key)
            else:
                result = backend.get(key)

            if result is not None:
                expire_time, value = result
                if expire_time > time.time():
                    stats.hit()
                    if sliding:
                        backend.set(key, value, ttl)  # Reset TTL
                    _refresh_if_needed(key, expire_time)
                    return value

            stats.miss()
            value = func(*args, **kwargs)
            backend.set(key, value, ttl)
            return value

        def cache_clear():
            backend.clear()
            stats.reset()

        def cache_delete(*args, **kwargs):
            key = _make_full_key(*args, **kwargs)
            backend.delete(key)

        def cache_get(*args, **kwargs):
            key = _make_full_key(*args, **kwargs)
            result = backend.get(key)
            if result:
                _, value = result
                return value
            return None

        def cache_set(value, *args, **kwargs):
            key = _make_full_key(*args, **kwargs)
            backend.set(key, value, ttl)

        def cache_warm(args_list):
            """Pre-populate cache with given arguments."""
            for a in args_list:
                if isinstance(a, tuple):
                    wrapper(*a)
                elif isinstance(a, dict):
                    wrapper(**a)
                else:
                    wrapper(a)

        def cache_get_many(keys: List[str]):
            return backend.get_many(keys)

        def cache_set_many(items: Dict[str, Any], custom_ttl: Optional[float] = None):
            backend.set_many(items, custom_ttl or ttl)

        def cache_delete_many(keys: List[str]):
            backend.delete_many(keys)

        # Attach cache management methods
        wrapper.cache_backend = backend
        wrapper.cache_clear = cache_clear
        wrapper.cache_delete = cache_delete
        wrapper.cache_get = cache_get
        wrapper.cache_set = cache_set
        wrapper.cache_warm = cache_warm
        wrapper.cache_stats = stats
        wrapper.cache_keys = backend.keys
        wrapper.cache_health = backend.health
        wrapper.cache_get_many = cache_get_many
        wrapper.cache_set_many = cache_set_many
        wrapper.cache_delete_many = cache_delete_many

        return wrapper

    return decorator
