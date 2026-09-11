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

# تابع کلید سفارشی
@cache(ttl="1h", key_fn=lambda f, a, k: f"{a}_{k.get('mode', '')}")
def custom(data, mode):
    return f"{data}_{mode}"
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
