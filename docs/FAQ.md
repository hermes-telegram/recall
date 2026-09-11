# Frequently Asked Questions

## General

### What is recall-cache?

recall-cache is a Python caching library that provides a simple API for caching function results with TTL (time-to-live) support. It supports multiple backends including Memory, Disk, and Redis.

### How is it different from functools.lru_cache?

`functools.lru_cache` has no TTL support and no persistence. recall-cache provides TTL, disk persistence, Redis backend, and many enterprise features.

### How is it different from cachetools?

cachetools has a complex API and no disk/Redis backend. recall-cache provides a simpler API with real backends and TTL done right.

## Usage

### How do I enable caching?

```python
from recall import cache

@cache(ttl="1h")
def my_func(x):
    return x * 2
```

### How do I clear the cache?

```python
# Clear all cache
my_func.cache_clear()

# Delete specific key
my_func.cache_delete(42)
```

### How do I get cache statistics?

```python
stats = my_func.cache_stats
print(f"Hit rate: {stats.hit_rate:.2%}")
```

## Backends

### Which backend should I use?

- **Memory**: Fastest, but data is lost on restart
- **Disk**: Persistent, but slower than memory
- **Redis**: Persistent, shared across processes
- **Multi-tier**: Combines Memory + Redis for best performance

### How do I use Redis?

```python
from recall import cache, RedisBackend

backend = RedisBackend("redis://localhost:6379")
@cache(ttl="1h", backend=backend)
def my_func(x):
    return x * 2
```

## Performance

### What is the performance overhead?

recall-cache adds <1μs overhead for cache hits and <10μs for cache misses (Memory backend).

### How do I improve performance?

1. Enable compression for large values
2. Use multi-tier caching
3. Enable stampede protection
4. Use appropriate TTL values

## Production

### Is recall-cache production-ready?

Yes, recall-cache v3.1.0 is production-ready with comprehensive features for enterprise use.

### How do I deploy in production?

See the [Production Deployment Guide](PRODUCTION.md).

### How do I monitor recall-cache?

Use Prometheus metrics and Grafana dashboards. See the [Monitoring Guide](MONITORING.md).

## Troubleshooting

### High memory usage

Reduce `maxsize` or enable compression.

### Low hit rate

Increase TTL or check key patterns for uniqueness.

### Redis connection errors

Check network connectivity and Redis health.

## Support

### How do I get support?

- Community: GitHub Issues
- Business: support@recall-cache.dev
- Enterprise: 24/7 phone support

### How do I report a bug?

Open an issue on GitHub with a minimal reproduction case.

### How do I request a feature?

Open an issue on GitHub with the "feature request" label.
