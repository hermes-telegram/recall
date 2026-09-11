"""GDPR Compliance for recall-cache."""

import time
import threading
from typing import Optional, List, Dict, Any, Callable

from recall.cache import CacheBackend


class GDPRManager:
    """
    GDPR compliance manager for cache.
    
    Implements "Right to be Forgotten" — complete deletion of user data.
    
    Usage:
        from recall.gdpr import GDPRManager
        
        gdpr = GDPRManager(backend)
        
        # Track user data
        gdpr.track_user("user123", ["user:123:profile", "user:123:posts"])
        
        # Delete all user data (right to be forgotten)
        deleted = gdpr.forget_user("user123")
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._user_index: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
    
    def track_user(self, user_id: str, keys: List[str]):
        """Track keys belonging to a user."""
        with self._lock:
            if user_id not in self._user_index:
                self._user_index[user_id] = []
            self._user_index[user_id].extend(keys)
            # Remove duplicates
            self._user_index[user_id] = list(set(self._user_index[user_id]))
    
    def forget_user(self, user_id: str) -> int:
        """
        Delete all data for a user (Right to be Forgotten).
        
        Returns:
            Number of keys deleted
        """
        with self._lock:
            keys = self._user_index.get(user_id, [])
        
        if keys:
            self.backend.delete_many(keys)
        
        with self._lock:
            del self._user_index[user_id]
        
        return len(keys)
    
    def get_user_keys(self, user_id: str) -> List[str]:
        """Get all tracked keys for a user."""
        with self._lock:
            return self._user_index.get(user_id, [])
    
    def get_all_users(self) -> List[str]:
        """Get all tracked user IDs."""
        with self._lock:
            return list(self._user_index.keys())
    
    def forget_all(self) -> int:
        """Delete all tracked user data."""
        total = 0
        with self._lock:
            users = list(self._user_index.keys())
        
        for user_id in users:
            total += self.forget_user(user_id)
        
        return total
