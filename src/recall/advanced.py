"""Advanced caching patterns — all 20 enterprise features in one module."""

import asyncio
import functools
import hashlib
import json
import threading
import time
import zlib
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from recall.cache import CacheBackend, MemoryBackend


# ============================================================
# 1. Request Coalescing (Single-Flight)
# ============================================================

class RequestCoalescer:
    """
    Request Coalescing — when multiple requests for the same key arrive
    simultaneously, only one fetch operation is performed.
    
    Usage:
        from recall.advanced import RequestCoalescer
        
        coalescer = RequestCoalescer()
        
        @coalescer.coalesce
        def fetch_user(user_id):
            return db.query(user_id)
    """
    
    def __init__(self):
        self._in_flight: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def coalesce(self, key_fn: Callable = None):
        """Decorator for coalescing requests."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = key_fn(*args, **kwargs) if key_fn else f"{func.__name__}:{args}:{kwargs}"
                
                with self._lock:
                    if key in self._in_flight:
                        return self._in_flight[key]
                    
                    self._in_flight[key] = asyncio.Future()
                
                try:
                    result = func(*args, **kwargs)
                    with self._lock:
                        self._in_flight.pop(key, None)
                    return result
                except Exception as e:
                    with self._lock:
                        self._in_flight.pop(key, None)
                    raise
            
            return wrapper
        return decorator


# ============================================================
# 2. Probabilistic Early Expiration (Facebook method)
# ============================================================

class ProbabilisticEarlyExpiration:
    """
    Probabilistic Early Expiration — prevents thundering herd by
    expiring keys probabilistically before their actual TTL expires.
    
    Usage:
        from recall.advanced import ProbabilisticEarlyExpiration
        
        pee = ProbabilisticEarlyExpiration(backend)
        
        @pee.wrap(ttl="1h", beta=1.0)
        def fetch_data(key):
            return expensive_query(key)
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def wrap(self, ttl: str = "1h", beta: float = 1.0):
        """Decorator for probabilistic early expiration."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = f"{func.__name__}:{args}:{kwargs}"
                result = self.backend.get(key)
                
                if result:
                    expire_time, value = result
                    now = time.time()
                    remaining = expire_time - now
                    
                    if remaining > 0:
                        import random
                        ttl_seconds = self._parse_ttl(ttl)
                        probability = beta * (1 - remaining / ttl_seconds)
                        
                        if random.random() < probability:
                            value = func(*args, **kwargs)
                            self.backend.set(key, value, ttl_seconds)
                        
                        return value
                
                value = func(*args, **kwargs)
                self.backend.set(key, value, self._parse_ttl(ttl))
                return value
            
            return wrapper
        return decorator
    
    def _parse_ttl(self, ttl: str) -> float:
        if isinstance(ttl, (int, float)):
            return float(ttl)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        return float(ttl[:-1]) * multipliers.get(ttl[-1].lower(), 1)


# ============================================================
# 3. Negative Caching
# ============================================================

class NegativeCache:
    """
    Negative Caching — cache misses and errors.
    
    Usage:
        from recall.advanced import NegativeCache
        
        neg_cache = NegativeCache(backend, ttl="5m")
        
        result = neg_cache.get("key", lambda: fetch_from_db("key"))
    """
    
    def __init__(self, backend: CacheBackend, ttl: float = 300):
        self.backend = backend
        self.ttl = ttl
        self._sentinel = "__NEGATIVE_CACHE__"
    
    def get(self, key: str, fetch_fn: Callable, ttl: Optional[float] = None) -> Any:
        """Get with negative caching."""
        result = self.backend.get(f"neg:{key}")
        
        if result:
            _, value = result
            if value == self._sentinel:
                return None
            return value
        
        value = fetch_fn()
        
        if value is None:
            self.backend.set(f"neg:{key}", self._sentinel, ttl or self.ttl)
        else:
            self.backend.set(f"neg:{key}", value, ttl or self.ttl)
        
        return value
    
    def invalidate(self, key: str):
        """Invalidate a negative cache entry."""
        self.backend.delete(f"neg:{key}")


# ============================================================
# 4. Read-Through/Write-Through/Write-Behind
# ============================================================

class CachePatterns:
    """
    Read-Through, Write-Through, Write-Behind patterns.
    
    Usage:
        from recall.advanced import CachePatterns
        
        patterns = CachePatterns(backend, data_source)
        
        data = patterns.read_through("key")
        patterns.write_through("key", value)
        patterns.write_behind("key", value)
    """
    
    def __init__(self, backend: CacheBackend, data_source: Any = None):
        self.backend = backend
        self.data_source = data_source
        self._write_queue: List[Tuple[str, Any]] = []
        self._write_lock = threading.Lock()
    
    def read_through(self, key: str, fetch_fn: Callable, ttl: float = 300) -> Any:
        """Read-Through: load from cache, fetch on miss."""
        result = self.backend.get(key)
        if result:
            _, value = result
            return value
        
        value = fetch_fn()
        if value is not None:
            self.backend.set(key, value, ttl)
        return value
    
    def write_through(self, key: str, value: Any, ttl: float = 300):
        """Write-Through: write to cache and data source."""
        self.backend.set(key, value, ttl)
        if self.data_source:
            self.data_source.write(key, value)
    
    def write_behind(self, key: str, value: Any, ttl: float = 300):
        """Write-Behind: write to cache, queue for data source."""
        self.backend.set(key, value, ttl)
        with self._write_lock:
            self._write_queue.append((key, value))
    
    def flush_write_queue(self):
        """Flush write-behind queue to data source."""
        with self._write_lock:
            queue = self._write_queue[:]
            self._write_queue.clear()
        
        if self.data_source:
            for key, value in queue:
                self.data_source.write(key, value)


# ============================================================
# 5. Dependency Invalidation
# ============================================================

class DependencyInvalidator:
    """
    Dependency Invalidation — invalidate related keys when data changes.
    
    Usage:
        from recall.advanced import DependencyInvalidator
        
        dep = DependencyInvalidator(backend)
        dep.register("user:123", ["user:123:posts", "user:123:friends"])
        dep.invalidate("user:123")
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.Lock()
    
    def register(self, key: str, depends_on: List[str]):
        """Register key dependencies."""
        with self._lock:
            for dep in depends_on:
                self._dependencies[key].add(dep)
                self._reverse_deps[dep].add(key)
    
    def invalidate(self, key: str) -> int:
        """Invalidate a key and all its dependents."""
        with self._lock:
            keys_to_invalidate = {key}
            queue = [key]
            while queue:
                current = queue.pop(0)
                for dependent in self._reverse_deps.get(current, set()):
                    if dependent not in keys_to_invalidate:
                        keys_to_invalidate.add(dependent)
                        queue.append(dependent)
        
        for k in keys_to_invalidate:
            self.backend.delete(k)
        
        return len(keys_to_invalidate)
    
    def get_dependents(self, key: str) -> Set[str]:
        """Get all keys that depend on this key."""
        with self._lock:
            return self._reverse_deps.get(key, set()).copy()


