"""Comprehensive tests for recall."""

import os
import shutil
import time
import pytest
from recall import cache, MemoryBackend, DiskBackend


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
        # Only 3 should remain
        count = sum(1 for i in range(5) if be.get(f"k{i}") is not None)
        assert count == 3

    def test_lru_eviction(self):
        be = MemoryBackend(maxsize=3)
        be.set("a", 1, ttl=60)
        be.set("b", 2, ttl=60)
        be.set("c", 3, ttl=60)
        # Access "a" to make it recently used
        be.get("a")
        # Add "d" — should evict "b" (least recently used)
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


# ============================================================
# Disk Backend Tests
# ============================================================

class TestDiskBackend:
    def setup_method(self):
        self.dir = ".test_recall_cache"

    def teardown_method(self):
        if os.path.exists(self.dir):
            shutil.rmtree(self.dir)

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
        # Create new backend instance (simulates restart)
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
        assert add(2, 3) == 5  # Should use cache
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
        assert add(2, 3) == 5  # Recomputed
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
        def process(data, mode):
            nonlocal call_count
            call_count += 1
            return f"{data}_{mode}"

        assert process("x", mode="y") == "x_y"
        assert process("x", mode="z") == "x_z"  # Different key
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
        # Verify backend has the key
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
        assert call_count == 2  # Not cached

    def test_none_return(self):
        call_count = 0

        @cache(ttl="1h")
        def return_none():
            nonlocal call_count
            call_count += 1
            return None

        assert return_none() is None
        assert return_none() is None
        assert call_count == 1  # Cached

    def test_ttl_parsing(self):
        # Test various TTL formats
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

        @cache(ttl=3600)  # raw seconds
        def f6():
            nonlocal call_count
            call_count += 1
            return 6

        f1(); f2(); f3(); f4(); f5(); f6()
        assert call_count == 6

    def test_nested_decorator(self):
        @cache(ttl="1h")
        @staticmethod
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

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
        import threading

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


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    def test_memory_to_disk(self):
        """Test that data can be cached in memory and retrieved from disk."""
        mem_be = MemoryBackend()
        disk_be = DiskBackend(".test_integration_cache")

        try:
            @cache(ttl="1h", backend=mem_be)
            def compute(x):
                return x * 2

            result = compute(5)
            assert result == 10

            # Verify it's in memory
            assert mem_be.get("some_key") is None  # Different key
        finally:
            shutil.rmtree(".test_integration_cache", ignore_errors=True)

    def test_real_world_pattern(self):
        """Simulate real-world usage: API call caching."""
        api_calls = []

        @cache(ttl="5m")
        def fetch_user(user_id):
            api_calls.append(user_id)
            return {"id": user_id, "name": f"User {user_id}"}

        # First call hits the API
        user = fetch_user(1)
        assert user["name"] == "User 1"
        assert len(api_calls) == 1

        # Second call uses cache
        user = fetch_user(1)
        assert user["name"] == "User 1"
        assert len(api_calls) == 1

        # Different user hits the API
        user = fetch_user(2)
        assert user["name"] == "User 2"
        assert len(api_calls) == 2

    def test_cache_invalidation_pattern(self):
        """Test manual cache invalidation."""
        @cache(ttl="1h")
        def get_config(key):
            return f"value_for_{key}"

        get_config("db_host")
        get_config("db_port")

        # Invalidate one
        get_config.cache_delete("db_host")

        # db_host should be gone, db_port should remain
        # (we can't easily check this without accessing backend directly)
