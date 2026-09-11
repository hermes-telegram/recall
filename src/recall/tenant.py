"""Multi-Tenancy support for recall-cache."""

import threading
import time
from typing import Optional, Dict, Any, List

from recall.cache import CacheBackend, MemoryBackend, DiskBackend, RedisBackend, MultiTierBackend


class TenantManager:
    """
    Multi-tenancy support — isolate cache data per tenant.
    
    Usage:
        from recall.tenant import TenantManager
        
        tenants = TenantManager(backend)
        
        # Get tenant-specific operations
        tenant_a = tenants.get_tenant("tenant-a")
        tenant_a.set("key", "value", ttl=60)
    """
    
    def __init__(self, backend: CacheBackend, default_tenant: str = "default"):
        self.backend = backend
        self.default_tenant = default_tenant
        self._tenants: Dict[str, CacheBackend] = {}
        self._lock = threading.Lock()
    
    def get_tenant(self, tenant_id: str) -> 'TenantBackend':
        """Get a tenant-specific backend."""
        with self._lock:
            if tenant_id not in self._tenants:
                self._tenants[tenant_id] = TenantBackend(self.backend, tenant_id)
            return self._tenants[tenant_id]
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete all data for a tenant."""
        with self._lock:
            if tenant_id in self._tenants:
                self._tenants[tenant_id].clear()
                del self._tenants[tenant_id]
                return True
            return False
    
    def get_all_tenants(self) -> List[str]:
        """Get all tenant IDs."""
        with self._lock:
            return list(self._tenants.keys())
    
    def count_tenants(self) -> int:
        """Get number of tenants."""
        with self._lock:
            return len(self._tenants)


class TenantBackend:
    """
    Tenant-specific cache backend wrapper.
    
    All keys are automatically prefixed with the tenant ID.
    """
    
    def __init__(self, backend: CacheBackend, tenant_id: str):
        self.backend = backend
        self.tenant_id = tenant_id
        self.prefix = f"tenant:{tenant_id}:"
    
    def _prefixed_key(self, key: str) -> str:
        return f"{self.prefix}{key}"
    
    def get(self, key: str) -> Optional[tuple[float, Any]]:
        return self.backend.get(self._prefixed_key(key))
    
    def set(self, key: str, value: Any, ttl: float) -> None:
        return self.backend.set(self._prefixed_key(key), value, ttl)
    
    def delete(self, key: str) -> None:
        return self.backend.delete(self._prefixed_key(key))
    
    def clear(self) -> None:
        """Clear all keys for this tenant."""
        keys = self.keys()
        if keys:
            self.backend.delete_many([self._prefixed_key(k) for k in keys])
    
    def keys(self) -> List[str]:
        """Get all keys for this tenant (without prefix)."""
        all_keys = self.backend.keys()
        prefix_len = len(self.prefix)
        return [k[prefix_len:] for k in all_keys if k.startswith(self.prefix)]
    
    def health(self) -> dict:
        return {
            "status": "healthy",
            "type": "tenant",
            "tenant_id": self.tenant_id,
        }