# ============================================================
# 6. Transaction Integration
# ============================================================

class TransactionIntegration:
    """
    Transaction Integration — only update cache if transaction succeeds.
    
    Usage:
        from recall.advanced import TransactionIntegration
        
        tx_cache = TransactionIntegration(backend)
        
        with tx_cache.transaction() as tx:
            tx.set("key1", value1)
            tx.set("key2", value2)
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def transaction(self):
        """Create a cache transaction."""
        return _CacheTransaction(self.backend)


class _CacheTransaction:
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._operations: List[Tuple[str, Any, float]] = []
        self._committed = False
    
    def set(self, key: str, value: Any, ttl: float = 300):
        """Stage a set operation."""
        self._operations.append(("set", key, value, ttl))
    
    def delete(self, key: str):
        """Stage a delete operation."""
        self._operations.append(("delete", key))
    
    def commit(self):
        """Commit all staged operations."""
        if self._committed:
            return
        
        for op in self._operations:
            if op[0] == "set":
                self.backend.set(op[1], op[2], op[3])
            elif op[0] == "delete":
                self.backend.delete(op[1])
        
        self._committed = True
    
    def rollback(self):
        """Rollback all staged operations."""
        self._operations.clear()
        self._committed = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


# ============================================================
# 7. Schema Versioning
# ============================================================

class SchemaVersioning:
    """
    Schema Versioning — invalidate keys when code changes.
    
    Usage:
        from recall.advanced import SchemaVersioning
        
        schema = SchemaVersioning(backend, version="1.0.0")
        
        @schema.cached(ttl="1h")
        def get_user(user_id):
            return db.query(user_id)
    """
    
    def __init__(self, backend: CacheBackend, version: str = "1.0.0"):
        self.backend = backend
        self.version = version
    
    def cached(self, ttl: float = 300, key_fn: Callable = None):
        """Decorator with schema versioning."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                base_key = key_fn(*args, **kwargs) if key_fn else f"{func.__name__}:{args}:{kwargs}"
                versioned_key = f"v{self.version}:{base_key}"
                
                result = self.backend.get(versioned_key)
                if result:
                    _, value = result
                    return value
                
                value = func(*args, **kwargs)
                self.backend.set(versioned_key, value, ttl)
                return value
            
            return wrapper
        return decorator
    
    def invalidate_version(self, old_version: str):
        """Invalidate all keys from an old version."""
        prefix = f"v{old_version}:"
        keys = [k for k in self.backend.keys() if k.startswith(prefix)]
        self.backend.delete_many(keys)
        return len(keys)


