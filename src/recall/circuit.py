"""Circuit Breaker for recall-cache."""

import functools
import time
import threading
from enum import Enum
from typing import Optional, Callable


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit Breaker pattern for cache backends.
    
    Usage:
        from recall.circuit import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        
        @cb
        def cache_operation():
            return backend.get("key")
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - (self._last_failure_time or 0) >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
            return self._state
    
    def _record_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
    
    def _record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            state = self.state
            if state == CircuitState.OPEN:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except self.expected_exception as e:
                self._record_failure()
                raise e
        
        return wrapper


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass
