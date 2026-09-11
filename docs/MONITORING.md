# Monitoring & Alerting

## Overview

This document covers monitoring and alerting for recall-cache in production.

## Metrics

### Backend Metrics

```prometheus
# Backend status (1=healthy, 0=unhealthy)
recall_cache_backend_status

# Backend type
recall_cache_backend_type{type="memory"}

# Key count
recall_cache_keys_total

# Operations
recall_cache_operations_total
recall_cache_errors_total

# Uptime
recall_cache_uptime_seconds
```

### Application Metrics

```prometheus
# Cache hit rate
recall_cache_hit_rate

# Latency
recall_cache_latency_seconds{quantile="0.5"}
recall_cache_latency_seconds{quantile="0.95"}
recall_cache_latency_seconds{quantile="0.99"}

# Memory usage
recall_cache_memory_bytes

# Disk usage
recall_cache_disk_bytes
```

## Grafana Dashboard

Import the dashboard from `monitoring/grafana-dashboard.json`.

### Panels

1. **Backend Status** — Current backend health
2. **Key Count** — Number of cached keys
3. **Hit Rate** — Cache hit rate over time
4. **Operations** — Operations per second
5. **Latency** — P50, P95, P99 latency
6. **Memory Usage** — Memory consumption
7. **Error Rate** — Errors per second

## Alerting Rules

### Critical (P0)

```yaml
- alert: RecallCacheDown
  expr: recall_cache_backend_status == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "recall-cache is down"
    description: "recall-cache has been down for more than 5 minutes"
```

### Warning (P1)

```yaml
- alert: RecallCacheHighErrorRate
  expr: rate(recall_cache_errors_total[5m]) > 0.1
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High error rate in recall-cache"

- alert: RecallCacheLowHitRate
  expr: recall_cache_hit_rate < 0.5
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Low hit rate in recall-cache"

- alert: RecallCacheHighLatency
  expr: recall_cache_latency_seconds{quantile="0.99"} > 0.01
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High latency in recall-cache"
```

## Log Monitoring

### Error Patterns

| Pattern | Action |
|---------|--------|
| `Connection refused` | Check Redis connectivity |
| `Memory exceeded` | Reduce maxsize or enable compression |
| `Disk full` | Free up disk space |
| `Invalid key` | Check key format |

### Structured Logging

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "logger": "recall",
  "event": "cache_error",
  "error": "Connection refused",
  "key": "user:123"
}
```

## Health Checks

### Liveness Probe

```http
GET /health
```

Returns 200 if backend is healthy.

### Readiness Probe

```http
GET /ready
```

Returns 200 if backend can serve requests.
