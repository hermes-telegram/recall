"""recall — smart caching for any function, simple as requests."""

from .cache import (
    cache,
    CacheBackend,
    MemoryBackend,
    DiskBackend,
    RedisBackend,
    MultiTierBackend,
    CacheStats,
)

# Admin Panel
from .admin import AdminPanel, start_admin

# Metrics
from .metrics import MetricsCollector

# Logging
from .logging_config import StructuredLogger, get_logger

# Rate Limiting
from .ratelimit import RateLimiter

# Circuit Breaker
from .circuit import CircuitBreaker, CircuitBreakerOpenError

# Audit Logging
from .audit import AuditLogger

# Key Search
from .search import KeySearcher

# Memory Tracking
from .memory import MemoryTracker

# GDPR Compliance
from .gdpr import GDPRManager

# Backup/Restore
from .backup import BackupManager

# Key Rotation
from .key_rotation import KeyRotator

# Multi-Tenancy
from .tenant import TenantManager, TenantBackend

# Cache Warming
from .warming import WarmingScheduler

# Plugins
from .plugins import FastAPICache

# Advanced patterns (20 enterprise features)
from .advanced import (
    RequestCoalescer,
    ProbabilisticEarlyExpiration,
    NegativeCache,
    CachePatterns,
    DependencyInvalidator,
    TransactionIntegration,
    SchemaVersioning,
    HTTPCache,
    CacheControl,
    AdaptiveTTL,
    HotKeyDetector,
    LargeKeyDetector,
    CompressionRatioMonitoring,
    MemoryFragmentationTracker,
    StaleDataDetector,
    StartupWarmer,
    GracefulDegradation,
    IdempotencyKeySupport,
    RequestDeduplication,
    CacheEfficiencyTracker,
)

__all__ = [
    "cache",
    "CacheBackend",
    "MemoryBackend",
    "DiskBackend",
    "RedisBackend",
    "MultiTierBackend",
    "CacheStats",
    "AdminPanel",
    "start_admin",
    "MetricsCollector",
    "StructuredLogger",
    "get_logger",
    "RateLimiter",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "AuditLogger",
    "KeySearcher",
    "MemoryTracker",
    "GDPRManager",
    "BackupManager",
    "KeyRotator",
    "TenantManager",
    "TenantBackend",
    "WarmingScheduler",
    "FastAPICache",
    "RequestCoalescer",
    "ProbabilisticEarlyExpiration",
    "NegativeCache",
    "CachePatterns",
    "DependencyInvalidator",
    "TransactionIntegration",
    "SchemaVersioning",
    "HTTPCache",
    "CacheControl",
    "AdaptiveTTL",
    "HotKeyDetector",
    "LargeKeyDetector",
    "CompressionRatioMonitoring",
    "MemoryFragmentationTracker",
    "StaleDataDetector",
    "StartupWarmer",
    "GracefulDegradation",
    "IdempotencyKeySupport",
    "RequestDeduplication",
    "CacheEfficiencyTracker",
]
__version__ = "2.0.0"
