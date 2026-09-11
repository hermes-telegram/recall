# Troubleshooting Guide

## Common Issues

### High Memory Usage

**Symptoms**: OOM kills, slow performance

**Diagnosis**:
```bash
curl http://localhost:8080/api/stats
```

**Resolution**:
1. Reduce `maxsize` in MemoryBackend
2. Enable compression
3. Reduce TTL values
4. Clear cache if needed

### Low Hit Rate

**Symptoms**: High database load, slow responses

**Diagnosis**:
```bash
curl http://localhost:8080/api/stats | grep hit_rate
```

**Resolution**:
1. Increase TTL values
2. Check key patterns for uniqueness
3. Enable cache warming
4. Review cache invalidation logic

### Redis Connection Errors

**Symptoms**: Connection timeouts, high latency

**Diagnosis**:
```bash
redis-cli ping
redis-cli info
```

**Resolution**:
1. Check network connectivity
2. Verify Redis is running
3. Check Redis memory usage
4. Review connection pool settings

### Disk Backend Errors

**Symptoms**: Write failures, read errors

**Diagnosis**:
```bash
df -h /var/cache/recall
ls -la /var/cache/recall
```

**Resolution**:
1. Free up disk space
2. Check file permissions
3. Verify encryption key
4. Check for corrupted files

## Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Getting Help

- GitHub Issues: https://github.com/hermes-telegram/recall/issues
- Documentation: https://recall-cache.readthedocs.io
- Email: support@recall-cache.dev
