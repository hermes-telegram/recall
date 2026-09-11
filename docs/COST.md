# Cost Analysis

## Overview

This document analyzes the cost of running recall-cache in production.

## Infrastructure Costs

### Single Server (Small)

| Resource | Monthly Cost |
|----------|--------------|
| 1x Application Server (2 vCPU, 4GB RAM) | $40 |
| 1x Redis (1GB) | $25 |
| Storage (10GB SSD) | $10 |
| **Total** | **$75/month** |

### Medium Deployment

| Resource | Monthly Cost |
|----------|--------------|
| 3x Application Server (4 vCPU, 8GB RAM) | $300 |
| 3x Redis (4GB, HA) | $200 |
| Storage (100GB SSD) | $50 |
| Load Balancer | $25 |
| **Total** | **$575/month** |

### Large Deployment

| Resource | Monthly Cost |
|----------|--------------|
| 10x Application Server (8 vCPU, 16GB RAM) | $1,500 |
| 6x Redis (16GB, Cluster) | $1,200 |
| Storage (1TB SSD) | $200 |
| Load Balancer | $100 |
| Monitoring | $100 |
| **Total** | **$3,100/month** |

## Cost Per Operation

| Metric | Cost |
|--------|------|
| Cache Hit | $0.00001 |
| Cache Miss | $0.001 |
| DB Query (avoided) | $0.01 |

## ROI Analysis

| Scenario | Without Cache | With Cache | Savings |
|----------|---------------|------------|---------|
| 1M requests/day | $300/month | $75/month | 75% |
| 10M requests/day | $3,000/month | $575/month | 81% |
| 100M requests/day | $30,000/month | $3,100/month | 90% |

## Optimization Tips

1. **Enable compression** — reduces memory usage by 50-80%
2. **Use appropriate TTL** — balance freshness vs cache hits
3. **Monitor hit rate** — aim for >90%
4. **Use multi-tier** — reduce Redis costs
