"""Rate Limiter for recall-cache."""

import time
import threading
from typing import Optional, Dict
from collections import defaultdict


class RateLimiter:
    """
    Token bucket rate limiter for cache operations.
    
    Usage:
        from recall.ratelimit import RateLimiter
        
        limiter = RateLimiter(max_requests=100, window=60)
        
        if limiter.allow():
            # proceed with cache operation
            pass
    """
    
    def __init__(self, max_requests: int = 100, window: float = 60.0):
        self.max_requests = max_requests
        self.window = window
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def allow(self, key: str = "default") -> bool:
        """Check if request is allowed."""
        with self._lock:
            now = time.time()
            # Remove old requests
            self._requests[key] = [t for t in self._requests[key] if now - t < self.window]
            
            if len(self._requests[key]) < self.max_requests:
                self._requests[key].append(now)
                return True
            return False
    
    def remaining(self, key: str = "default") -> int:
        """Get remaining requests in current window."""
        with self._lock:
            now = time.time()
            self._requests[key] = [t for t in self._requests[key] if now - t < self.window]
            return max(0, self.max_requests - len(self._requests[key]))
    
    def reset(self, key: str = "default"):
        """Reset rate limiter for a key."""
        with self._lock:
            self._requests[key].clear()
    
    def reset_all(self):
        """Reset all rate limiters."""
        with self._lock:
            self._requests.clear()
