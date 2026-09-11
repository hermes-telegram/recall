# Tutorials & Examples

## Basic Usage

### Simple Caching

```python
from recall import cache

@cache(ttl="1h")
def get_user(user_id):
    return db.query(user_id)

# First call: fetches from database
user = get_user(1)

# Second call: returns from cache (instant)
user = get_user(1)
```

### Cache with Custom Key

```python
from recall import cache

@cache(ttl="5m", key_fn=lambda user_id: f"user:{user_id}")
def get_user(user_id):
    return db.query(user_id)
```

### Cache with Condition

```python
from recall import cache

@cache(ttl="1h", condition=lambda result: result is not None)
def get_user(user_id):
    return db.query(user_id)  # Only caches if result is not None
```

## Advanced Usage

### Multi-Tier Caching

```python
from recall import cache, MultiTierBackend, MemoryBackend, RedisBackend

backend = MultiTierBackend(
    l1=MemoryBackend(maxsize=1000),
    l2=RedisBackend("redis://localhost:6379"),
    jitter=True,
)

@cache(ttl="1h", backend=backend)
def get_user(user_id):
    return db.query(user_id)
```

### Cache Warming

```python
from recall import cache, MemoryBackend

backend = MemoryBackend()

@cache(ttl="1h", backend=backend)
def get_user(user_id):
    return db.query(user_id)

# Pre-populate cache
get_user.cache_warm([(1,), (2,), (3,)])
```

### Cache Invalidation

```python
from recall import cache

@cache(ttl="1h")
def get_user(user_id):
    return db.query(user_id)

# Delete specific key
get_user.cache_delete(1)

# Clear all cache
get_user.cache_clear()
```

### Cache Statistics

```python
from recall import cache

@cache(ttl="1h")
def get_user(user_id):
    return db.query(user_id)

# Get stats
stats = get_user.cache_stats
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Hit Rate: {stats.hit_rate:.2%}")
```

## Integration Examples

### Django Integration

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'recall.plugins.django_plugin.RecallCache',
        'LOCATION': 'recall-cache',
    }
}

# views.py
from django.core.cache import cache

@cache(ttl="5m", prefix="user")
def get_user(user_id):
    return User.objects.get(id=user_id)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from recall import cache, MemoryBackend
from recall.plugins import FastAPICache

app = FastAPI()
cache = FastAPICache(app, backend=MemoryBackend())

@app.get("/users/{user_id}")
@cache.route(ttl="5m")
def get_user(user_id: int):
    return {"user": user_id}
```

### Flask Integration

```python
from flask import Flask
from recall import cache, MemoryBackend

app = Flask(__name__)
backend = MemoryBackend()

@app.route("/users/<int:user_id>")
@cache(ttl="5m", backend=backend)
def get_user(user_id):
    return {"user": user_id}
```

## Enterprise Patterns

### Request Coalescing

```python
from recall.advanced import RequestCoalescer

coalescer = RequestCoalescer()

@coalescer.coalesce
def fetch_user(user_id):
    return db.query(user_id)
```

### Graceful Degradation

```python
from recall.advanced import GracefulDegradation

gd = GracefulDegradation(backend, stale_ttl=3600)

@gd.resilient(ttl="1h")
def get_user(user_id):
    return db.query(user_id)
```

### Adaptive TTL

```python
from recall.advanced import AdaptiveTTL

adaptive = AdaptiveTTL(backend, min_ttl=60, max_ttl=3600)

@adaptive.cached(target_hit_rate=0.8)
def fetch_data(key):
    return expensive_query(key)
```

## Testing

### Unit Testing

```python
import pytest
from recall import cache, MemoryBackend

def test_cache_hit():
    backend = MemoryBackend()
    
    @cache(ttl="1h", backend=backend)
    def func(x):
        return x * 2
    
    assert func(5) == 10
    assert func(5) == 10  # From cache
    assert func.cache_stats.hits == 1
```

### Integration Testing

```python
import pytest
from recall import cache, RedisBackend

def test_redis_backend():
    backend = RedisBackend("redis://localhost:6379")
    
    @cache(ttl="1h", backend=backend)
    def func(x):
        return x * 2
    
    assert func(5) == 10
```

## Best Practices

1. **Use appropriate TTL** — Balance freshness vs cache hits
2. **Enable compression** — For large values
3. **Use multi-tier** — For production workloads
4. **Monitor hit rate** — Aim for >90%
5. **Use cache warming** — For predictable workloads
6. **Enable stampede protection** — For high-traffic endpoints
7. **Use conditional caching** — To avoid caching errors
