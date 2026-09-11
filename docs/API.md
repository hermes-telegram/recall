# API Reference

## `cache()`

```python
from recall import cache

@cache(
    ttl="1h",
    maxsize=1000,
    backend=None,
    key_fn=None,
    prefix="",
    sliding=False,
    version=None,
    on_evict=None,
    compression=False,
    stampede_protection=False,
    background_refresh=None,
    serializer="pickle",
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ttl` | `str \| float` | `"1h"` | Time-to-live: `"30s"`, `"5m"`, `"1h"`, `"1d"`, `"1w"`, or seconds |
| `maxsize` | `int` | `1000` | Max items (MemoryBackend only) |
| `backend` | `CacheBackend` | `None` | Custom backend (MemoryBackend, DiskBackend, RedisBackend) |
| `key_fn` | `Callable` | `None` | Custom key function `f(func, args, kwargs) -> str` |
| `prefix` | `str` | `""` | Key prefix for namespacing |
| `sliding` | `bool` | `False` | Reset TTL on each access |
| `version` | `str` | `None` | Cache version (change to invalidate) |
| `on_evict` | `Callable` | `None` | Callback `f(key, value)` on eviction |
| `compression` | `bool` | `False` | Compress values with zlib |
| `stampede_protection` | `bool` | `False` | Prevent cache stampede |
| `background_refresh` | `float` | `None` | Seconds before expiry to trigger refresh |
| `serializer` | `str` | `"pickle"` | Serialization: `"pickle"`, `"json"`, `"msgpack"` |

### Attached Methods

| Method | Description |
|--------|-------------|
| `.cache_clear()` | Clear all cached values |
| `.cache_delete(*args, **kwargs)` | Delete specific key |
| `.cache_get(*args, **kwargs)` | Get value without computing |
| `.cache_set(value, *args, **kwargs)` | Set value manually |
| `.cache_warm(args_list)` | Pre-populate cache |
| `.cache_stats` | Get CacheStats object |
| `.cache_keys()` | Get all keys |
| `.cache_health()` | Backend health check |
| `.cache_get_many(keys)` | Get multiple keys |
| `.cache_set_many(items, ttl)` | Set multiple keys |
| `.cache_delete_many(keys)` | Delete multiple keys |
| `.cache_backend` | Access the backend instance |

---

## `CacheStats`

```python
stats = my_func.cache_stats
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `.hits` | `int` | Number of cache hits |
| `.misses` | `int` | Number of cache misses |
| `.total` | `int` | Total lookups |
| `.hit_rate` | `float` | Hit rate (0.0 to 1.0) |

### Methods

| Method | Description |
|--------|-------------|
| `.reset()` | Reset all counters |
| `.to_dict()` | Return stats as dictionary |

---

## Backends

### `MemoryBackend`

```python
from recall import MemoryBackend

backend = MemoryBackend(
    maxsize=1000,
    compression=False,
)
```

### `DiskBackend`

```python
from recall import DiskBackend

backend = DiskBackend(
    directory=".recall_cache",
    compression=False,
    max_size_bytes=None,
)
```

### `RedisBackend`

```python
from recall import RedisBackend

backend = RedisBackend(
    url="redis://localhost:6379",
    prefix="recall:",
    compression=False,
)
```

---

## CacheBackend Interface

```python
class CacheBackend(ABC):
    def get(self, key: str) -> Optional[tuple[float, Any]]: ...
    def set(self, key: str, value: Any, ttl: float) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...
    def get_many(self, keys: List[str]) -> Dict[str, tuple[float, Any]]: ...
    def set_many(self, items: Dict[str, Any], ttl: float) -> None: ...
    def delete_many(self, keys: List[str]) -> None: ...
    def keys(self) -> List[str]: ...
    def health(self) -> dict: ...
```

---

## Exceptions

| Exception | Description |
|-----------|-------------|
| `CacheError` | Base exception for cache errors |
| `BackendError` | Backend-specific error |
