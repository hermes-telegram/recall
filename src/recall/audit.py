"""Audit Logging for recall-cache."""

import time
import threading
import json
from typing import Optional, List, Dict, Any


class AuditLogger:
    """
    Audit logger for cache operations.
    
    Tracks who did what and when — essential for compliance.
    
    Usage:
        from recall.audit import AuditLogger
        
        audit = AuditLogger()
        audit.log("cache_clear", user="admin", details="Cleared all cache")
    """
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._entries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def log(self, action: str, user: str = "system", details: str = "", **kwargs):
        """Log an audit entry."""
        with self._lock:
            entry = {
                "timestamp": time.time(),
                "action": action,
                "user": user,
                "details": details,
                **kwargs
            }
            self._entries.append(entry)
            
            # Trim if too many
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries:]
    
    def get_entries(
        self,
        limit: int = 100,
        action: Optional[str] = None,
        user: Optional[str] = None,
        since: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Get audit entries with optional filtering."""
        with self._lock:
            entries = self._entries[:]
        
        if action:
            entries = [e for e in entries if e["action"] == action]
        if user:
            entries = [e for e in entries if e["user"] == user]
        if since:
            entries = [e for e in entries if e["timestamp"] >= since]
        
        return entries[-limit:]
    
    def clear(self):
        """Clear all audit entries."""
        with self._lock:
            self._entries.clear()
    
    @property
    def count(self) -> int:
        return len(self._entries)
