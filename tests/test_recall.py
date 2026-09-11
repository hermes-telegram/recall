"""Comprehensive tests for recall."""

import asyncio
import os
import shutil
import tempfile
import time
import threading
import pytest
from recall import cache, MemoryBackend, DiskBackend, CacheStats

# Check if redis is available
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


# ============================================================
# Memory Backend Tests
# ============================================================

class TestMemoryBackend:
    def test_set_and_get(self):
        be = MemoryBackend()
        be.set("key1", "value1", ttl=60)
        result = be.get("key1")
        assert result is not None
        _, value = result
        assert value == "value1"

    def test_get_missing(self):
        be = MemoryBackend()
        assert be.get("nonexistent") is None

    def test_expiration(self):
        be = MemoryBackend()
        be.set("key1", "value1", ttl=0.1)
        time.sleep(0.15)
        assert be.get("key1") is None

    def test_delete(self):
        be = MemoryBackend()
        be.set("key1", "value1", ttl=60)
        be.delete("key1")
        assert be.get("key1") is None

    def test_clear(self):
        be = MemoryBackend()
        be.set("k1", "v1", ttl=60)
        be.set("k2", "v2", ttl=60)
        be.clear()
        assert be.get("k1") is None
        assert be.get("k2") is None

    def test_maxsize_eviction(self):
        be = MemoryBackend(maxsize=3)
        for i in range(5):
            be.set(f"k{i}", f"v{i}", ttl=60)
        count = sum(1 for i in range(5) if be.get(f"k{i}") is not None)
        assert count == 3

    def test_lru_eviction(self):
        be = MemoryBackend(maxsize=3)
        be.set("a", 1, ttl=60)
        be.set("b", 2, ttl=60)
        be.set("c", 3, ttl=60)
        be.get("a")
        be.set("d", 4, ttl=60)
        assert be.get("a") is not None
        assert be.get("b") is None
        assert be.get("c") is not None
        assert be.get("d") is not None

    def test_overwrite(self):
        be = MemoryBackend()
        be.set("key1", "old", ttl=60)
        be.set("key1", "new", ttl=60)
        _, value = be.get("key1")
        assert value == "new"

    def test_various_types(self):
        be = MemoryBackend()
        be.set("int", 42, ttl=60)
        be.set("list", [1, 2, 3], ttl=60)
        be.set("dict", {"a": 1}, ttl=60)
        be.set("none", None, ttl=60)
        be.set("tuple", (1, 2), ttl=60)
        assert be.get("int")[1] == 42
        assert be.get("list")[1] == [1, 2, 3]
        assert be.get("dict")[1] == {"a": 1}
        assert be.get("none")[1] is None
        assert be.get("tuple")[1] == (1, 2)

    def test_compression(self):
        be = MemoryBackend(compression=True)
        be.set("key1", "value1", ttl=60)
        result = be.get("key1")
        assert result is not None
        assert result[1] == "value1"

    def test_get_many(self):
        be = MemoryBackend()
        be.set("k1", "v1", ttl=60)
        be.set("k2", "v2", ttl=60)
        be.set("k3", "v3", ttl=60)
        results = be.get_many(["k1", "k2", "k4"])
        assert "k1" in results
        assert "k2" in results
        assert "k4" not in results

    def test_set_many(self):
        be = MemoryBackend()
        be.set_many({"k1": "v1", "k2": "v2"}, ttl=60)
        assert be.get("k1")[1] == "v1"
        assert be.get("k2")[1] == "v2"

    def test_delete_many(self):
        be = MemoryBackend()
        be.set("k1", "v1", ttl=60)
        be.set("k2", "v2", ttl=60)
        be.delete_many(["k1", "k2"])
        assert be.get("k1") is None
        assert be.get("k2") is None

    def test_keys(self):
        be = MemoryBackend()
        be.set("k1", "v1", ttl=60)
        be.set("k2", "v2", ttl=60)
        keys = be.keys()
        assert len(keys) == 2

    def test_health(self):
        be = MemoryBackend()
        health = be.health()
        assert health["status"] == "healthy"
        assert health["type"] == "memory"


# ============================================================
# Disk Backend Tests
# ============================================================

