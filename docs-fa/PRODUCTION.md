# راهنمای استقرار در پروداکشن

## نمای کلی

این راهنما نحوه استقرار recall-cache در محیط پروداکشن را پوشش می‌دهد.

## پیش‌نیازها

- Python 3.11+
- Redis 7+ (اختیاری ولی توصیه شده)
- Docker 20.10+
- Kubernetes 1.25+

## معماری‌های استقرار

### سرور تکی

```
┌─────────────────────────────────────┐
│            Load Balancer            │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Application Server          │
│  ┌───────────────────────────────┐  │
│  │      recall-cache (Memory)    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### چند لایه با Redis

```
┌─────────────────────────────────────┐
│            Load Balancer            │
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

## پیکربندی

### متغیرهای محیطی

```bash
# نوع بک‌اند: memory, disk, redis, multi-tier
RECALL_BACKEND=multi-tier

# URL Redis
REDIS_URL=redis://localhost:6379

# تنظیمات حافظه
RECALL_MEMORY_MAXSIZE=10000
RECALL_MEMORY_COMPRESSION=true

# تنظیمات دیسک
RECALL_DISK_DIRECTORY=/var/cache/recall
RECALL_DISK_MAX_SIZE_GB=10
RECALL_DISK_ENCRYPTION_KEY=your-encryption-key

# تنظیمات چند لایه
RECALL_L1_MAXSIZE=5000
RECALL_L2_TTL=3600
RECALL_JITTER=true

# پنل ادمین
RECALL_ADMIN_ENABLED=true
RECALL_ADMIN_PORT=8080
RECALL_ADMIN_AUTH_TOKEN=your-secret-token

# مانیتورینگ
RECALL_METRICS_ENABLED=true
RECALL_METRICS_PORT=9090
RECALL_TRACING_ENABLED=true

# لاگینگ
RECALL_LOG_LEVEL=INFO
RECALL_LOG_FORMAT=json
```

## استقرار با Docker

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

## مانیتورینگ

### متریک‌های Prometheus

```
recall_cache_backend_status 1
recall_cache_keys_total 5000
recall_cache_operations_total 100000
recall_cache_errors_total 50
recall_cache_uptime_seconds 86400
```

## امنیت

- استفاده از TLS برای اتصالات Redis
- محدود کردن دسترسی به پنل ادمین
- استفاده از توکن‌های احراز هویت
- فعال کردن رمزنگاری برای بک‌اند دیسک

## پشتیبان‌گیری و بازیابی

```bash
# پشتیبان‌گیری روزانه
0 2 * * * recall-backup /var/cache/recall /backup/recall-$(date +\%Y\%m\%d).json

# بازیابی
recall-restore /backup/recall-20240101.json /var/cache/recall
```

## عیب‌یابی

### مشکلات رایج

1. **استفاده بالای حافظه**: کاهش `maxsize` یا فعال کردن فشرده‌سازی
2. **نرخ hit پایین**: افزایش TTL یا بررسی الگوهای کلید
3. **خطاهای اتصال Redis**: بررسی شبکه و سلامت Redis
4. **عملکرد کند**: فعال کردن محافظت stampede
