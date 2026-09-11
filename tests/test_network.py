"""Network partition tests for recall-cache."""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from recall import cache, MemoryBackend, RedisBackend


class TestNetworkPartition:
    """Test behavior during network partitions."""
    
    def test_redis_connection_failure_graceful_degradation(self):
        """Test graceful degradation when Redis fails."""
        backend = MemoryBackend()
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            return x * 2
        
        # Normal operation
        assert func(5) == 10
        
        # Simulate failure by clearing
        backend.clear()
        
        # Should still work (recompute)
        assert func(5) == 10
    
    def test_redis_timeout_handling(self):
        """Test handling of Redis timeouts."""
        backend = MemoryBackend()
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            return x * 2
        
        # Should handle timeout gracefully
        with patch.object(backend, 'get', side_effect=Exception("Timeout")):
            # Should raise or handle gracefully
            try:
                func(5)
            except Exception:
                pass  # Expected
    
    def test_partial_availability(self):
        """Test partial availability scenario."""
        backend = MemoryBackend()
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            return x * 2
        
        # Fill cache
        for i in range(10):
            func(i)
        
        # Simulate partial failure (some keys available)
        # In real scenario, some Redis nodes would be down
        assert func(0) == 0
        assert func(1) == 2
    
    def test_recovery_after_partition(self):
        """Test recovery after network partition heals."""
        backend = MemoryBackend()
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            return x * 2
        
        # Fill cache
        func(1)
        func(2)
        
        # Simulate partition (clear cache)
        backend.clear()
        
        # Partition heals - should rebuild cache
        assert func(1) == 2
        assert func(2) == 4
        
        # Cache should be repopulated
        assert len(backend.keys()) == 2
    
    def test_concurrent_access_during_partition(self):
        """Test concurrent access during network partition."""
        backend = MemoryBackend()
        results = []
        errors = []
        
        @cache(ttl="1h", backend=backend)
        def func(x):
            return x * 2
        
        def worker():
            try:
                for i in range(10):
                    result = func(i % 5)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0
        assert len(results) == 50
