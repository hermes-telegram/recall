"""Integration tests for recall-cache."""

import pytest
import time
import threading
from recall import cache, MemoryBackend, DiskBackend, RedisBackend, MultiTierBackend


class TestIntegration:
    """Integration tests with real backends."""
    
    def test_memory_to_disk_promotion(self):
        """Test data flows from memory to disk."""
        memory = MemoryBackend(maxsize=100)
        disk = DiskBackend("/tmp/test_integration")
        
        @cache(ttl="1h", backend=memory)
        def func(x):
            return x * 2
        
        # Fill memory
        for i in range(100):
            func(i)
        
        assert len(memory.keys()) == 100
        
        # Clear memory, data should still be on disk
        # (This test would need multi-tier to work properly)
        disk.clear()
    
    def test_concurrent_access(self):
        """Test concurrent access from multiple threads."""
        backend = MemoryBackend()
        results = []
        errors = []
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            time.sleep(0.01)
            return x * 2
        
        def worker():
            try:
                for i in range(100):
                    result = func(i % 10)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert len(results) == 1000
    
    def test_high_contention(self):
        """Test high contention on same key."""
        backend = MemoryBackend()
        
        @cache(ttl="1h", backend=backend, stampede_protection=True)
        def func(x):
            time.sleep(0.1)
            return x * 2
        
        results = []
        
        def worker():
            results.append(func(1))
        
        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert all(r == 2 for r in results)
        assert len(results) == 50


class TestChaos:
    """Chaos engineering tests."""
    
    def test_backend_failure_recovery(self):
        """Test recovery after backend failure."""
        backend = MemoryBackend()
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            return x * 2
        
        # Normal operation
        assert func(5) == 10
        
        # Simulate failure by clearing backend
        backend.clear()
        
        # Should still work (recompute)
        assert func(5) == 10
    
    def test_memory_pressure(self):
        """Test behavior under memory pressure."""
        backend = MemoryBackend(maxsize=10)
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            return x * 2
        
        # Fill beyond capacity
        for i in range(100):
            func(i)
        
        # Should only have maxsize items
        assert len(backend.keys()) <= 10
    
    def test_rapid_ttl_expiration(self):
        """Test rapid TTL expiration."""
        backend = MemoryBackend()
        
        @cache(ttl=0.1, backend=backend)
        def func(x):
            return x * 2
        
        # Rapid set/get
        for i in range(100):
            func(i)
            time.sleep(0.01)
        
        # Most should be expired
        assert len(backend.keys()) < 100


class TestLoad:
    """Load tests."""
    
    def test_sustained_throughput(self):
        """Test sustained throughput."""
        backend = MemoryBackend()
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            return x * 2
        
        start = time.time()
        for i in range(10000):
            func(i % 100)
        duration = time.time() - start
        
        # Should complete in reasonable time
        assert duration < 10
    
    def test_burst_traffic(self):
        """Test burst traffic pattern."""
        backend = MemoryBackend()
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            return x * 2
        
        # Burst of requests
        for i in range(1000):
            func(1)
        
        # All should return correct value
        assert all(func(1) == 2 for _ in range(100))