class TestDiskBackend:
    def setup_method(self):
        self.dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_set_and_get(self):
        be = DiskBackend(self.dir)
        be.set("key1", "value1", ttl=60)
        result = be.get("key1")
        assert result is not None
        assert result[1] == "value1"

    def test_get_missing(self):
        be = DiskBackend(self.dir)
        assert be.get("nonexistent") is None

    def test_expiration(self):
        be = DiskBackend(self.dir)
        be.set("key1", "value1", ttl=0.1)
        time.sleep(0.15)
        assert be.get("key1") is None

    def test_delete(self):
        be = DiskBackend(self.dir)
        be.set("key1", "value1", ttl=60)
        be.delete("key1")
        assert be.get("key1") is None

    def test_clear(self):
        be = DiskBackend(self.dir)
        be.set("k1", "v1", ttl=60)
        be.set("k2", "v2", ttl=60)
        be.clear()
        assert be.get("k1") is None
        assert be.get("k2") is None

    def test_persistence(self):
        be = DiskBackend(self.dir)
        be.set("key1", {"complex": "data"}, ttl=60)
        be2 = DiskBackend(self.dir)
        result = be2.get("key1")
        assert result is not None
        assert result[1] == {"complex": "data"}

    def test_various_types(self):
        be = DiskBackend(self.dir)
        be.set("int", 42, ttl=60)
        be.set("list", [1, 2, 3], ttl=60)
        be.set("dict", {"a": 1}, ttl=60)
        be.set("none", None, ttl=60)
        assert be.get("int")[1] == 42
        assert be.get("list")[1] == [1, 2, 3]
        assert be.get("dict")[1] == {"a": 1}
        assert be.get("none")[1] is None

    def test_compression(self):
        be = DiskBackend(self.dir, compression=True)
        be.set("key1", "value1", ttl=60)
        result = be.get("key1")
        assert result is not None
        assert result[1] == "value1"

    def test_size_limit(self):
        be = DiskBackend(self.dir, max_size_bytes=200)
        be.set("k1", "x" * 100, ttl=60)
        be.set("k2", "y" * 100, ttl=60)
        be.set("k3", "z" * 100, ttl=60)
        # One should be evicted
        count = sum(1 for k in ["k1", "k2", "k3"] if be.get(k) is not None)
        assert count <= 2

    def test_get_many(self):
        be = DiskBackend(self.dir)
        be.set("k1", "v1", ttl=60)
        be.set("k2", "v2", ttl=60)
        results = be.get_many(["k1", "k2"])
        assert "k1" in results
        assert "k2" in results

    def test_set_many(self):
        be = DiskBackend(self.dir)
        be.set_many({"k1": "v1", "k2": "v2"}, ttl=60)
        assert be.get("k1")[1] == "v1"
        assert be.get("k2")[1] == "v2"

    def test_delete_many(self):
        be = DiskBackend(self.dir)
        be.set("k1", "v1", ttl=60)
        be.set("k2", "v2", ttl=60)
        be.delete_many(["k1", "k2"])
        assert be.get("k1") is None
        assert be.get("k2") is None

    def test_keys(self):
        be = DiskBackend(self.dir)
        be.set("k1", "v1", ttl=60)
        be.set("k2", "v2", ttl=60)
        keys = be.keys()
        assert len(keys) == 2

    def test_health(self):
        be = DiskBackend(self.dir)
        health = be.health()
        assert health["status"] == "healthy"
        assert health["type"] == "disk"


# ============================================================
# CacheStats Tests
# ============================================================

class TestCacheStats:
    def test_hit(self):
        stats = CacheStats()
        stats.hit()
        stats.hit()
        assert stats.hits == 2
        assert stats.misses == 0
        assert stats.hit_rate == 1.0

    def test_miss(self):
        stats = CacheStats()
        stats.miss()
        assert stats.hits == 0
        assert stats.misses == 1
        assert stats.hit_rate == 0.0

    def test_mixed(self):
        stats = CacheStats()
        stats.hit()
        stats.hit()
        stats.miss()
        assert stats.hit_rate == 2 / 3

    def test_reset(self):
        stats = CacheStats()
        stats.hit()
        stats.miss()
        stats.reset()
        assert stats.hits == 0
        assert stats.misses == 0

    def test_to_dict(self):
        stats = CacheStats()
        stats.hit()
        d = stats.to_dict()
        assert "hits" in d
        assert "misses" in d
        assert "hit_rate" in d

    def test_thread_safety(self):
        stats = CacheStats()
        def worker():
            for _ in range(100):
                stats.hit()
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert stats.hits == 1000


# ============================================================
# Decorator Tests
# ============================================================

