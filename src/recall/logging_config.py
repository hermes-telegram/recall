"""Structured Logging for recall-cache."""

import json
import logging
import threading
import time
from typing import Optional, Any, Dict


class StructuredLogger:
    """
    Structured JSON logger for recall-cache.
    
    Usage:
        from recall.logging import StructuredLogger
        
        logger = StructuredLogger("myapp")
        logger.log("cache_hit", key="user:123", ttl=300)
    """
    
    def __init__(self, name: str = "recall", level: int = logging.INFO):
        self.name = name
        self.level = level
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._lock = threading.Lock()
        self._log_count = 0
    
    def log(self, event: str, **kwargs):
        """Log a structured event."""
        with self._lock:
            self._log_count += 1
            entry = {
                "timestamp": time.time(),
                "logger": self.name,
                "event": event,
                "sequence": self._log_count,
                **kwargs
            }
            self._logger.info(json.dumps(entry))
    
    def cache_hit(self, key: str, ttl: Optional[float] = None):
        self.log("cache_hit", key=key, ttl=ttl)
    
    def cache_miss(self, key: str):
        self.log("cache_miss", key=key)
    
    def cache_set(self, key: str, ttl: float):
        self.log("cache_set", key=key, ttl=ttl)
    
    def cache_delete(self, key: str):
        self.log("cache_delete", key=key)
    
    def cache_clear(self, count: int = 0):
        self.log("cache_clear", count=count)
    
    def cache_error(self, error: str, key: Optional[str] = None):
        self.log("cache_error", error=error, key=key)
    
    def backend_status(self, status: str, backend_type: str):
        self.log("backend_status", status=status, backend_type=backend_type)
    
    @property
    def log_count(self) -> int:
        return self._log_count


# Global default logger
_default_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "recall") -> StructuredLogger:
    """Get or create the default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = StructuredLogger(name)
    return _default_logger