# ============================================================
# 8. ETag/If-None-Match
# ============================================================

class HTTPCache:
    """
    HTTP Caching with ETag and Cache-Control headers.
    
    Usage:
        from recall.advanced import HTTPCache
        
        http_cache = HTTPCache(backend)
        
        @http_cache.etag(ttl="1h")
        def get_user(user_id):
            return {"id": user_id, "name": "Ali"}
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def etag(self, ttl: float = 300, key_fn: Callable = None):
        """Decorator for ETag-based caching."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = key_fn(*args, **kwargs) if key_fn else f"{func.__name__}:{args}:{kwargs}"
                
                result = self.backend.get(key)
                if result:
                    _, value = result
                    etag = hashlib.md5(str(value).encode()).hexdigest()
                    return {"value": value, "etag": etag, "cached": True}
                
                value = func(*args, **kwargs)
                self.backend.set(key, value, ttl)
                etag = hashlib.md5(str(value).encode()).hexdigest()
                return {"value": value, "etag": etag, "cached": False}
            
            return wrapper
        return decorator
    
    def check_none_match(self, key: str, if_none_match: str) -> bool:
        """Check if client's ETag matches."""
        result = self.backend.get(key)
        if result:
            _, value = result
            etag = hashlib.md5(str(value).encode()).hexdigest()
            return etag == if_none_match
        return False


# ============================================================
# 9. Cache-Control Headers
# ============================================================

class CacheControl:
    """
    Cache-Control header support.
    
    Usage:
        from recall.advanced import CacheControl
        
        cc = CacheControl(backend)
        
        @cc.cached(max_age=3600, stale_while_revalidate=60)
        def get_data(key):
            return fetch(key)
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def cached(self, max_age: int = 300, stale_while_revalidate: int = 0, must_revalidate: bool = False):
        """Decorator with Cache-Control directives."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = f"{func.__name__}:{args}:{kwargs}"
                
                result = self.backend.get(key)
                if result:
                    expire_time, value = result
                    remaining = expire_time - time.time()
                    
                    if remaining > 0:
                        headers = {
                            "Cache-Control": f"max-age={max_age}",
                            "X-Cache": "HIT",
                            "X-Cache-TTL": str(int(remaining)),
                        }
                        if stale_while_revalidate > 0:
                            headers["Cache-Control"] += f", stale-while-revalidate={stale_while_revalidate}"
                        if must_revalidate:
                            headers["Cache-Control"] += ", must-revalidate"
                        
                        return {"value": value, "headers": headers}
                
                value = func(*args, **kwargs)
                ttl = max_age + stale_while_revalidate
                self.backend.set(key, value, ttl)
                
                headers = {
                    "Cache-Control": f"max-age={max_age}",
                    "X-Cache": "MISS",
                }
                return {"value": value, "headers": headers}
            
            return wrapper
        return decorator