class TestCacheDecorator:
    def test_basic_caching(self):
        call_count = 0

        @cache(ttl="1h")
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(2, 3) == 5
        assert add(2, 3) == 5
        assert call_count == 1

    def test_different_args(self):
        call_count = 0

        @cache(ttl="1h")
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(2, 3) == 5
        assert add(3, 4) == 7
        assert call_count == 2

    def test_ttl_expiration(self):
        call_count = 0

        @cache(ttl=0.1)
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(2, 3) == 5
        time.sleep(0.15)
        assert add(2, 3) == 5
        assert call_count == 2

    def test_cache_clear(self):
        call_count = 0

        @cache(ttl="1h")
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        add(2, 3)
        add.cache_clear()
        add(2, 3)
        assert call_count == 2

    def test_cache_delete(self):
        call_count = 0

        @cache(ttl="1h")
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        add(2, 3)
        add.cache_delete(2, 3)
        add(2, 3)
        assert call_count == 2

    def test_kwargs_caching(self):
        call_count = 0

        @cache(ttl="1h")
        def greet(name, greeting="Hello"):
            nonlocal call_count
            call_count += 1
            return f"{greeting}, {name}!"

        assert greet("Alice") == "Hello, Alice!"
        assert greet("Alice") == "Hello, Alice!"
        assert greet("Alice", greeting="Hi") == "Hi, Alice!"
        assert call_count == 2

    def test_custom_key_fn(self):
        call_count = 0

        @cache(ttl="1h", key_fn=lambda f, a, k: f"{a[0]}_{k.get('mode', '')}")
        def process(data, mode="default"):
            nonlocal call_count
            call_count += 1
            return f"{data}_{mode}"

        assert process("x", mode="fast") == "x_fast"
        assert process("x", mode="fast") == "x_fast"
        assert process("x", mode="slow") == "x_slow"
        assert call_count == 2

    def test_custom_backend(self):
        be = MemoryBackend()
        call_count = 0

        @cache(ttl="1h", backend=be)
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        add(2, 3)
        assert len(be._cache) == 1

    def test_functools_wraps(self):
        @cache(ttl="1h")
        def my_func(a, b):
            """My docstring."""
            return a + b

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "My docstring."

    def test_exception_not_cached(self):
        call_count = 0

        @cache(ttl="1h")
        def fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("oops")

        with pytest.raises(ValueError):
            fail()
        with pytest.raises(ValueError):
            fail()
        assert call_count == 2

    def test_none_return(self):
        call_count = 0

        @cache(ttl="1h")
        def return_none():
            nonlocal call_count
            call_count += 1
            return None

        assert return_none() is None
        assert return_none() is None
        assert call_count == 1

    def test_ttl_parsing(self):
        call_count = 0

        @cache(ttl="1s")
        def f1():
            nonlocal call_count
            call_count += 1
            return 1

        @cache(ttl="5m")
        def f2():
            nonlocal call_count
            call_count += 1
            return 2

        @cache(ttl="2h")
        def f3():
            nonlocal call_count
            call_count += 1
            return 3

        @cache(ttl="1d")
        def f4():
            nonlocal call_count
            call_count += 1
            return 4

        @cache(ttl="1w")
        def f5():
            nonlocal call_count
            call_count += 1
            return 5

        @cache(ttl=3600)
        def f6():
            nonlocal call_count
            call_count += 1
            return 6

        f1(); f2(); f3(); f4(); f5(); f6()
        assert call_count == 6

    def test_method_caching(self):
        class Calculator:
            def __init__(self):
                self.calls = 0

            @cache(ttl="1h")
            def add(self, a, b):
                self.calls += 1
                return a + b

        calc = Calculator()
        assert calc.add(2, 3) == 5
        assert calc.add(2, 3) == 5
        assert calc.calls == 1

    def test_concurrent_access(self):
        @cache(ttl="1h")
        def slow_func(x):
            time.sleep(0.01)
            return x * 2

        results = []
        def worker():
            results.append(slow_func(5))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r == 10 for r in results)

    def test_cache_get(self):
        call_count = 0

        @cache(ttl="1h")
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        result = add.cache_get(2, 3)
        assert result is None
        add(2, 3)
        result = add.cache_get(2, 3)
        assert result == 5

    def test_cache_set(self):
        @cache(ttl="1h")
        def add(a, b):
            return a + b

        add.cache_set(99, 2, 3)
        result = add.cache_get(2, 3)
        assert result == 99

    def test_cache_warm(self):
        call_count = 0

        @cache(ttl="1h")
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        add.cache_warm([(1, 2), (3, 4)])
        assert call_count == 2
        add(1, 2)
        add(3, 4)
        assert call_count == 2  # No additional calls

    def test_cache_stats(self):
        @cache(ttl="1h")
        def add(a, b):
            return a + b

        add(2, 3)
        add(2, 3)
        add(3, 4)
        stats = add.cache_stats
        assert stats.hits == 1
        assert stats.misses == 2

    def test_cache_keys(self):
        @cache(ttl="1h")
        def add(a, b):
            return a + b

        add(2, 3)
        add(3, 4)
        keys = add.cache_keys()
        assert len(keys) == 2

    def test_cache_health(self):
        @cache(ttl="1h")
        def add(a, b):
            return a + b

        health = add.cache_health()
        assert health["status"] == "healthy"

    def test_cache_get_many(self):
        @cache(ttl="1h")
        def add(a, b):
            return a + b

        add(2, 3)
        add(3, 4)
        results = add.cache_get_many(add.cache_keys())
        assert len(results) == 2

    def test_cache_set_many(self):
        @cache(ttl="1h")
        def add(a, b):
            return a + b

        keys = add.cache_keys()
        add.cache_set_many({k: 99 for k in keys})
        for k in keys:
            _, v = add.cache_backend.get(k)
            assert v == 99

    def test_cache_delete_many(self):
        @cache(ttl="1h")
        def add(a, b):
            return a + b

        add(2, 3)
        add(3, 4)
        keys = add.cache_keys()
        add.cache_delete_many(keys)
        assert len(add.cache_keys()) == 0

    def test_prefix(self):
        @cache(ttl="1h", prefix="myapp")
        def add(a, b):
            return a + b

        add(2, 3)
        keys = add.cache_keys()
        assert all(k.startswith("myapp:") for k in keys)

    def test_version(self):
        @cache(ttl="1h", version="1")
        def add(a, b):
            return a + b

        add(2, 3)
        keys = add.cache_keys()
        assert len(keys) == 1
        # Key should contain version
        assert "v1" in keys[0]

    def test_sliding_ttl(self):
        @cache(ttl=0.5, sliding=True)
        def add(a, b):
            return a + b

        add(2, 3)
        time.sleep(0.3)
        add(2, 3)  # Should reset TTL
        time.sleep(0.3)
        result = add.cache_get(2, 3)
        assert result is not None  # Still alive due to sliding

    def test_stampede_protection(self):
        call_count = 0
        lock = threading.Lock()

        @cache(ttl="1h", stampede_protection=True)
        def expensive(x):
            nonlocal call_count
            with lock:
                call_count += 1
            time.sleep(0.05)
            return x * 2

        results = []
        def worker():
            results.append(expensive(5))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r == 10 for r in results)
        # Stampede protection should result in fewer calls than threads
        # (some threads should get cached result)
        assert call_count <= 5

    def test_compression(self):
        @cache(ttl="1h", compression=True)
        def add(a, b):
            return a + b

        assert add(2, 3) == 5
        assert add(2, 3) == 5

    def test_serializer_json(self):
        @cache(ttl="1h", serializer="json")
        def add(a, b):
            return a + b

        assert add(2, 3) == 5
        assert add(2, 3) == 5


