# recall

Smart caching for any function — simple as requests.

```python
from recall import cache

@cache(ttl="1h")
def get_user(user_id):
    return db.query(user_id)
```

## Features

- **Simple API** — just `@cache(ttl="1h")` on any function
- **Multiple backends** — Memory, Disk, Redis
- **TTL shorthand** — `"30m"`, `"1h"`, `"7d"` instead of raw seconds
- **LRU eviction** — automatic cleanup when maxsize is reached
- **Thread-safe** — works in concurrent environments
- **Async support** — full async/await compatibility
- **Cache statistics** — track hit/miss rates
- **Stampede protection** — prevent cache stampede
- **Background refresh** — auto-refresh before expiry
- **Compression** — zlib compression for large values
- **Bulk operations** — get_many, set_many, delete_many
- **Serialization** — pickle, JSON, msgpack
- **Namespacing** — key prefix and versioning
- **Cache warming** — pre-populate cache
- **Sliding TTL** — reset TTL on each access
- **Zero dependencies** — Redis backend optional

## Install

```bash
pip install recall
# With Redis support:
pip install recall[redis]
```

## Quick Start

```python
from recall import cache
import time

@cache(ttl="1h", maxsize=1000)
def expensive_func(x):
    time.sleep(2)
    return x * 2

# First call: computes
result = expensive_func(5)  # takes 2 seconds

# Second call: instant (from cache)
result = expensive_func(5)  # returns immediately
```

## Backends

### Memory (default)

```python
@cache(ttl="1h", maxsize=1000)
def func(x):
    return x * 2
```

### Disk (persistent)

```python
from recall import DiskBackend

@cache(ttl="1h", backend=DiskBackend("/tmp/my_cache"))
def func(x):
    return x * 2
```

### Redis

```python
from recall import RedisBackend

@cache(ttl="1h", backend=RedisBackend("redis://localhost:6379"))
def func(x):
    return x * 2
```

## Cache Management

```python
# Clear all cached values
expensive_func.cache_clear()

# Delete specific key
expensive_func.cache_delete(42)

# Get without computing
result = expensive_func.cache_get(42)

# Set manually
expensive_func.cache_set(99, 42)

# Pre-populate cache
expensive_func.cache_warm([(1,), (2,), (3,)])

# Get cache statistics
stats = expensive_func.cache_stats
print(stats.hits, stats.misses, stats.hit_rate)

# Get all keys
keys = expensive_func.cache_keys()

# Backend health check
health = expensive_func.cache_health()
```

## Bulk Operations

```python
# Get multiple keys
results = expensive_func.cache_get_many(["key1", "key2"])

# Set multiple keys
expensive_func.cache_set_many({"key1": 1, "key2": 2})

# Delete multiple keys
expensive_func.cache_delete_many(["key1", "key2"])
```

## Advanced Features

### Sliding TTL (reset on access)

```python
@cache(ttl="5m", sliding=True)
def get_session(session_id):
    return db.query(session_id)
```

### Cache Versioning

```python
@cache(ttl="1h", version="2")  # Change to invalidate all
def get_data(key):
    return fetch(key)
```

### Stampede Protection

```python
@cache(ttl="1h", stampede_protection=True)
def expensive_computation(x):
    return x ** x
```

### Background Refresh

```python
@cache(ttl="1h", background_refresh=300)  # Refresh 5min before expiry
def get_config():
    return fetch_config()
```

### Compression

```python
@cache(ttl="1h", compression=True)
def get_large_data():
    return list(range(100000))
```

### Custom Key Function

```python
@cache(ttl="1h", key_fn=lambda f, a, k: f"{a[0]}_{k.get('mode', '')}")
def process(data, mode="default"):
    return f"{data}_{mode}"
```

### Key Prefix (Namespacing)

```python
@cache(ttl="1h", prefix="myapp")
def get_user(user_id):
    return db.query(user_id)
```

### Serialization Format

```python
@cache(ttl="1h", serializer="json")  # pickle, json, msgpack
def get_data():
    return {"key": "value"}
```

## Async Support

```python
@cache(ttl="1h")
async def get_user_async(user_id):
    return await db.query(user_id)

# Works with async functions
result = await get_user_async(1)

# Cache warming in async
await get_user_async.cache_warm([(1,), (2,)])
```

## TTL Formats

| Shorthand | Meaning |
|-----------|---------|
| `"30s"` | 30 seconds |
| `"5m"` | 5 minutes |
| `"1h"` | 1 hour |
| `"1d"` | 1 day |
| `"1w"` | 1 week |
| `3600` | raw seconds (int/float) |

## Why recall?

| Tool | Issue |
|------|-------|
| `functools.lru_cache` | No TTL, no persistence |
| `cachetools` | Complex API, no disk/Redis |
| `redis` alone | Manual key management |
| `dogpile.cache` | Overkill for simple use |

**recall** = simple API + real backends + TTL done right.

## License

MIT
