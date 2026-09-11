# دفترچه عملیات

## نمای کلی

این دفترچه رویه‌های عملیاتی برای recall-cache در پروداکشن را پوشش می‌دهد.

## عملیات رایج

### بررسی سلامت کش

```bash
# بررسی وضعیت بک‌اند
curl http://localhost:8080/api/health

# بررسی متریک‌ها
curl http://localhost:8080/api/metrics

# بررسی کلیدها
curl http://localhost:8080/api/keys
```

### پاک کردن کش

```bash
# پاک کردن کل کش
curl -X DELETE http://localhost:8080/api/cache

# پاک کردن یک کلید خاص
curl -X DELETE http://localhost:8080/api/cache/my-key
```

### پشتیبان‌گیری

```bash
# ایجاد پشتیبان
recall-backup /var/cache/recall /backup/recall-$(date +%Y%m%d).json

# بازیابی از پشتیبان
recall-restore /backup/recall-20240101.json /var/cache/recall
```

## عیب‌یابی

### استفاده بالای حافظه

**علائم**: OOM kills، عملکرد کند

**تشخیص**:
```bash
# بررسی مصرف حافظه
curl http://localhost:8080/api/stats | grep memory

# بررسی تعداد کلیدها
curl http://localhost:8080/api/keys
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
# بررسی نرخ hit
curl http://localhost:8080/api/stats | grep hit_rate

# بررسی الگوهای کلید
curl http://localhost:8080/api/keys
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
# بررسی سلامت Redis
redis-cli ping

# بررسی اطلاعات Redis
redis-cli info
```

**راه‌حل**:
1. بررسی اتصال شبکه
2. تأیید اجرای Redis
3. بررسی مصرف حافظه Redis
4. بررسی تنظیمات connection pool

## رویدهای اضطراری

### خرابی کامل کش

1. **فعال کردن حالت داده قدیمی** (در صورت پیکربندی)
2. **افزایش مقیاس دیتابیس** برای مدیریت بار مستقیم
3. **راه‌اندازی مجدد بک‌اندها**
4. **فعال کردن تدریجی کش**

### خرابی داده

1. **توقف تمام نوشتن‌ها** به کش
2. **پشتیبان‌گیری از وضعیت فعلی**
3. **پاک کردن کلیدهای خراب شده**
4. **بازیابی از پشتیبان**
5. **تأیید یکپارچگی داده**

## مرتبط‌سازی

| مشکل | تماس | پاسخ |
|------|------|------|
| P0 (حیاتی) | oncall@recall-cache.dev | ۱۵ دقیقه |
| P1 (بالا) | oncall@recall-cache.dev | ۳۰ دقیقه |
| P2 (متوسط) | support@recall-cache.dev | ۲ ساعت |
| P3 (پایین) | support@recall-cache.dev | ۱ روز کاری |
