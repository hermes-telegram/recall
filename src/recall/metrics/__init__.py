"""Prometheus Metrics Export for recall-cache."""

import time
import threading
from typing import Optional, Dict, Any

from recall.cache import CacheBackend


class MetricsCollector:
    """
    Collect and export Prometheus-compatible metrics.
    
    Usage:
        from recall.metrics import MetricsCollector
        
        metrics = MetricsCollector(backend)
        print(metrics.get_metrics())  # Prometheus format
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._start_time = time.time()
        self._operations = 0
        self._errors = 0
        self._lock = threading.Lock()
    
    def record_operation(self):
        with self._lock:
            self._operations += 1
    
    def record_error(self):
        with self._lock:
            self._errors += 1
    
    def get_metrics(self) -> str:
        """Generate Prometheus-compatible metrics."""
        health = self.backend.health()
        lines = []
        
        # Backend status
        status_val = 1 if health.get("status") == "healthy" else 0
        lines.append(f'recall_cache_backend_status {status_val}')
        
        # Backend type
        backend_type = health.get("type", "unknown")
        lines.append(f'recall_cache_backend_type{{type="{backend_type}"}} 1')
        
        # Key count
        try:
            key_count = len(self.backend.keys())
            lines.append(f'recall_cache_keys_total {key_count}')
        except:
            lines.append(f'recall_cache_keys_total 0')
        
        # Operations
        lines.append(f'recall_cache_operations_total {self._operations}')
        lines.append(f'recall_cache_errors_total {self._errors}')
        
        # Uptime
        lines.append(f'recall_cache_uptime_seconds {time.time() - self._start_time}')
        
        return "\n".join(lines) + "\n"
    
    def get_stats(self) -> dict:
        """Get stats as dictionary."""
        return {
            "operations": self._operations,
            "errors": self._errors,
            "uptime": time.time() - self._start_time,
            "backend": self.backend.health(),
        }
