# آموزش‌ها و نمونه‌ها

## استفاده پایه

### کش ساده

```python
from recall import cache

@cache(ttl="1h")
def get_user(user_id):
    return db.query(user_id)

# اولین فراخوانی: از دیتابیس می‌خواند
user = get_user(1)

# دومین فراخوانی: از کش برمی‌گردد (فوری)
user = get_user(1)
```

### کش با کلید سفارشی

```python
from recall import cache

@cache(ttl="5m", key_fn=lambda user_id: f"user:{user_id}")
def get_user(user_id):
    return db.query(user_id)
```

### کش با شرط

```python
from recall import cache

@cache(ttl="1h", condition=lambda result: result is not None)
def get_user(user_id):
    return db.query(user_id)  # فقط اگر نتیجه None نباشد کش می‌شود
```

## استفاده پیشرفته

### کش چند لایه

```python
from recall import cache, MultiTierBackend, MemoryBackend, RedisBackend

backend = MultiTierBackend(
    l1=MemoryBackend(maxsize=1000),
    l2=RedisBackend("redis://localhost:6379"),
    jitter=True,
)

@cache(ttl="1h", backend=backend)
def get_user(user_id):
    return db.query(user_id)
```

### گرم کردن کش

```python
from recall import cache, MemoryBackend

backend = MemoryBackend()

@cache(ttl="1h", backend=backend)
def get_user(user_id):
    return db.query(user_id)

# پر کردن کش از قبل
get_user.cache_warm([(1,), (2,), (3,)])
```

### باطل کردن کش

```python
from recall import cache

@cache(ttl="1h")
def get_user(user_id):
    return db.query(user_id)

# حذف یک کلید خاص
get_user.cache_delete(1)

# پاک کردن کل کش
get_user.cache_clear()
```

### آمار کش

```python
from recall import cache

@cache(ttl="1h")
def get_user(user_id):
    return db.query(user_id)

# دریافت آمار
stats = get_user.cache_stats
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Hit Rate: {stats.hit_rate:.2%}")
```

## نمونه‌های یکپارچه‌سازی

### یکپارچه‌سازی Django

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'recall.plugins.django_plugin.RecallCache',
        'LOCATION': 'recall-cache',
    }
}

# views.py
from django.core.cache import cache

@cache(ttl="5m", prefix="user")
def get_user(user_id):
    return User.objects.get(id=user_id)
```

### یکپارچه‌سازی FastAPI

```python
from fastapi import FastAPI
from recall import cache, MemoryBackend
from recall.plugins import FastAPICache

app = FastAPI()
cache = FastAPICache(app, backend=MemoryBackend())

@app.get("/users/{user_id}")
@cache.route(ttl="5m")
def get_user(user_id: int):
    return {"user": user_id}
```

### یکپارچه‌سازی Flask

```python
from flask import Flask
from recall import cache, MemoryBackend

app = Flask(__name__)
backend = MemoryBackend()

@app.route("/users/<int:user_id>")
@cache(ttl="5m", backend=backend)
def get_user(user_id):
    return {"user": user_id}
```

## الگوهای سازمانی

### Request Coalescing

```python
from recall.advanced import RequestCoalescer

coalescer = RequestCoalescer()

@coalescer.coalesce
def fetch_user(user_id):
    return db.query(user_id)
```

### Graceful Degradation

```python
from recall.advanced import GracefulDegradation

gd = GracefulDegradation(backend, stale_ttl=3600)

@gd.resilient(ttl="1h")
def get_user(user_id):
    return db.query(user_id)
```

### Adaptive TTL

```python
from recall.advanced import AdaptiveTTL

adaptive = AdaptiveTTL(backend, min_ttl=60, max_ttl=3600)

@adaptive.cached(target_hit_rate=0.8)
def fetch_data(key):
    return expensive_query(key)
```

## تست‌نویسی

### تست واحد

```python
import pytest
from recall import cache, MemoryBackend

def test_cache_hit():
    backend = MemoryBackend()
    
    @cache(ttl="1h", backend=backend)
    def func(x):
        return x * 2
    
    assert func(5) == 10
    assert func(5) == 10  # از کش
    assert func.cache_stats.hits == 1
```

### تست یکپارچه

```python
import pytest
from recall import cache, RedisBackend

def test_redis_backend():
    backend = RedisBackend("redis://localhost:6379")
    
    @cache(ttl="1h", backend=backend)
    def func(x):
        return x * 2
    
    assert func(5) == 10
```

## بهترین شیوه‌ها

1. **از TTL مناسب استفاده کنید** — تعادل بین تازگی و cache hit
2. **فشرده‌سازی را فعال کنید** — برای مقادیر بزرگ
3. **از چند لایه استفاده کنید** — برای بارهای کاری پروداکشن
4. **hit rate را مانیتور کنید** — هدف >90%
5. **از گرم کردن کش استفاده کنید** — برای بارهای قابل پیش‌بینی
6. **محافظت stampede را فعال کنید** — برای endpointهای پرترافیک
7. **از کش شرطی استفاده کنید** — برای جلوگیری از کش خطا
