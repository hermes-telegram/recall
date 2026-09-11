# Runbook for Operations

## Overview

This runbook covers operational procedures for recall-cache in production.

## Common Operations

### Check Cache Health

```bash
# Check backend status
curl http://localhost:8080/api/health

# Check metrics
curl http://localhost:8080/api/metrics

# Check keys
curl http://localhost:8080/api/keys
```

### Clear Cache

```bash
# Clear all cache
curl -X DELETE http://localhost:8080/api/cache

# Clear specific key
curl -X DELETE http://localhost:8080/api/cache/my-key
```

### Backup

```bash
# Create backup
recall-backup /var/cache/recall /backup/recall-$(date +%Y%m%d).json

# Restore from backup
recall-restore /backup/recall-20240101.json /var/cache/recall
```

## Troubleshooting

### High Memory Usage

**Symptoms**: OOM kills, slow performance

**Diagnosis**:
```bash
# Check memory usage
curl http://localhost:8080/api/stats | grep memory

# Check key count
curl http://localhost:8080/api/keys
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
# Check hit rate
curl http://localhost:8080/api/stats | grep hit_rate

# Check key patterns
curl http://localhost:8080/api/keys
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
# Check Redis health
redis-cli ping

# Check Redis info
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
# Check disk space
df -h /var/cache/recall

# Check permissions
ls -la /var/cache/recall
```

**Resolution**:
1. Free up disk space
2. Check file permissions
3. Verify encryption key
4. Check for corrupted files

## Emergency Procedures

### Complete Cache Failure

1. **Enable stale data mode** (if configured)
2. **Scale up database** to handle direct load
3. **Restart cache backends**
4. **Gradually re-enable cache**

### Data Corruption

1. **Stop all writes** to cache
2. **Backup current state**
3. **Clear corrupted keys**
4. **Restore from backup**
5. **Verify data integrity**

### Security Breach

1. **Rotate all credentials**
2. **Enable audit logging**
3. **Review access logs**
4. **Patch vulnerabilities**
5. **Notify stakeholders**

## Escalation

| Issue | Contact | Response |
|-------|---------|----------|
| P0 (Critical) | oncall@recall-cache.dev | 15 min |
| P1 (High) | oncall@recall-cache.dev | 30 min |
| P2 (Medium) | support@recall-cache.dev | 2 hours |
| P3 (Low) | support@recall-cache.dev | 1 business day |
