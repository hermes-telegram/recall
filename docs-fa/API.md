# مرجع API

## `cache()`

```python
from recall import cache

@cache(
    ttl="1h",
    maxsize=1000,
    backend=None,
    key_fn=None,
    prefix="",
    sliding=False,
    version=None,
    on_evict=None,
    compression=False,
    compression_level=6,
    stampede_protection=False,
    background_refresh=None,
    serializer="pickle",
    jitter=False,
    jitter_max_percent=10,
    condition=None,
    admin=False,
    rate_limit=False,
    rate_limit_max=100,
    rate_limit_window=60,
    circuit_breaker=False,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=30,
    audit=False,
    trace=False,
)
```

### پارامترها

| پارامتر | نوع | پیش‌فرض | توضیح |
|---------|-----|---------|--------|
| `ttl` | `str \| float` | `"1h"` | زمان انقضا: `"30s"`، `"5m"`، `"1h"`، `"1d"`، `"1w"`، یا ثانیه |
| `maxsize` | `int` | `1000` | حداکثر آیتم (فقط MemoryBackend) |
| `backend` | `CacheBackend` | `None` | بک‌اند سفارشی |
| `key_fn` | `Callable` | `None` | تابع کلید سفارشی |
| `prefix` | `str` | `""` | پیشوند کلید برای نیم‌اسپیس |
| `sliding` | `bool` | `False` | ریست TTL در هر دسترسی |
| `version` | `str` | `None` | نسخه کش |
| `compression` | `bool` | `False` | فشرده‌سازی مقادیر |
| `compression_level` | `int` | `6` | سطح فشرده‌سازی (۱-۹) |
| `stampede_protection` | `bool` | `False` | محافظت از stampede |
| `background_refresh` | `float` | `None` | ثانیه قبل از انقضا برای رفرش |
| `serializer` | `str` | `"pickle"` | فرمت سریالیزاسیون |
| `jitter` | `bool` | `False` | فعال کردن jitter |
| `condition` | `Callable` | `None` | کش شرطی |
| `admin` | `bool` | `False` | فعال کردن پنل ادمین |
| `rate_limit` | `bool` | `False` | فعال کردن محدودیت نرخ |
| `circuit_breaker` | `bool` | `False` | فعال کردن circuit breaker |
| `audit` | `bool` | `False` | فعال کردن لاگ حسابرسی |
| `trace` | `bool` | `False` | فعال کردن ردیابی توزیع‌شده |

### متدهای پیوسته

| متد | توضیح |
|-----|--------|
| `.cache_clear()` | پاک کردن همه مقادیر |
| `.cache_delete(*args, **kwargs)` | حذف یک کلید خاص |
| `.cache_get(*args, **kwargs)` | گرفتن بدون محاسبه |
| `.cache_set(value, *args, **kwargs)` | تنظیم دستی |
| `.cache_warm(args_list)` | پر کردن کش از قبل |
| `.cache_stats` | آمار کش |
| `.cache_keys()` | همه کلیدها |
| `.cache_health()` | سلامت بک‌اند |
| `.cache_get_many(keys)` | گرفتن چند کلید |
| `.cache_set_many(items, ttl)` | تنظیم چند کلید |
| `.cache_delete_many(keys)` | حذف چند کلید |
| `.cache_ttl(key)` | TTL باقیمانده |
| `.cache_touch(key, ttl)` | آپدیت TTL |
| `.cache_exists(key)` | بررسی وجود کلید |

---

## بک‌اندها

### `MemoryBackend`

```python
from recall import MemoryBackend

backend = MemoryBackend(
    maxsize=1000,
    compression=False,
    compression_level=6,
)
```

### `DiskBackend`

```python
from recall import DiskBackend

backend = DiskBackend(
    directory=".recall_cache",
    compression=False,
    compression_level=6,
    max_size_bytes=None,
    encryption_key=None,
    cleanup_interval=60,
)
```

### `RedisBackend`

```python
from recall import RedisBackend

backend = RedisBackend(
    url="redis://localhost:6379",
    prefix="recall:",
    compression=False,
    compression_level=6,
    max_connections=10,
    socket_timeout=5.0,
    retry_on_timeout=True,
    max_retries=3,
    serializer="pickle",
    key_hash=False,
    db=0,
)
```

### `MultiTierBackend`

```python
from recall import MultiTierBackend, MemoryBackend, RedisBackend

backend = MultiTierBackend(
    l1=MemoryBackend(),
    l2=RedisBackend(),
    jitter=True,
    jitter_max_percent=10,
)
```

---

## پنل ادمین

```python
from recall import AdminPanel

panel = AdminPanel(
    backend=backend,
    port=8080,
    host="0.0.0.0",
    auth_token="secret",
    enable_metrics=True,
    enable_audit=True,
)
panel.start()
```

---

## محدودکننده نرخ

```python
from recall import RateLimiter

limiter = RateLimiter(max_requests=100, window=60.0)

if limiter.allow():
    # ادامه عملیات
    pass
```

---

## Circuit Breaker

```python
from recall import CircuitBreaker

cb = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30.0,
)

@cb
def cache_operation():
    return backend.get("key")
```

---

## لاگر حسابرسی

```python
from recall import AuditLogger

audit = AuditLogger()
audit.log("cache_clear", user="admin", details="Cleared all cache")
entries = audit.get_entries(limit=100)
```

---

## جستجوگر کلید

```python
from recall import KeySearcher

searcher = KeySearcher(backend)
keys = searcher.search("user:*")
keys = searcher.search_contains("123")
keys = searcher.search_by_prefix("user:")
```

---

## مدیریت GDPR

```python
from recall import GDPRManager

gdpr = GDPRManager(backend)
gdpr.track_user("user123", ["user:123:profile", "user:123:posts"])
deleted = gdpr.forget_user("user123")
```

---

## مدیریت پشتیبان

```python
from recall import BackupManager

backup = BackupManager(backend)
backup.backup_to_file("/tmp/backup.json")
backup.restore_from_file("/tmp/backup.json")
```

---

## آمار کش

```python
stats = my_func.cache_stats
print(stats.hits)       # تعداد hits
print(stats.misses)     # تعداد misses
print(stats.total)      # کل درخواست‌ها
print(stats.hit_rate)   # نرخ hit (۰.۰ تا ۱.۰)
stats.reset()           # ریست شمارنده‌ها
```

---

## استثناها

| استثنا | توضیح |
|--------|--------|
| `CacheError` | استثنا پایه برای خطاهای کش |
| `BackendError` | خطای مربوط به بک‌اند |
| `CircuitBreakerOpenError` | Circuit breaker باز است |
| `RateLimitExceededError` | محدودیت نرخ رد شده |
