# سؤالات متداول

## عمومی

### recall-cache چیست؟

recall-cache یه کتابخونه کش پایتونه که API ساده‌ای برای کش نتایج توابع با پشتیبانی TTL (زمان زنده) ارائه میده. این کتابخانه چندین بک‌اند از جمله Memory، Disk و Redis رو پشتیبانی می‌کنه.

### تفاوتش با functools.lru_cache چیه؟

`functools.lru_cache` پشتیبانی TTL نداره و دائمی نیست. recall-cache TTL، دائمی بودن دیسک، بک‌اند Redis و خیلی ویژگی‌های سازمانی رو ارائه میده.

### تفاوتش با cachetools چیه؟

cachetools API پیچیده‌ای داره و بک‌اند دیسک/Redis نداره. recall-cache API ساده‌تری با بک‌اند واقعی و TTL درست انجام شده ارائه میده.

## استفاده

### چطور کش رو فعال کنم؟

```python
from recall import cache

@cache(ttl="1h")
def my_func(x):
    return x * 2
```

### چطور کش رو پاک کنم؟

```python
# پاک کردن کل کش
my_func.cache_clear()

# حذف یک کلید خاص
my_func.cache_delete(42)
```

### چطور آمار کش رو بگیرم؟

```python
stats = my_func.cache_stats
print(f"Hit rate: {stats.hit_rate:.2%}")
```

## بک‌اندها

### کدوم بک‌اند رو استفاده کنم؟

- **Memory**: سریع‌ترین، ولی داده با ریستارت از بین میره
- **Disk**: دائمی، ولی از حافظه کندتره
- **Redis**: دائمی، بین پروسه‌ها مشترکه
- **Multi-tier**: ترکیب Memory + Redis برای بهترین عملکرد

### چطور از Redis استفاده کنم؟

```python
from recall import cache, RedisBackend

backend = RedisBackend("redis://localhost:6379")
@cache(ttl="1h", backend=backend)
def my_func(x):
    return x * 2
```

## عملکرد

### سربار عملکرد چقدره؟

recall-cache برای cache hits کمتر از 1μs و برای cache misses کمتر از 10μs (بک‌اند Memory) سربار اضافه می‌کنه.

### چطور عملکرد رو بهبود بدم؟

1. فشرده‌سازی رو برای مقادیر بزرگ فعال کنید
2. از کش چند لایه استفاده کنید
3. محافظت stampede رو فعال کنید
4. از مقادیر TTL مناسب استفاده کنید

## پروداکشن

### recall-cache آماده پروداکشن هست؟

بله، recall-cache v3.1.0 با ویژگی‌های جامع برای استفاده سازمانی آماده پروداکشن هست.

### چطور در پروداکشن مستقر کنم؟

به [راهنمای استقرار در پروداکشن](PRODUCTION.md) مراجعه کنید.

### چطور recall-cache رو مانیتور کنم؟

از متریک‌های Prometheus و داشبورد Grafana استفاده کنید. به [راهنمای مانیتورینگ](MONITORING.md) مراجعه کنید.

## عیب‌یابی

### استفاده بالای حافظه

`maxsize` رو کاهش بدید یا فشرده‌سازی رو فعال کنید.

### نرخ hit پایین

TTL رو افزایش بدید یا الگوهای کلید رو برای یکتایی بررسی کنید.

### خطاهای اتصال Redis

اتصال شبکه و سلامت Redis رو بررسی کنید.

## پشتیبانی

### چطور پشتیبانی بگیرم؟

- جامعه: GitHub Issues
- تجاری: support@recall-cache.dev
- سازمانی: پشتیبانی تلفنی ۲۴/۷

### چطور باگ رو گزارش کنم؟

یه issue رو GitHub با یه مورد بازسازی حداقلی باز کنید.

### چطور درخواست ویژگی بدم؟

یه issue رو GitHub با برچسب "feature request" باز کنید.
