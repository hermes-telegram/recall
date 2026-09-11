# مانیتورینگ و هشدار

## نمای کلی

این سند مانیتورینگ و هشدار برای recall-cache در پروداکشن را پوشش می‌دهد.

## متریک‌ها

### متریک‌های بک‌اند

```prometheus
# وضعیت بک‌اند (۱=سالم، ۰=خراب)
recall_cache_backend_status

# نوع بک‌اند
recall_cache_backend_type{type="memory"}

# تعداد کلیدها
recall_cache_keys_total

# عملیات
recall_cache_operations_total
recall_cache_errors_total

# Uptime
recall_cache_uptime_seconds
```

### متریک‌های برنامه

```prometheus
# نرخ hit
recall_cache_hit_rate

# تأخیر
recall_cache_latency_seconds{quantile="0.5"}
recall_cache_latency_seconds{quantile="0.95"}
recall_cache_latency_seconds{quantile="0.99"}

# مصرف حافظه
recall_cache_memory_bytes

# مصرف دیسک
recall_cache_disk_bytes
```

## داشبورد Grafana

داشبورد را از `monitoring/grafana-dashboard.json` وارد کنید.

### پنل‌ها

1. **وضعیت بک‌اند** — سلامت فعلی بک‌اند
2. **تعداد کلیدها** — تعداد کلیدهای کش شده
3. **نرخ Hit** — نرخ hit در طول زمان
4. **عملیات** — عملیات در ثانیه
5. **تأخیر** — تأخیر P50، P95، P99
6. **مصرف حافظه** — مصرف حافظه
7. **نرخ خطا** — خطا در ثانیه

## قوانین هشدار

### حیاتی (P0)

```yaml
- alert: RecallCacheDown
  expr: recall_cache_backend_status == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "recall-cache خراب است"
    description: "recall-cache بیش از ۵ دقیقه خراب است"
```

### هشدار (P1)

```yaml
- alert: RecallCacheHighErrorRate
  expr: rate(recall_cache_errors_total[5m]) > 0.1
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "نرخ خطای بالا در recall-cache"

- alert: RecallCacheLowHitRate
  expr: recall_cache_hit_rate < 0.5
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "نرخ hit پایین در recall-cache"

- alert: RecallCacheHighLatency
  expr: recall_cache_latency_seconds{quantile="0.99"} > 0.01
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "تأخیر بالا در recall-cache"
```

## مانیتورینگ لاگ

### الگوهای خطا

| الگو | اقدام |
|------|--------|
| `Connection refused` | بررسی اتصال Redis |
| `Memory exceeded` | کاهش maxsize یا فعال کردن فشرده‌سازی |
| `Disk full` | آزاد کردن فضای دیسک |
| `Invalid key` | بررسی فرمت کلید |

### لاگینگ ساختاریافته

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

## بررسی‌های سلامت

### Liveness Probe

```http
GET /health
```

۲۰۰ برمی‌گرداند اگر بک‌اند سالم باشد.

### Readiness Probe

```http
GET /ready
```

۲۰۰ برمی‌گرداند اگر بک‌اند بتواند درخواست‌ها را پردازش کند.
