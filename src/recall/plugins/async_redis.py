"""Async Redis Backend for recall-cache."""

import asyncio
import hashlib
import json
import time
import threading
import pickle
import zlib
from typing import Any, Dict, List, Optional

from recall.cache import CacheBackend


class AsyncRedisBackend(CacheBackend):
    """
    Async Redis cache backend using aioredis.
    
    Usage:
        from recall.plugins.async_redis import AsyncRedisBackend
        
        backend = AsyncRedisBackend("redis://localhost:6379")
        
        # In async function:
        await backend.async_set("key", "value", ttl=300)
        value = await backend.async_get("key")
    """
    
    def __init__(
        self,
        url: str = "redis://localhost:6379",
        prefix: str = "recall:",
        compression: bool = False,
        compression_level: int = 6,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        serializer: str = "pickle",
        key_hash: bool = False,
        db: int = 0,
    ):
        self.url = url
        self.prefix = prefix
        self.compression = compression
        self.compression_level = compression_level
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.serializer = serializer
        self.key_hash = key_hash
        self.db = db
        self.socket_timeout = socket_timeout
        self.retry_on_timeout = retry_on_timeout
        self.max_connections = max_connections
        
        self._client = None
        self._lock = threading.Lock()
        self._init_serializer()
    
    def _init_serializer(self):
        """Initialize serializer functions."""
        if self.serializer == "json":
            self._serialize = lambda v: json.dumps(v).encode()
            self._deserialize = lambda v: json.loads(v.decode())
        elif self.serializer == "msgpack":
            import msgpack
            self._serialize = lambda v: msgpack.packb(v)
            self._deserialize = lambda v: msgpack.unpackb(v)
        else:
            self._serialize = pickle.dumps
            self._deserialize = pickle.loads
    
    def _key(self, key: str) -> str:
        full_key = f"{self.prefix}{key}"
        if self.key_hash and len(full_key) > 250:
            hashed = hashlib.sha256(full_key.encode()).hexdigest()[:16]
            return f"{self.prefix}hash:{hashed}"
        return full_key
    
    def _get_client(self):
        """Get or create Redis client."""
        if self._client is None:
            import aioredis
            self._client = aioredis.from_url(
                self.url,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                retry_on_timeout=self.retry_on_timeout,
                db=self.db,
            )
        return self._client
    
    def _execute_with_retry(self, func, *args, **kwargs):
        """Execute Redis operation with retry logic."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise last_error
    
    # Sync interface (required by CacheBackend)
    def get(self, key: str) -> Optional[tuple[float, Any]]:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.async_get(key))
    
    def set(self, key: str, value: Any, ttl: float) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_set(key, value, ttl))
    
    def delete(self, key: str) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_delete(key))
    
    def clear(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_clear())
    
    def get_many(self, keys: List[str]) -> Dict[str, tuple[float, Any]]:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.async_get_many(keys))
    
    def set_many(self, items: Dict[str, Any], ttl: float) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_set_many(items, ttl))
    
    def delete_many(self, keys: List[str]) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_delete_many(keys))
    
    def keys(self) -> List[str]:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.async_keys())
    
    def health(self) -> dict:
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._get_client().ping())
            return {"status": "healthy", "type": "async-redis"}
        except Exception as e:
            return {"status": "unhealthy", "type": "async-redis", "error": str(e)}
    
    # Async interface
    async def async_get(self, key: str) -> Optional[tuple[float, Any]]:
        try:
            client = self._get_client()
            raw = await self._execute_with_retry(client.get, self._key(key))
            if raw:
                data = self._deserialize(raw)
                if self.compression:
                    return (data[0], self._deserialize(zlib.decompress(data[1])))
                return data
        except Exception:
            pass
        return None
    
    async def async_set(self, key: str, value: Any, ttl: float) -> None:
        expire_time = time.time() + ttl
        if self.compression:
            data = self._serialize((expire_time, zlib.compress(self._serialize(value), self.compression_level)))
        else:
            data = self._serialize((expire_time, value))
        client = self._get_client()
        await self._execute_with_retry(client.set, self._key(key), data, ex=int(ttl))
    
    async def async_delete(self, key: str) -> None:
        client = self._get_client()
        await self._execute_with_retry(client.delete, self._key(key))
    
    async def async_clear(self) -> None:
        client = self._get_client()
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor, match=f"{self.prefix}*", count=100)
            if keys:
                await self._execute_with_retry(client.delete, *keys)
            if cursor == 0:
                break
    
    async def async_get_many(self, keys: List[str]) -> Dict[str, tuple[float, Any]]:
        if not keys:
            return {}
        try:
            client = self._get_client()
            pipe = client.pipeline()
            for key in keys:
                pipe.get(self._key(key))
            results = {}
            for key, raw in zip(keys, await pipe.execute()):
                if raw:
                    results[key] = self._deserialize(raw)
            return results
        except Exception:
            return {}
    
    async def async_set_many(self, items: Dict[str, Any], ttl: float) -> None:
        if not items:
            return
        try:
            client = self._get_client()
            pipe = client.pipeline()
            for key, value in items.items():
                if self.compression:
                    data = self._serialize((time.time() + ttl, zlib.compress(self._serialize(value), self.compression_level)))
                else:
                    data = self._serialize((time.time() + ttl, value))
                pipe.set(self._key(key), data, ex=int(ttl))
            await self._execute_with_retry(pipe.execute)
        except Exception:
            pass
    
    async def async_delete_many(self, keys: List[str]) -> None:
        if not keys:
            return
        try:
            client = self._get_client()
            pipe = client.pipeline()
            for key in keys:
                pipe.delete(self._key(key))
            await self._execute_with_retry(pipe.execute)
        except Exception:
            pass
    
    async def async_keys(self) -> List[str]:
        prefix_len = len(self.prefix)
        result = []
        try:
            client = self._get_client()
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=f"{self.prefix}*", count=100)
                result.extend(k.decode()[prefix_len:] for k in keys)
                if cursor == 0:
                    break
        except Exception:
            pass
        return result
    
    async def async_health(self) -> dict:
        try:
            client = self._get_client()
            await client.ping()
            return {"status": "healthy", "type": "async-redis"}
        except Exception as e:
            return {"status": "unhealthy", "type": "async-redis", "error": str(e)}
    
    async def shutdown(self):
        """Graceful shutdown."""
        if self._client:
            await self._client.close()
