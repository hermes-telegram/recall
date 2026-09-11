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
    compression_level=6,
    stampede_protection=False,
    background_refresh=None,
    serializer="pickle",
    jitter=False,
    jitter_max_percent=10,
    condition=None,
    admin=False,
    rate_limit=False,
    rate_limit_max=100,
    rate_limit_window=60,
    circuit_breaker=False,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=30,
    audit=False,
    trace=False,
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
| `compression_level` | `int` | `6` | Compression level (1-9) |
| `stampede_protection` | `bool` | `False` | Prevent cache stampede |
| `background_refresh` | `float` | `None` | Seconds before expiry to trigger refresh |
| `serializer` | `str` | `"pickle"` | Serialization: `"pickle"`, `"json"`, `"msgpack"` |
| `jitter` | `bool` | `False` | Enable TTL jitter |
| `jitter_max_percent` | `int` | `10` | Max jitter percentage |
| `condition` | `Callable` | `None` | Conditional caching `f(result) -> bool` |
| `admin` | `bool` | `False` | Enable admin panel |
| `rate_limit` | `bool` | `False` | Enable rate limiting |
| `rate_limit_max` | `int` | `100` | Max requests per window |
| `rate_limit_window` | `float` | `60` | Rate limit window in seconds |
| `circuit_breaker` | `bool` | `False` | Enable circuit breaker |
| `circuit_breaker_threshold` | `int` | `5` | Failure threshold |
| `circuit_breaker_timeout` | `float` | `30` | Recovery timeout |
| `audit` | `bool` | `False` | Enable audit logging |
| `trace` | `bool` | `False` | Enable distributed tracing |

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
| `.cache_ttl(key)` | Get remaining TTL |
| `.cache_touch(key, ttl)` | Update TTL |
| `.cache_exists(key)` | Check if key exists |

---

## Backends

### `MemoryBackend`

```python
from recall import MemoryBackend

backend = MemoryBackend(
    maxsize=1000,
    compression=False,
    compression_level=6,
)
```

### `DiskBackend`

```python
from recall import DiskBackend

backend = DiskBackend(
    directory=".recall_cache",
    compression=False,
    compression_level=6,
    max_size_bytes=None,
    encryption_key=None,
    cleanup_interval=60,
)
```

### `RedisBackend`

```python
from recall import RedisBackend

backend = RedisBackend(
    url="redis://localhost:6379",
    prefix="recall:",
    compression=False,
    compression_level=6,
    max_connections=10,
    socket_timeout=5.0,
    retry_on_timeout=True,
    max_retries=3,
    serializer="pickle",
    key_hash=False,
    db=0,
)
```

### `MultiTierBackend`

```python
from recall import MultiTierBackend, MemoryBackend, RedisBackend

backend = MultiTierBackend(
    l1=MemoryBackend(),
    l2=RedisBackend(),
    jitter=True,
    jitter_max_percent=10,
)
```

---

## Admin Panel

```python
from recall import AdminPanel

panel = AdminPanel(
    backend=backend,
    port=8080,
    host="0.0.0.0",
    auth_token="secret",
    enable_metrics=True,
    enable_audit=True,
)
panel.start()
```

---

## Rate Limiter

```python
from recall import RateLimiter

limiter = RateLimiter(max_requests=100, window=60.0)

if limiter.allow():
    # proceed
    pass
```

---

## Circuit Breaker

```python
from recall import CircuitBreaker

cb = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30.0,
)

@cb
def cache_operation():
    return backend.get("key")
```

---

## Audit Logger

```python
from recall import AuditLogger

audit = AuditLogger()
audit.log("cache_clear", user="admin", details="Cleared all cache")
entries = audit.get_entries(limit=100)
```

---

## Key Searcher

```python
from recall import KeySearcher

searcher = KeySearcher(backend)
keys = searcher.search("user:*")
keys = searcher.search_contains("123")
keys = searcher.search_by_prefix("user:")
```

---

## GDPR Manager

```python
from recall import GDPRManager

gdpr = GDPRManager(backend)
gdpr.track_user("user123", ["user:123:profile", "user:123:posts"])
deleted = gdpr.forget_user("user123")
```

---

## Backup Manager

```python
from recall import BackupManager

backup = BackupManager(backend)
backup.backup_to_file("/tmp/backup.json")
backup.restore_from_file("/tmp/backup.json")
```

---

## Cache Stats

```python
stats = my_func.cache_stats
print(stats.hits)       # Number of hits
print(stats.misses)     # Number of misses
print(stats.total)      # Total lookups
print(stats.hit_rate)   # Hit rate (0.0 to 1.0)
stats.reset()           # Reset counters
```

---

## Exceptions

| Exception | Description |
|-----------|-------------|
| `CacheError` | Base exception for cache errors |
| `BackendError` | Backend-specific error |
| `CircuitBreakerOpenError` | Circuit breaker is open |
| `RateLimitExceededError` | Rate limit exceeded |