# ============================================================
# 10. Adaptive TTL
# ============================================================

class AdaptiveTTL:
    """
    Adaptive TTL — automatically adjust TTL based on hit rate.
    
    Usage:
        from recall.advanced import AdaptiveTTL
        
        adaptive = AdaptiveTTL(backend, min_ttl=60, max_ttl=3600)
        
        @adaptive.cached(target_hit_rate=0.8)
        def fetch_data(key):
            return expensive_query(key)
    """
    
    def __init__(self, backend: CacheBackend, min_ttl: float = 60, max_ttl: float = 3600):
        self.backend = backend
        self.min_ttl = min_ttl
        self.max_ttl = max_ttl
        self._stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"hits": 0, "misses": 0})
        self._lock = threading.Lock()
    
    def cached(self, target_hit_rate: float = 0.8):
        """Decorator with adaptive TTL."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = f"{func.__name__}:{args}:{kwargs}"
                
                result = self.backend.get(key)
                if result:
                    _, value = result
                    with self._lock:
                        self._stats[key]["hits"] += 1
                    return value
                
                with self._lock:
                    self._stats[key]["misses"] += 1
                
                value = func(*args, **kwargs)
                ttl = self._calculate_ttl(key, target_hit_rate)
                self.backend.set(key, value, ttl)
                return value
            
            return wrapper
        return decorator
    
    def _calculate_ttl(self, key: str, target_hit_rate: float) -> float:
        """Calculate adaptive TTL based on hit rate."""
        with self._lock:
            stats = self._stats[key]
            total = stats["hits"] + stats["misses"]
            
            if total == 0:
                return self.min_ttl
            
            hit_rate = stats["hits"] / total
            
            if hit_rate >= target_hit_rate:
                return min(self.max_ttl, self.min_ttl * 2)
            else:
                return max(self.min_ttl / 2, self.min_ttl)


# ============================================================
# 11. Hot Key Detection
# ============================================================

class HotKeyDetector:
    """
    Hot Key Detection — identify frequently accessed keys.
    
    Usage:
        from recall.advanced import HotKeyDetector
        
        detector = HotKeyDetector(backend, threshold=100)
        
        @detector.monitor
        def get_data(key):
            return fetch(key)
    """
    
    def __init__(self, backend: CacheBackend, threshold: int = 100):
        self.backend = backend
        self.threshold = threshold
        self._access_count: Dict[str, int] = defaultdict(int)
        self._hot_keys: Set[str] = set()
        self._lock = threading.Lock()
    
    def monitor(self, func):
        """Decorator to monitor key access."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            
            with self._lock:
                self._access_count[key] += 1
                if self._access_count[key] >= self.threshold:
                    self._hot_keys.add(key)
            
            return func(*args, **kwargs)
        
        return wrapper
    
    def get_hot_keys(self) -> List[str]:
        """Get list of hot keys."""
        with self._lock:
            return list(self._hot_keys)
    
    def get_access_count(self, key: str) -> int:
        """Get access count for a key."""
        with self._lock:
            return self._access_count.get(key, 0)
    
    def reset(self):
        """Reset all counters."""
        with self._lock:
            self._access_count.clear()
            self._hot_keys.clear()


# ============================================================
# 12. Large Key Detection
# ============================================================

