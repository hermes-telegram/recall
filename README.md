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

# Custom key function
@cache(ttl="1h", key_fn=lambda f, a, k: f"{a}_{k.get('mode', '')}")
def custom(data, mode):
    return f"{data}_{mode}"
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
# trigger

# trigger
