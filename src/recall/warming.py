"""Cache Warming Scheduler for recall-cache."""

import time
import threading
from typing import Callable, List, Dict, Any, Optional, Tuple

from recall.cache import CacheBackend


class WarmingScheduler:
    """
    Schedule cache warming tasks.
    
    Usage:
        from recall.warming import WarmingScheduler
        
        scheduler = WarmingScheduler(backend)
        
        # Add a warming task
        scheduler.add_task("users", lambda: fetch_users(), ttl="5m", interval=300)
        
        # Start scheduler
        scheduler.start()
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def add_task(
        self,
        name: str,
        func: Callable,
        ttl: str = "5m",
        interval: int = 300,
        args: tuple = (),
        kwargs: dict = None,
    ):
        """
        Add a warming task.
        
        Args:
            name: Task name
            func: Function to call for warming data
            ttl: TTL for cached data
            interval: How often to run (seconds)
            args: Arguments for func
            kwargs: Keyword arguments for func
        """
        with self._lock:
            self._tasks[name] = {
                "func": func,
                "ttl": ttl,
                "interval": interval,
                "args": args,
                "kwargs": kwargs or {},
                "last_run": 0,
                "run_count": 0,
                "error_count": 0,
            }
    
    def remove_task(self, name: str):
        """Remove a warming task."""
        with self._lock:
            self._tasks.pop(name, None)
    
    def start(self):
        """Start the scheduler."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            now = time.time()
            
            with self._lock:
                tasks = list(self._tasks.items())
            
            for name, task in tasks:
                if now - task["last_run"] >= task["interval"]:
                    self._execute_task(name, task)
            
            time.sleep(1)
    
    def _execute_task(self, name: str, task: Dict[str, Any]):
        """Execute a warming task."""
        try:
            data = task["func"](*task["args"], **task["kwargs"])
            
            # Store in cache
            if isinstance(data, dict):
                for key, value in data.items():
                    self.backend.set(f"{name}:{key}", value, self._parse_ttl(task["ttl"]))
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    self.backend.set(f"{name}:{i}", item, self._parse_ttl(task["ttl"]))
            
            task["last_run"] = time.time()
            task["run_count"] += 1
        except Exception as e:
            task["error_count"] += 1
    
    def _parse_ttl(self, ttl: str) -> float:
        """Parse TTL string to seconds."""
        if isinstance(ttl, (int, float)):
            return float(ttl)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        return float(ttl[:-1]) * multipliers.get(ttl[-1].lower(), 1)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        with self._lock:
            return {
                "running": self._running,
                "task_count": len(self._tasks),
                "tasks": {
                    name: {
                        "run_count": task["run_count"],
                        "error_count": task["error_count"],
                        "last_run": task["last_run"],
                    }
                    for name, task in self._tasks.items()
                },
            }
