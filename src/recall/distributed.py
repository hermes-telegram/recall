"""Distributed Locking for recall-cache."""

import time
import threading
import uuid
from typing import Optional, Dict, Any

from recall.cache import CacheBackend, RedisBackend


class DistributedLock:
    """
    Distributed lock using Redis for coordination.
    
    Usage:
        from recall.distributed import DistributedLock
        
        lock = DistributedLock(backend, "my-lock", timeout=30)
        
        if lock.acquire():
            try:
                # Critical section
                pass
            finally:
                lock.release()
    """
    
    def __init__(
        self,
        backend: CacheBackend,
        name: str,
        timeout: float = 30.0,
        retry_interval: float = 0.1,
    ):
        self.backend = backend
        self.name = f"lock:{name}"
        self.timeout = timeout
        self.retry_interval = retry_interval
        self._owner = str(uuid.uuid4())
        self._locked = False
    
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire the lock.
        
        Args:
            blocking: If True, block until lock is acquired
            timeout: Max time to wait (None = use self.timeout)
        """
        if self._locked:
            return True
        
        wait_time = timeout or self.timeout
        start = time.time()
        
        while True:
            # Try to acquire
            existing = self.backend.get(self.name)
            
            if existing is None:
                # Lock is free, try to acquire
                self.backend.set(self.name, self._owner, ttl=wait_time)
                self._locked = True
                return True
            
            # Check if we already own it
            _, owner = existing
            if owner == self._owner:
                self._locked = True
                return True
            
            # Lock is held by someone else
            if not blocking:
                return False
            
            # Check timeout
            if time.time() - start >= wait_time:
                return False
            
            time.sleep(self.retry_interval)
    
    def release(self) -> bool:
        """Release the lock."""
        if not self._locked:
            return False
        
        existing = self.backend.get(self.name)
        if existing:
            _, owner = existing
            if owner == self._owner:
                self.backend.delete(self.name)
                self._locked = False
                return True
        
        return False
    
    def extend(self, additional_time: float) -> bool:
        """Extend the lock timeout."""
        if not self._locked:
            return False
        
        existing = self.backend.get(self.name)
        if existing:
            _, owner = existing
            if owner == self._owner:
                self.backend.set(self.name, self._owner, ttl=additional_time)
                return True
        
        return False
    
    @property
    def is_locked(self) -> bool:
        return self._locked
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


class DistributedSemaphore:
    """
    Distributed semaphore for limiting concurrent access.
    
    Usage:
        from recall.distributed import DistributedSemaphore
        
        sem = DistributedSemaphore(backend, "api-sem", max_concurrent=10)
        
        if sem.acquire():
            try:
                # Limited section
                pass
            finally:
                sem.release()
    """
    
    def __init__(
        self,
        backend: CacheBackend,
        name: str,
        max_concurrent: int = 10,
        timeout: float = 30.0,
    ):
        self.backend = backend
        self.name = f"sem:{name}"
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self._owner = str(uuid.uuid4())
    
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire a semaphore slot."""
        wait_time = timeout or self.timeout
        start = time.time()
        
        while True:
            # Get current count
            current = self.backend.get(self.name)
            count = current[1] if current else 0
            
            if count < self.max_concurrent:
                # Slot available
                self.backend.set(self.name, count + 1, ttl=self.timeout)
                return True
            
            if not blocking:
                return False
            
            if time.time() - start >= wait_time:
                return False
            
            time.sleep(0.1)
    
    def release(self) -> bool:
        """Release a semaphore slot."""
        current = self.backend.get(self.name)
        if current:
            count = current[1]
            if count > 0:
                self.backend.set(self.name, count - 1, ttl=self.timeout)
                return True
        return False