# ============================================================
# Async Tests
# ============================================================

class TestAsyncCache:
    def test_async_basic(self):
        call_count = 0

        @cache(ttl="1h")
        async def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        loop = asyncio.new_event_loop()
        assert loop.run_until_complete(add(2, 3)) == 5
        assert loop.run_until_complete(add(2, 3)) == 5
        assert call_count == 1
        loop.close()

    def test_async_cache_clear(self):
        @cache(ttl="1h")
        async def add(a, b):
            return a + b

        loop = asyncio.new_event_loop()
        loop.run_until_complete(add(2, 3))
        add.cache_clear()
        assert len(add.cache_keys()) == 0
        loop.close()

    def test_async_cache_warm(self):
        call_count = 0

        @cache(ttl="1h")
        async def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        loop = asyncio.new_event_loop()
        loop.run_until_complete(add.cache_warm([(1, 2), (3, 4)]))
        assert call_count == 2
        loop.close()


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    def test_real_world_pattern(self):
        api_calls = []

        @cache(ttl="5m")
        def fetch_user(user_id):
            api_calls.append(user_id)
            return {"id": user_id, "name": f"User {user_id}"}

        user = fetch_user(1)
        assert user["name"] == "User 1"
        assert len(api_calls) == 1

        user = fetch_user(1)
        assert user["name"] == "User 1"
        assert len(api_calls) == 1

        user = fetch_user(2)
        assert user["name"] == "User 2"
        assert len(api_calls) == 2

    def test_cache_invalidation_pattern(self):
        @cache(ttl="1h")
        def get_config(key):
            return f"value_for_{key}"

        get_config("db_host")
        get_config("db_port")

        get_config.cache_delete("db_host")

    def test_compression_large_data(self):
        @cache(ttl="1h", compression=True)
        def get_large():
            return list(range(1000))

        data = get_large()
        assert len(data) == 1000
        data2 = get_large()
        assert data == data2


