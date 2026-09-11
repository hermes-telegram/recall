"""Key Pattern Search for recall-cache."""

import re
from typing import List, Optional, Set
from recall.cache import CacheBackend


class KeySearcher:
    """
    Search cache keys using regex patterns.
    
    Usage:
        from recall.search import KeySearcher
        
        searcher = KeySearcher(backend)
        keys = searcher.search("user:*")  # All keys starting with "user:"
        keys = searcher.search(".*:123:.*")  # All keys containing ":123:"
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def search(self, pattern: str, limit: int = 100) -> List[str]:
        """Search keys matching a regex pattern."""
        try:
            all_keys = self.backend.keys()
        except Exception:
            return []
        
        regex = re.compile(pattern)
        matches = [k for k in all_keys if regex.match(k)]
        return matches[:limit]
    
    def search_contains(self, substring: str, limit: int = 100) -> List[str]:
        """Search keys containing a substring."""
        try:
            all_keys = self.backend.keys()
        except Exception:
            return []
        
        matches = [k for k in all_keys if substring in k]
        return matches[:limit]
    
    def search_by_prefix(self, prefix: str, limit: int = 100) -> List[str]:
        """Search keys by prefix."""
        try:
            all_keys = self.backend.keys()
        except Exception:
            return []
        
        matches = [k for k in all_keys if k.startswith(prefix)]
        return matches[:limit]
    
    def search_by_suffix(self, suffix: str, limit: int = 100) -> List[str]:
        """Search keys by suffix."""
        try:
            all_keys = self.backend.keys()
        except Exception:
            return []
        
        matches = [k for k in all_keys if k.endswith(suffix)]
        return matches[:limit]
    
    def count_by_pattern(self, pattern: str) -> int:
        """Count keys matching a pattern."""
        return len(self.search(pattern, limit=float('inf')))
    
    def delete_by_pattern(self, pattern: str, confirm: bool = False) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Regex pattern
            confirm: Must be True to actually delete
        """
        if not confirm:
            return 0
        
        keys = self.search(pattern, limit=float('inf'))
        self.backend.delete_many(keys)
        return len(keys)
    
    def get_stats_by_pattern(self, pattern: str) -> dict:
        """Get statistics about keys matching a pattern."""
        keys = self.search(pattern, limit=float('inf'))
        return {
            "pattern": pattern,
            "count": len(keys),
            "sample": keys[:10],
        }
