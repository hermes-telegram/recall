# Production Deployment Guide

## Overview

This guide covers deploying recall-cache in production environments.

## Prerequisites

- Python 3.11+
- Redis 7+ (optional but recommended)
- Docker 20.10+ (for containerized deployment)
- Kubernetes 1.25+ (for orchestrated deployment)

## Deployment Architectures

### Single Server

```
┌─────────────────────────────────────┐
│           Load Balancer             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Application Server          │
│  ┌───────────────────────────────┐  │
│  │      recall-cache (Memory)    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Multi-Tier with Redis

```
┌─────────────────────────────────────┐
│           Load Balancer             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Application Server          │
│  ┌───────────────────────────────┐  │
│  │      recall-cache (L1: Memory)│  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Redis Cluster (L2)          │
└─────────────────────────────────────┘
```

### Kubernetes Deployment

```
┌─────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                   │
│  ┌─────────────────────────────────────────────────┐    │
│  │                 Ingress Controller               │    │
│  └─────────────────────┬───────────────────────────┘    │
│                        │                                │
│  ┌─────────────────────▼───────────────────────────┐    │
│  │              Application Pods (HPA)              │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────┐  │    │
│  │  │  Pod 1      │ │  Pod 2      │ │  Pod N   │  │    │
│  │  │  (Memory L1)│ │  (Memory L1)│ │ (Memory) │  │    │
│  │  └─────────────┘ └─────────────┘ └──────────┘  │    │
│  └─────────────────────┬───────────────────────────┘    │
│                        │                                │
│  ┌─────────────────────▼───────────────────────────┐    │
│  │              Redis StatefulSet                   │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────┐  │    │
│  │  │  Redis 1    │ │  Redis 2    │ │  Redis N │  │    │
│  │  └─────────────┘ └─────────────┘ └──────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

```bash
# Backend type: memory, disk, redis, multi-tier
RECALL_BACKEND=multi-tier

# Redis URL (when using Redis backend)
REDIS_URL=redis://localhost:6379

# Memory backend settings
RECALL_MEMORY_MAXSIZE=10000
RECALL_MEMORY_COMPRESSION=true

# Disk backend settings
RECALL_DISK_DIRECTORY=/var/cache/recall
RECALL_DISK_MAX_SIZE_GB=10
RECALL_DISK_ENCRYPTION_KEY=your-encryption-key

# Multi-tier settings
RECALL_L1_MAXSIZE=5000
RECALL_L2_TTL=3600
RECALL_JITTER=true

# Admin panel
RECALL_ADMIN_ENABLED=true
RECALL_ADMIN_PORT=8080
RECALL_ADMIN_AUTH_TOKEN=your-secret-token

# Monitoring
RECALL_METRICS_ENABLED=true
RECALL_METRICS_PORT=9090
RECALL_TRACING_ENABLED=true

# Logging
RECALL_LOG_LEVEL=INFO
RECALL_LOG_FORMAT=json
```

### Django Settings

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'recall.plugins.django_plugin.RecallCache',
        'LOCATION': 'recall-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
            'CULL_FREQUENCY': 3,
        }
    }
}

# recall-cache settings
RECALL_CONFIG = {
    'backend': 'multi-tier',
    'redis_url': 'redis://localhost:6379',
    'memory_maxsize': 5000,
    'admin_enabled': True,
    'admin_port': 8080,
    'metrics_enabled': True,
}
```

### FastAPI Settings

```python
# config.py
from recall import MultiTierBackend, MemoryBackend, RedisBackend

backend = MultiTierBackend(
    l1=MemoryBackend(maxsize=5000),
    l2=RedisBackend("redis://localhost:6379"),
    jitter=True,
)

# Enable admin panel
from recall.admin import AdminPanel
panel = AdminPanel(backend, port=8080, auth_token="secret")
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e ".[redis]"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "recall.admin"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379
      - RECALL_ADMIN_ENABLED=true
      - RECALL_ADMIN_AUTH_TOKEN=secret
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  redis_data:
```

## Kubernetes Deployment

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: recall-cache
spec:
  replicas: 3
  selector:
    matchLabels:
      app: recall-cache
  template:
    metadata:
      labels:
        app: recall-cache
    spec:
      containers:
      - name: recall-cache
        image: recall-cache:latest
        ports:
        - containerPort: 8080
        env:
        - name: REDIS_URL
          value: "redis://redis:6379"
        - name: RECALL_ADMIN_ENABLED
          value: "true"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: recall-cache
spec:
  selector:
    app: recall-cache
  ports:
  - port: 8080
    targetPort: 8080
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: recall-cache
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: recall-cache
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Monitoring

### Prometheus Metrics

```
# Backend status
recall_cache_backend_status 1

# Key count
recall_cache_keys_total 5000

# Operations
recall_cache_operations_total 100000
recall_cache_errors_total 50

# Uptime
recall_cache_uptime_seconds 86400
```

### Grafana Dashboard

Import the provided dashboard from `monitoring/grafana-dashboard.json`.

### Alerting Rules

```yaml
groups:
- name: recall-cache
  rules:
  - alert: RecallCacheDown
    expr: recall_cache_backend_status == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "recall-cache is down"
      
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
```

## Security

### Network Security

- Use TLS for Redis connections
- Restrict admin panel access with firewall
- Use authentication tokens for admin panel
- Enable encryption for disk backend

### Authentication

```python
from recall.admin import AdminPanel

panel = AdminPanel(
    backend=backend,
    port=8080,
    auth_token="your-secret-token",  # Use strong token
)
```

### Encryption

```python
from recall import DiskBackend

backend = DiskBackend(
    directory="/var/cache/recall",
    encryption_key="your-256-bit-key",  # Use strong key
)
```

## Backup & Recovery

### Automated Backups

```bash
# Daily backup
0 2 * * * recall-backup /var/cache/recall /backup/recall-$(date +\%Y\%m\%d).json
```

### Recovery

```bash
# Restore from backup
recall-restore /backup/recall-20240101.json /var/cache/recall
```

## Troubleshooting

### Common Issues

1. **High memory usage**: Reduce `maxsize` or enable compression
2. **Low hit rate**: Increase TTL or check key patterns
3. **Redis connection errors**: Check network and Redis health
4. **Slow performance**: Enable stampede protection

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

- GitHub Issues: https://github.com/hermes-telegram/recall/issues
- Documentation: https://recall-cache.readthedocs.io
- Email: support@recall-cache.dev
