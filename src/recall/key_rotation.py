"""Key Rotation for recall-cache encryption."""

import os
import json
import time
import shutil
import hashlib
import secrets
from typing import Optional, Dict, Any

from recall.cache import DiskBackend


class KeyRotator:
    """
    Rotate encryption keys for DiskBackend.
    
    Usage:
        from recall.key_rotation import KeyRotator
        
        rotator = KeyRotator(backend, new_key="new-secret")
        rotated = rotator.rotate()  # Re-encrypt all data with new key
    """
    
    def __init__(self, backend: DiskBackend, new_key: str):
        if not hasattr(backend, 'encryption_key'):
            raise ValueError("Backend does not support encryption")
        
        self.backend = backend
        self.old_key = backend.encryption_key
        self.new_key = new_key
    
    def rotate(self) -> int:
        """
        Re-encrypt all data with the new key.
        
        Returns:
            Number of keys re-encrypted
        """
        if not self.old_key:
            # No existing key, just set new one
            self.backend.encryption_key = self.new_key
            return 0
        
        # Get all keys
        keys = self.backend.keys()
        rotated = 0
        
        for key in keys:
            # Temporarily set old key for decryption
            self.backend.encryption_key = self.old_key
            result = self.backend.get(key)
            
            if result:
                expire_time, value = result
                remaining_ttl = expire_time - time.time()
                
                if remaining_ttl > 0:
                    # Set new key for re-encryption
                    self.backend.encryption_key = self.new_key
                    self.backend.set(key, value, remaining_ttl)
                    rotated += 1
        
        # Update key
        self.backend.encryption_key = self.new_key
        return rotated
    
    def verify(self) -> bool:
        """Verify that all data can be decrypted with current key."""
        keys = self.backend.keys()
        
        for key in keys:
            result = self.backend.get(key)
            if result is None:
                return False
        
        return True
