# ریکال — کش هوشمند برای هر تابعی

کش هوشمند برای هر تابعی — ساده مثل requests.

```python
from recall import cache

@cache(ttl="1h")
def get_user(user_id):
    return db.query(user_id)
```

## ویژگی‌ها

- **API ساده** — فقط با `@cache(ttl="1h")` هر تابعی رو کش کن
- **چندین بک‌اند** — حافظه، دیسک، ردیس
- **انقدا ساده** — `"30m"`، `"1h"`، `"7d"` به جای ثانیه
- **حذف LRU** — تمیز کردن خودکار وقتی به حداکثر رسیدی
- **ایمن برای ترد** — در محیط‌های همزمان کار می‌کنه
- **پشتیبانی async** — سازگاری کامل با async/await
- **آمار کش** — ردیابی hit/miss
- **محافظت stampede** — جلوگیری از cache stampede
- **رفرش پس‌زمینه** — رفرش خودکار قبل از انقضا
- **فشرده‌سازی** — فشرده‌سازی zlib برای مقادیر بزرگ
- **عملیات دسته‌ای** — get_many, set_many, delete_many
- **سریالیزاسیون** — pickle, JSON, msgpack
- **نیم‌اسپیس** — پیشوند کلید و نسخه‌بندی
- **گرم کردن کش** — پر کردن کش از قبل
- **TTL لغزنده** — ریست TTL در هر دسترسی
- **بدون وابستگی** — بک‌اند ردیس اختیاریه

## نصب

```bash
pip install recall
# با پشتیبانی ردیس:
pip install recall[redis]
```

## شروع سریع

```python
from recall import cache
import time

@cache(ttl="1h", maxsize=1000)
def expensive_func(x):
    time.sleep(2)
    return x * 2

# اولین فراخوانی: محاسبه می‌کنه
result = expensive_func(5)  # ۲ ثانیه طول می‌کشه

# دومین فراخوانی: فوری (از کش)
result = expensive_func(5)  # فوری برمی‌گردونه
```

## بک‌اند‌ها

### حافظه (پیش‌فرض)

```python
@cache(ttl="1h", maxsize=1000)
def func(x):
    return x * 2
```

### دیسک (دائمی)

```python
from recall import DiskBackend

@cache(ttl="1h", backend=DiskBackend("/tmp/my_cache"))
def func(x):
    return x * 2
```

### ردیس

```python
from recall import RedisBackend

@cache(ttl="1h", backend=RedisBackend("redis://localhost:6379"))
def func(x):
    return x * 2
```

## مدیریت کش

```python
# پاک کردن همه مقادیر کش شده
expensive_func.cache_clear()

# حذف یک کلید خاص
expensive_func.cache_delete(42)

# گرفتن بدون محاسبه
result = expensive_func.cache_get(42)

# تنظیم دستی
expensive_func.cache_set(99, 42)

# پر کردن کش از قبل
expensive_func.cache_warm([(1,), (2,), (3,)])

# آمار کش
stats = expensive_func.cache_stats
print(stats.hits, stats.misses, stats.hit_rate)

# همه کلیدها
keys = expensive_func.cache_keys()

# سلامت بک‌اند
health = expensive_func.cache_health()
```

## عملیات دسته‌ای

```python
# گرفتن چند کلید
results = expensive_func.cache_get_many(["key1", "key2"])

# تنظیم چند کلید
expensive_func.cache_set_many({"key1": 1, "key2": 2})

# حذف چند کلید
expensive_func.cache_delete_many(["key1", "key2"])
```

## ویژگی‌های پیشرفته

### TTL لغزنده (ریست در هر دسترسی)

```python
@cache(ttl="5m", sliding=True)
def get_session(session_id):
    return db.query(session_id)
```

### نسخه‌بندی کش

```python
@cache(ttl="1h", version="2")  # تغییر برای باطل کردن همه
def get_data(key):
    return fetch(key)
```

### محافظت Stampede

```python
@cache(ttl="1h", stampede_protection=True)
def expensive_computation(x):
    return x ** x
```

### رفرش پس‌زمینه

```python
@cache(ttl="1h", background_refresh=300)  # رفرش ۵ دقیقه قبل از انقضا
def get_config():
    return fetch_config()
```

### فشرده‌سازی

```python
@cache(ttl="1h", compression=True)
def get_large_data():
    return list(range(100000))
```

### تابع کلید سفارشی

```python
@cache(ttl="1h", key_fn=lambda f, a, k: f"{a[0]}_{k.get('mode', '')}")
def process(data, mode="default"):
    return f"{data}_{mode}"
```

### پیشوند کلید (نیم‌اسپیس)

```python
@cache(ttl="1h", prefix="myapp")
def get_user(user_id):
    return db.query(user_id)
```

### فرمت سریالیزاسیون

```python
@cache(ttl="1h", serializer="json")  # pickle, json, msgpack
def get_data():
    return {"key": "value"}
```

## پشتیبانی Async

```python
@cache(ttl="1h")
async def get_user_async(user_id):
    return await db.query(user_id)

# کار با توابع async
result = await get_user_async(1)

# گرم کردن کش در async
await get_user_async.cache_warm([(1,), (2,)])
```

## فرمت‌های انقضا

| مختصر | معنی |
|--------|------|
| `"30s"` | ۳۰ ثانیه |
| `"5m"` | ۵ دقیقه |
| `"1h"` | ۱ ساعت |
| `"1d"` | ۱ روز |
| `"1w"` | ۱ هفته |
| `3600` | ثانیه خام (int/float) |

## چرا ریکال؟

| ابزار | مشکل |
|--------|------|
| `functools.lru_cache` | بدون انقضا، بدون دائمی بودن |
| `cachetools` | API پیچیده، بدون دیسک/ردیس |
| `redis` به تنهایی | مدیریت دستی کلید |
| `dogpile.cache` | بیش از حد ساده برای استفاده ساده |

**ریکال** = API ساده + بک‌اند واقعی + انقضا درست انجام شده.

## مجوز

MIT
