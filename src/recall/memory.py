"""Memory Usage Tracking for recall-cache."""

import sys
import threading
import time
from typing import Dict, Any, Optional

from recall.cache import CacheBackend


class MemoryTracker:
    """
    Track memory usage of cache backends.
    
    Usage:
        from recall.memory import MemoryTracker
        
        tracker = MemoryTracker(backend)
        stats = tracker.get_stats()
        print(f"Memory usage: {stats['total_bytes']} bytes")
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._snapshots: list = []
        self._lock = threading.Lock()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        try:
            keys = self.backend.keys()
            key_count = len(keys)
        except:
            key_count = 0
        
        # Estimate memory usage
        total_bytes = sys.getsizeof(keys)
        
        # Try to get more specific stats
        health = self.backend.health()
        
        # For memory backend, try to get internal cache size
        if hasattr(self.backend, '_cache'):
            total_bytes += sys.getsizeof(self.backend._cache)
        
        # For disk backend, get total file size
        if hasattr(self.backend, 'directory'):
            try:
                import os
                for f in os.listdir(self.backend.directory):
                    path = os.path.join(self.backend.directory, f)
                    total_bytes += os.path.getsize(path)
            except:
                pass
        
        return {
            "key_count": key_count,
            "estimated_bytes": total_bytes,
            "backend_type": health.get("type", "unknown"),
            "timestamp": time.time(),
        }
    
    def take_snapshot(self) -> Dict[str, Any]:
        """Take a snapshot of current memory usage."""
        snapshot = self.get_stats()
        with self._lock:
            self._snapshots.append(snapshot)
            # Keep only last 100 snapshots
            if len(self._snapshots) > 100:
                self._snapshots = self._snapshots[-100:]
        return snapshot
    
    def get_snapshots(self, limit: int = 10) -> list:
        """Get recent snapshots."""
        with self._lock:
            return self._snapshots[-limit:]
    
    def get_trend(self) -> Dict[str, Any]:
        """Get memory usage trend."""
        with self._lock:
            if len(self._snapshots) < 2:
                return {"trend": "insufficient_data"}
            
            first = self._snapshots[0]
            last = self._snapshots[-1]
            
            bytes_diff = last["estimated_bytes"] - first["estimated_bytes"]
            keys_diff = last["key_count"] - first["key_count"]
            time_diff = last["timestamp"] - first["timestamp"]
            
            return {
                "trend": "growing" if bytes_diff > 0 else "shrinking" if bytes_diff < 0 else "stable",
                "bytes_change": bytes_diff,
                "keys_change": keys_diff,
                "time_span": time_diff,
                "snapshots_count": len(self._snapshots),
            }