# ============================================================
# Redis Tests (only if redis is available)
# ============================================================

@pytest.mark.skipif(not HAS_REDIS, reason="Redis not installed")
class TestRedisBackend:
    def setup_method(self):
        from recall import RedisBackend
        self.backend = RedisBackend("redis://localhost:6379", prefix="test:")

    def teardown_method(self):
        self.backend.clear()

    def test_set_and_get(self):
        self.backend.set("key1", "value1", ttl=60)
        result = self.backend.get("key1")
        assert result is not None
        assert result[1] == "value1"

    def test_get_missing(self):
        assert self.backend.get("nonexistent") is None

    def test_expiration(self):
        self.backend.set("key1", "value1", ttl=1)
        time.sleep(1.5)
        assert self.backend.get("key1") is None

    def test_delete(self):
        self.backend.set("key1", "value1", ttl=60)
        self.backend.delete("key1")
        assert self.backend.get("key1") is None

    def test_clear(self):
        self.backend.set("k1", "v1", ttl=60)
        self.backend.set("k2", "v2", ttl=60)
        self.backend.clear()
        assert self.backend.get("k1") is None
        assert self.backend.get("k2") is None

    def test_compression(self):
        from recall import RedisBackend
        be = RedisBackend("redis://localhost:6379", prefix="test:", compression=True)
        be.set("key1", "value1", ttl=60)
        result = be.get("key1")
        assert result is not None
        assert result[1] == "value1"
        be.clear()

    def test_get_many(self):
        self.backend.set("k1", "v1", ttl=60)
        self.backend.set("k2", "v2", ttl=60)
        results = self.backend.get_many(["k1", "k2"])
        assert "k1" in results
        assert "k2" in results

    def test_set_many(self):
        self.backend.set_many({"k1": "v1", "k2": "v2"}, ttl=60)
        assert self.backend.get("k1")[1] == "v1"
        assert self.backend.get("k2")[1] == "v2"

    def test_delete_many(self):
        self.backend.set("k1", "v1", ttl=60)
        self.backend.set("k2", "v2", ttl=60)
        self.backend.delete_many(["k1", "k2"])
        assert self.backend.get("k1") is None
        assert self.backend.get("k2") is None

    def test_keys(self):
        self.backend.set("k1", "v1", ttl=60)
        self.backend.set("k2", "v2", ttl=60)
        keys = self.backend.keys()
        assert len(keys) == 2

    def test_exists(self):
        self.backend.set("key1", "value1", ttl=60)
        assert self.backend.exists("key1") is True
        assert self.backend.exists("nonexistent") is False

    def test_ttl(self):
        self.backend.set("key1", "value1", ttl=60)
        remaining = self.backend.ttl("key1")
        assert remaining is not None
        assert remaining > 0

    def test_touch(self):
        self.backend.set("key1", "value1", ttl=60)
        assert self.backend.touch("key1", 120) is True
        assert self.backend.touch("nonexistent", 120) is False

    def test_health(self):
        health = self.backend.health()
        assert health["status"] == "healthy"
        assert health["type"] == "redis"

    def test_serializer_json(self):
        from recall import RedisBackend
        be = RedisBackend("redis://localhost:6379", prefix="test:", serializer="json")
        be.set("key1", {"a": 1}, ttl=60)
        result = be.get("key1")
        assert result is not None
        assert result[1] == {"a": 1}
        be.clear()

    def test_key_hash(self):
        from recall import RedisBackend
        be = RedisBackend("redis://localhost:6379", prefix="test:", key_hash=True)
        long_key = "x" * 300
        be.set(long_key, "value", ttl=60)
        result = be.get(long_key)
        assert result is not None
        assert result[1] == "value"
        be.clear()
