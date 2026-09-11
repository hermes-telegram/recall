"""Benchmarks for recall-cache."""

import time
import statistics
from typing import Callable, Dict, Any

from recall import cache, MemoryBackend, DiskBackend


class Benchmark:
    """Run performance benchmarks on cache backends."""
    
    @staticmethod
    def run(func: Callable, iterations: int = 1000) -> Dict[str, float]:
        """Run a benchmark on a function."""
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)
        
        return {
            "iterations": iterations,
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "max": max(times),
            "total": sum(times),
        }
    
    @staticmethod
    def compare(backends: Dict[str, Any], func: Callable, iterations: int = 1000) -> Dict[str, Dict]:
        """Compare multiple backends."""
        results = {}
        
        for name, backend in backends.items():
            cached_func = cache(ttl="1h", backend=backend)(func)
            results[name] = Benchmark.run(cached_func, iterations)
        
        return results


def run_benchmarks():
    """Run all benchmarks and print results."""
    print("=" * 60)
    print("recall-cache Benchmarks")
    print("=" * 60)
    
    # Test function
    def test_func(x):
        return x * 2
    
    # Backends to compare
    backends = {
        "Memory": MemoryBackend(),
        "Disk": DiskBackend("/tmp/bench_cache"),
    }
    
    print("\n--- Cache Set Performance ---")
    for name, backend in backends.items():
        cached = cache(ttl="1h", backend=backend)(test_func)
        
        start = time.perf_counter()
        for i in range(1000):
            cached(i)
        end = time.perf_counter()
        
        print(f"  {name}: {end - start:.4f}s for 1000 sets")
    
    print("\n--- Cache Hit Performance ---")
    for name, backend in backends.items():
        cached = cache(ttl="1h", backend=backend)(test_func)
        cached(1)  # Warm up
        
        start = time.perf_counter()
        for _ in range(1000):
            cached(1)
        end = time.perf_counter()
        
        print(f"  {name}: {end - start:.4f}s for 1000 hits")
    
    print("\n--- Cache Miss Performance ---")
    for name, backend in backends.items():
        cached = cache(ttl="1h", backend=backend)(test_func)
        
        start = time.perf_counter()
        for i in range(1000):
            cached.cache_clear()
            cached(i)
        end = time.perf_counter()
        
        print(f"  {name}: {end - start:.4f}s for 1000 misses")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_benchmarks()
