# Migration Guide

## From Django Redis

### Before (Django Redis)

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
    }
}

# views.py
from django.core.cache import cache

def get_user(user_id):
    key = f"user:{user_id}"
    user = cache.get(key)
    if user is None:
        user = db.query(user_id)
        cache.set(key, user, 300)
    return user
```

### After (recall-cache)

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'recall.plugins.django_plugin.RecallCache',
        'LOCATION': 'recall-cache',
    }
}

# views.py
from recall import cache

@cache(ttl="5m", prefix="user")
def get_user(user_id):
    return db.query(user_id)
```

## From django-cacheops

### Before (cacheops)

```python
from cacheops import cached_as

@cached_as(User, timeout=300)
def get_user(user_id):
    return User.objects.get(id=user_id)
```

### After (recall-cache)

```python
from recall import cache

@cache(ttl="5m", prefix="user")
def get_user(user_id):
    return User.objects.get(id=user_id)
```

## From Flask-Caching

### Before (Flask-Caching)

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'redis'})

@cache.cached(timeout=300, key_prefix='user')
def get_user(user_id):
    return db.query(user_id)
```

### After (recall-cache)

```python
from recall import cache

@cache(ttl="5m", prefix="user")
def get_user(user_id):
    return db.query(user_id)
```

## From cachetools

### Before (cachetools)

```python
from cachetools import TTLCache

cache = TTLCache(maxsize=1000, ttl=300)

def get_user(user_id):
    key = f"user:{user_id}"
    if key in cache:
        return cache[key]
    user = db.query(user_id)
    cache[key] = user
    return user
```

### After (recall-cache)

```python
from recall import cache

@cache(ttl="5m", prefix="user")
def get_user(user_id):
    return db.query(user_id)
```

## Manual Migration

1. Replace cache backend imports
2. Replace cache decorators
3. Update cache key patterns
4. Test thoroughly
5. Monitor hit rates
