"""Cache Warming on Startup for recall-cache."""

import time
import threading
from typing import Callable, List, Dict, Any, Optional

from recall.cache import CacheBackend


class StartupWarmer:
    """
    Cache Warming on Startup — pre-populate cache when application starts.
    
    Usage:
        from recall.startup import StartupWarmer
        
        warmer = StartupWarmer(backend)
        
        warmer.add_warmup("users", lambda: fetch_users(), ttl="1h")
        warmer.add_warmup("config", lambda: load_config(), ttl="24h")
        
        # Run all warmups
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
        """
        Run all warmup tasks.
        
        Args:
            parallel: If True, run tasks in parallel threads
            
        Returns:
            Dict with results and statistics
        """
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