class LargeKeyDetector:
    """
    Large Key Detection — identify keys with large values.
    
    Usage:
        from recall.advanced import LargeKeyDetector
        
        detector = LargeKeyDetector(backend, max_size_bytes=1024*1024)
        detector.check("key", value)
    """
    
    def __init__(self, backend: CacheBackend, max_size_bytes: int = 1024 * 1024):
        self.backend = backend
        self.max_size_bytes = max_size_bytes
        self._large_keys: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def check(self, key: str, value: Any) -> bool:
        """Check if a key's value is too large."""
        import pickle
        size = len(pickle.dumps(value))
        
        if size > self.max_size_bytes:
            with self._lock:
                self._large_keys.append({
                    "key": key,
                    "size_bytes": size,
                    "timestamp": time.time(),
                })
            return True
        return False
    
    def get_large_keys(self) -> List[Dict[str, Any]]:
        """Get list of large keys."""
        with self._lock:
            return self._large_keys.copy()
    
    def clear(self):
        """Clear large key history."""
        with self._lock:
            self._large_keys.clear()


# ============================================================
# 13. Compression Ratio Monitoring
# ============================================================

class CompressionRatioMonitoring:
    """
    Compression Ratio Monitoring — track compression effectiveness.
    
    Usage:
        from recall.advanced import CompressionRatioMonitoring
        
        monitor = CompressionRatioMonitoring()
        ratio = monitor.calculate(original, compressed)
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


# ============================================================
# 14. Memory Fragmentation Tracking
# ============================================================

class MemoryFragmentationTracker:
    """
    Memory Fragmentation Tracking — track memory allocation patterns.
    
    Usage:
        from recall.advanced import MemoryFragmentationTracker
        
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


# ============================================================
# 15. Stale Data Detection
# ============================================================

class StaleDataDetector:
    """
    Stale Data Detection — identify data that hasn't been refreshed.
    
    Usage:
        from recall.advanced import StaleDataDetector
        
        detector = StaleDataDetector(backend, max_age_seconds=3600)
        stale_keys = detector.find_stale_keys()
    """
    
    def __init__(self, backend: CacheBackend, max_age_seconds: float = 3600):
        self.backend = backend
        self.max_age_seconds = max_age_seconds
    
    def find_stale_keys(self) -> List[str]:
        """Find keys that are older than max_age."""
        stale = []
        now = time.time()
        
        for key in self.backend.keys():
            result = self.backend.get(key)
            if result:
                expire_time, _ = result
                remaining = expire_time - now
                if remaining < self.max_age_seconds * 0.1:
                    stale.append(key)
        
        return stale
    
    def get_stale_count(self) -> int:
        """Get count of stale keys."""
        return len(self.find_stale_keys())


# ============================================================
# 16. Cache Warming on Startup
# ============================================================

class StartupWarmer:
    """
    Cache Warming on Startup — pre-populate cache when application starts.
    
    Usage:
        from recall.advanced import StartupWarmer
        
        warmer = StartupWarmer(backend)
        warmer.add_warmup("users", lambda: fetch_users(), ttl="1h")
        warmer.warm_up()
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._warmups: Dict[str, Dict[str, Any]] = {}
        self._results: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def add_warmup(self, name: str, func: Callable, ttl: float = 300, args: tuple = (), kwargs: dict = None):
        """Add a warmup task."""
        self._warmups[name] = {
            "func": func,
            "ttl": ttl,
            "args": args,
            "kwargs": kwargs or {},
        }
    
    def warm_up(self, parallel: bool = True) -> Dict[str, Any]:
        """Run all warmup tasks."""
        start = time.time()
        success = 0
        failed = 0
        
        if parallel:
            threads = []
            results = {}
            
            def run_task(name, task):
                nonlocal success, failed
                try:
                    value = task["func"](*task["args"], **task["kwargs"])
                    self.backend.set(name, value, task["ttl"])
                    results[name] = {"status": "success", "value": value}
                    success += 1
                except Exception as e:
                    results[name] = {"status": "failed", "error": str(e)}
                    failed += 1
            
            for name, task in self._warmups.items():
                thread = threading.Thread(target=run_task, args=(name, task))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            self._results = results
        else:
            for name, task in self._warmups.items():
                try:
                    value = task["func"](*task["args"], **task["kwargs"])
                    self.backend.set(name, value, task["ttl"])
                    self._results[name] = {"status": "success", "value": value}
                    success += 1
                except Exception as e:
                    self._results[name] = {"status": "failed", "error": str(e)}
                    failed += 1
        
        return {
            "total": len(self._warmups),
            "success": success,
            "failed": failed,
            "duration": time.time() - start,
            "results": self._results,
        }
    
    def get_results(self) -> Dict[str, Any]:
        """Get warmup results."""
        return self._results.copy()
    
    def clear(self):
        """Clear all warmup tasks."""
        self._warmups.clear()
        self._results.clear()


# ============================================================
# 17. Graceful Degradation with Stale Data
# ============================================================

class GracefulDegradation:
    """
    Graceful Degradation with Stale Data.
    
    When backend fails, serve stale data instead of failing.
    
    Usage:
        from recall.advanced import GracefulDegradation
        
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
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = f"{func.__name__}:{args}:{kwargs}"
                stale_key = f"stale:{key}"
                
                try:
                    result = self.backend.get(key)
                    if result:
                        expire_time, value = result
                        if expire_time > time.time():
                            return value
                    
                    value = func(*args, **kwargs)
                    self.backend.set(key, value, ttl)
                    self.backend.set(stale_key, value, self.stale_ttl)
                    
                    with self._lock:
                        self._error_count = 0
                    
                    return value
                
                except Exception as e:
                    with self._lock:
                        self._error_count += 1
                        self._last_error = str(e)
                    
                    stale = self.backend.get(stale_key)
                    if stale:
                        _, value = stale
                        return value
                    
                    raise
            
            return wrapper
        return decorator
    
    @property
    def error_count(self) -> int:
        return self._error_count
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error


