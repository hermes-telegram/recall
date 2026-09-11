"""Backup and Restore for recall-cache."""

import json
import time
import os
import shutil
from typing import Optional, Dict, Any

from recall.cache import CacheBackend


class BackupManager:
    """
    Backup and restore cache data.
    
    Usage:
        from recall.backup import BackupManager
        
        backup = BackupManager(backend)
        
        # Create backup
        backup.backup_to_file("/tmp/cache_backup.json")
        
        # Restore from backup
        backup.restore_from_file("/tmp/cache_backup.json")
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
    
    def backup_to_file(self, filepath: str) -> int:
        """
        Backup all cache data to a JSON file.
        
        Returns:
            Number of keys backed up
        """
        keys = self.backend.keys()
        data = {}
        
        for key in keys:
            result = self.backend.get(key)
            if result:
                expire_time, value = result
                data[key] = {
                    "value": value,
                    "expire_time": expire_time,
                    "ttl": expire_time - time.time(),
                }
        
        with open(filepath, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "key_count": len(data),
                "data": data,
            }, f, indent=2, default=str)
        
        return len(data)
    
    def restore_from_file(self, filepath: str, overwrite: bool = False) -> int:
        """
        Restore cache data from a JSON file.
        
        Args:
            filepath: Path to backup file
            overwrite: If True, overwrite existing keys
            
        Returns:
            Number of keys restored
        """
        with open(filepath, "r") as f:
            backup = json.load(f)
        
        data = backup.get("data", {})
        restored = 0
        
        for key, item in data.items():
            if not overwrite and self.backend.get(key):
                continue
            
            ttl = item.get("ttl", 0)
            if ttl > 0:
                self.backend.set(key, item["value"], ttl)
                restored += 1
        
        return restored
    
    def backup_to_directory(self, directory: str) -> int:
        """Backup to a directory (one file per key)."""
        os.makedirs(directory, exist_ok=True)
        keys = self.backend.keys()
        
        for key in keys:
            result = self.backend.get(key)
            if result:
                expire_time, value = result
                safe_key = key.replace(":", "_").replace("/", "_")
                filepath = os.path.join(directory, f"{safe_key}.json")
                
                with open(filepath, "w") as f:
                    json.dump({
                        "key": key,
                        "value": value,
                        "expire_time": expire_time,
                    }, f, default=str)
        
        return len(keys)
    
    def restore_from_directory(self, directory: str) -> int:
        """Restore from a directory."""
        restored = 0
        
        for filename in os.listdir(directory):
            if not filename.endswith(".json"):
                continue
            
            filepath = os.path.join(directory, filename)
            with open(filepath, "r") as f:
                item = json.load(f)
            
            ttl = item.get("expire_time", 0) - time.time()
            if ttl > 0:
                self.backend.set(item["key"], item["value"], ttl)
                restored += 1
        
        return restored
