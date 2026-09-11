"""Graceful Degradation with Stale Data for recall-cache."""

import time
import threading
from typing import Any, Callable, Optional

from recall.cache import CacheBackend


class GracefulDegradation:
    """
    Graceful Degradation with Stale Data.
    
    When backend fails, serve stale data instead of failing.
    
    Usage:
        from recall.graceful import GracefulDegradation
        
        gd = GracefulDegradation(backend, stale_ttl=3600)
        
        @gd.resilient(ttl="1h")
        def get_user(user_id):
            return db.query(user_id)
    """
    
    def __init__(self, backend: CacheBackend, stale_ttl: float = 3600):
        self.backend = backend
        self.stale_ttl = stale_ttl
        self._error_count = 0
        self._last_error = None
        self._lock = threading.Lock()
    
    def resilient(self, ttl: float = 300):
        """Decorator for resilient caching."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                key = f"{func.__name__}:{args}:{kwargs}"
                stale_key = f"stale:{key}"
                
                try:
                    result = self.backend.get(key)
                    if result:
                        expire_time, value = result
                        if expire_time > time.time():
                            return value
                    
                    # Cache miss or expired
                    value = func(*args, **kwargs)
                    self.backend.set(key, value, ttl)
                    
                    # Store stale backup
                    self.backend.set(stale_key, value, self.stale_ttl)
                    
                    with self._lock:
                        self._error_count = 0
                    
                    return value
                
                except Exception as e:
                    with self._lock:
                        self._error_count += 1
                        self._last_error = str(e)
                    
                    # Try to serve stale data
                    stale = self.backend.get(stale_key)
                    if stale:
                        _, value = stale
                        return value
                    
                    # No stale data, re-raise
                    raise
            
            return wrapper
        return decorator
    
    @property
    def error_count(self) -> int:
        return self._error_count
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error


class IdempotencyKeySupport:
    """
    Idempotency Key Support for API caching.
    
    Ensures identical requests return cached results.
    
    Usage:
        from recall.idempotency import IdempotencyKeySupport
        
        idempotency = IdempotencyKeySupport(backend)
        
        @idempotency.cache(ttl="24h")
        def process_payment(order_id, amount):
            return gateway.charge(order_id, amount)
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def cache(self, ttl: float = 86400, key_fn: Callable = None):
        """Decorator for idempotent caching."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Generate idempotency key
                if key_fn:
                    key = key_fn(*args, **kwargs)
                else:
                    key_data = f"{func.__name__}:{args}:{kwargs}"
                    key = f"idemp:{hashlib.sha256(key_data.encode()).hexdigest()}"
                
                result = self.backend.get(key)
                if result:
                    _, value = result
                    return {"cached": True, "result": value}
                
                value = func(*args, **kwargs)
                self.backend.set(key, value, ttl)
                return {"cached": False, "result": value}
            
            return wrapper
        return decorator
    
    def invalidate(self, key: str):
        """Invalidate an idempotency key."""
        self.backend.delete(f"idemp:{key}")


class RequestDeduplication:
    """
    Request Deduplication — prevent duplicate requests.
    
    Usage:
        from recall.dedup import RequestDeduplication
        
        dedup = RequestDeduplication(backend)
        
        @dedup.deduplicate(ttl="10s")
        def send_email(to, subject, body):
            return mailer.send(to, subject, body)
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._in_flight: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def deduplicate(self, ttl: float = 10):
        """Decorator for request deduplication."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                key = f"dedup:{func.__name__}:{args}:{kwargs}"
                
                with self._lock:
                    # Check if already in flight
                    if key in self._in_flight:
                        elapsed = time.time() - self._in_flight[key]
                        if elapsed < ttl:
                            return {"deduplicated": True, "elapsed": elapsed}
                    
                    # Mark as in flight
                    self._in_flight[key] = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return {"deduplicated": False, "result": result}
                finally:
                    with self._lock:
                        self._in_flight.pop(key, None)
            
            return wrapper
        return decorator


class CompressionRatioMonitoring:
    """
    Compression Ratio Monitoring — track compression effectiveness.
    
    Usage:
        from recall.monitoring import CompressionRatioMonitoring
        
        monitor = CompressionRatioMonitoring()
        
        ratio = monitor.calculate(original, compressed)
        stats = monitor.get_stats()
    """
    
    def __init__(self):
        self._stats: Dict[str, Any] = {
            "total_original": 0,
            "total_compressed": 0,
            "count": 0,
        }
        self._lock = threading.Lock()
    
    def calculate(self, original: Any, compressed: bytes) -> float:
        """Calculate compression ratio."""
        import pickle
        original_size = len(pickle.dumps(original))
        compressed_size = len(compressed)
        
        with self._lock:
            self._stats["total_original"] += original_size
            self._stats["total_compressed"] += compressed_size
            self._stats["count"] += 1
        
        if original_size == 0:
            return 0.0
        
        return 1.0 - (compressed_size / original_size)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        with self._lock:
            if self._stats["total_original"] == 0:
                return {"ratio": 0, "count": 0}
            
            ratio = 1.0 - (self._stats["total_compressed"] / self._stats["total_original"])
            
            return {
                "ratio": ratio,
                "count": self._stats["count"],
                "total_original_bytes": self._stats["total_original"],
                "total_compressed_bytes": self._stats["total_compressed"],
                "savings_bytes": self._stats["total_original"] - self._stats["total_compressed"],
            }


class MemoryFragmentationTracker:
    """
    Memory Fragmentation Tracking — track memory allocation patterns.
    
    Usage:
        from recall.monitoring import MemoryFragmentationTracker
        
        tracker = MemoryFragmentationTracker(backend)
        fragmentation = tracker.get_fragmentation()
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._snapshots: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def snapshot(self):
        """Take a memory snapshot."""
        import sys
        
        try:
            keys = self.backend.keys()
            total_size = 0
            key_sizes = []
            
            for key in keys:
                result = self.backend.get(key)
                if result:
                    _, value = result
                    size = sys.getsizeof(value)
                    total_size += size
                    key_sizes.append(size)
            
            snapshot = {
                "timestamp": time.time(),
                "key_count": len(keys),
                "total_size": total_size,
                "avg_key_size": total_size / len(keys) if keys else 0,
                "max_key_size": max(key_sizes) if key_sizes else 0,
                "min_key_size": min(key_sizes) if key_sizes else 0,
            }
            
            with self._lock:
                self._snapshots.append(snapshot)
                if len(self._snapshots) > 100:
                    self._snapshots = self._snapshots[-100:]
            
            return snapshot
        except:
            return {"timestamp": time.time(), "error": "snapshot failed"}
    
    def get_fragmentation(self) -> Dict[str, Any]:
        """Calculate memory fragmentation."""
        with self._lock:
            if len(self._snapshots) < 2:
                return {"fragmentation": 0}
            
            first = self._snapshots[0]
            last = self._snapshots[-1]
            
            # Simple fragmentation metric
            if first["total_size"] == 0:
                return {"fragmentation": 0}
            
            size_change = abs(last["total_size"] - first["total_size"])
            fragmentation = size_change / first["total_size"]
            
            return {
                "fragmentation": fragmentation,
                "size_change": size_change,
                "snapshots": len(self._snapshots),
            }
    
    def get_snapshots(self) -> List[Dict[str, Any]]:
        """Get all snapshots."""
        with self._lock:
            return self._snapshots.copy()
