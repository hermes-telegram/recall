"""recall — smart caching for any function, simple as requests."""

from .cache import (
    cache,
    CacheBackend,
    MemoryBackend,
    DiskBackend,
    RedisBackend,
    CacheStats,
)

__all__ = [
    "cache",
    "CacheBackend",
    "MemoryBackend",
    "DiskBackend",
    "RedisBackend",
    "CacheStats",
]
__version__ = "0.3.0"
