# راهنمای عیب‌یابی

## مشکلات رایج

### استفاده بالای حافظه

**علائم**: OOM kills، عملکرد کند

**تشخیص**:
```bash
curl http://localhost:8080/api/stats
```

**راه‌حل**:
1. کاهش `maxsize` در MemoryBackend
2. فعال کردن فشرده‌سازی
3. کاهش مقادیر TTL
4. پاک کردن کش در صورت نیاز

### نرخ hit پایین

**علائم**: بار بالای دیتابیس، پاسخ‌های کند

**تشخیص**:
```bash
curl http://localhost:8080/api/stats | grep hit_rate
```

**راه‌حل**:
1. افزایش مقادیر TTL
2. بررسی الگوهای کلید برای یکتایی
3. فعال کردن گرم کردن کش
4. بررسی منطق باطل کردن کش

### خطاهای اتصال Redis

**علائم**: timeout اتصال، تأخیر بالا

**تشخیص**:
```bash
redis-cli ping
redis-cli info
```

**راه‌حل**:
1. بررسی اتصال شبکه
2. تأیید اجرای Redis
3. بررسی مصرف حافظه Redis
4. بررسی تنظیمات connection pool

### خطاهای بک‌اند دیسک

**علائم**: خرابی نوشتن، خطاهای خواندن

**تشخیص**:
```bash
df -h /var/cache/recall
ls -la /var/cache/recall
```

**راه‌حل**:
1. آزاد کردن فضای دیسک
2. بررسی مجوزهای فایل
3. تأیید کلید رمزنگاری
4. بررسی فایل‌های خراب شده

## حالت دیباگ

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## دریافت کمک

- GitHub Issues: https://github.com/hermes-telegram/recall/issues
- مستندات: https://recall-cache.readthedocs.io
- ایمیل: support@recall-cache.dev
