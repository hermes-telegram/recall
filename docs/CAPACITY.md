# Capacity Planning

## Overview

This document provides guidelines for capacity planning with recall-cache.

## Memory Backend

### Per-Key Memory Usage

| Data Type | Average Size |
|-----------|--------------|
| Small string (<100 chars) | 200 bytes |
| Medium string (<1KB) | 1.2 KB |
| Large string (<100KB) | 100 KB |
| Integer | 100 bytes |
| List (100 items) | 5 KB |
| Dict (100 keys) | 10 KB |

### Maxsize Recommendations

| Available RAM | Recommended Maxsize |
|---------------|---------------------|
| 512 MB | 5,000 |
| 1 GB | 10,000 |
| 2 GB | 25,000 |
| 4 GB | 50,000 |
| 8 GB | 100,000 |

## Disk Backend

### Per-Key Disk Usage

| Data Type | Average Size |
|-----------|--------------|
| Small string (<100 chars) | 300 bytes |
| Medium string (<1KB) | 1.5 KB |
| Large string (<100KB) | 100 KB |

### Max Size Recommendations

| Available Disk | Recommended Max |
|----------------|-----------------|
| 1 GB | 500,000 keys |
| 10 GB | 5,000,000 keys |
| 100 GB | 50,000,000 keys |

## Redis Backend

### Memory Usage

| Data Type | Average Size |
|-----------|--------------|
| Small string (<100 chars) | 150 bytes |
| Medium string (<1KB) | 1 KB |
| Large string (<100KB) | 100 KB |

### Connection Pool

| Concurrent Requests | Recommended Pool Size |
|---------------------|----------------------|
| <100 | 10 |
| 100-1000 | 50 |
| 1000-10000 | 100 |
| >10000 | 200 |

## Scaling Guidelines

### Vertical Scaling

- Increase `maxsize` for MemoryBackend
- Increase `max_size_bytes` for DiskBackend
- Increase `max_connections` for RedisBackend

### Horizontal Scaling

- Add more application servers
- Use Redis Cluster for L2
- Implement consistent hashing

## Monitoring

Key metrics to monitor:

- Memory usage
- Disk usage
- Key count
- Hit rate
- Error rate
- Latency (P50, P95, P99)