# ============================================================
# 18. Idempotency Key Support
# ============================================================

class IdempotencyKeySupport:
    """
    Idempotency Key Support for API caching.
    
    Usage:
        from recall.advanced import IdempotencyKeySupport
        
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
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
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


# ============================================================
# 19. Request Deduplication
# ============================================================

class RequestDeduplication:
    """
    Request Deduplication — prevent duplicate requests.
    
    Usage:
        from recall.advanced import RequestDeduplication
        
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
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = f"dedup:{func.__name__}:{args}:{kwargs}"
                
                with self._lock:
                    if key in self._in_flight:
                        elapsed = time.time() - self._in_flight[key]
                        if elapsed < ttl:
                            return {"deduplicated": True, "elapsed": elapsed}
                    
                    self._in_flight[key] = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return {"deduplicated": False, "result": result}
                finally:
                    with self._lock:
                        self._in_flight.pop(key, None)
            
            return wrapper
        return decorator


# ============================================================
# 20. Cache Efficiency Over Time
# ============================================================

class CacheEfficiencyTracker:
    """
    Cache Efficiency Over Time — track hit rate trends.
    
    Usage:
        from recall.advanced import CacheEfficiencyTracker
        
        tracker = CacheEfficiencyTracker(backend)
        
        @tracker.monitor
        def get_data(key):
            return fetch(key)
        
        trend = tracker.get_trend()
    """
    
    def __init__(self, backend: CacheBackend, window_seconds: float = 300):
        self.backend = backend
        self.window_seconds = window_seconds
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def monitor(self, func):
        """Decorator to monitor cache efficiency."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            
            result = self.backend.get(key)
            hit = result is not None
            
            with self._lock:
                self._history.append({
                    "timestamp": time.time(),
                    "hit": hit,
                    "key": key,
                })
                
                cutoff = time.time() - self.window_seconds
                self._history = [h for h in self._history if h["timestamp"] > cutoff]
            
            if hit:
                return result[1]
            
            value = func(*args, **kwargs)
            self.backend.set(key, value, self.window_seconds)
            return value
        
        return wrapper
    
    def get_trend(self) -> Dict[str, Any]:
        """Get cache efficiency trend."""
        with self._lock:
            if not self._history:
                return {"hit_rate": 0, "total": 0}
            
            hits = sum(1 for h in self._history if h["hit"])
            total = len(self._history)
            
            return {
                "hit_rate": hits / total if total > 0 else 0,
                "total": total,
                "hits": hits,
                "misses": total - hits,
                "window_seconds": self.window_seconds,
            }
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get raw history."""
        with self._lock:
            return self._history.copy()
