"""recall — smart caching for any function, simple as requests."""

from .cache import cache, CacheBackend, MemoryBackend, DiskBackend, RedisBackend

__all__ = ["cache", "CacheBackend", "MemoryBackend", "DiskBackend", "RedisBackend"]
__version__ = "0.1.0"
