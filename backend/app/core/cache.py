"""In-memory bounded LRU / TTL caching layer for performance and efficiency.

Provides thread-safe caching for expensive computational operations:
* Document query embeddings (O(1) repeat query vector lookup)
* Extracted clause tokens and pre-computed text hashes
* Intermediate analysis structures

Memory Guarantees:
* Strict maxsize bound (default 2048 entries) to prevent memory growth.
* Automatic TTL expiration to prevent stale data retention.
* Least-Recently-Used (LRU) eviction when capacity is reached.
* Constant time O(1) get and put operations.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Generic, TypeVar

T = TypeVar("T")

DEFAULT_MAX_CACHE_SIZE = 2048
DEFAULT_TTL_SECONDS = 3600.0  # 1 hour


class BoundedLRUCache(Generic[T]):
    """Thread-safe bounded LRU cache with TTL eviction."""

    def __init__(
        self,
        maxsize: int = DEFAULT_MAX_CACHE_SIZE,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._maxsize = max(1, maxsize)
        self._ttl_seconds = max(0.0, ttl_seconds)
        self._cache: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> T | None:
        """Retrieve an entry by key if it exists and has not expired."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            created_at, value = self._cache[key]
            now = time.monotonic()
            if self._ttl_seconds > 0 and (now - created_at) > self._ttl_seconds:
                # Expired
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: T) -> None:
        """Store an entry, evicting the least recently used item if at capacity."""
        with self._lock:
            now = time.monotonic()
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (now, value)

            # Evict oldest entry if size exceeds limit
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def invalidate(self, key: str) -> bool:
        """Remove a specific key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cached entries and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache hit/miss statistics and current utilization."""
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = (self._hits / total) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": round(hit_ratio, 4),
            }


# Global caches for high-impact repetitive operations
embedding_cache: BoundedLRUCache[list[float]] = BoundedLRUCache(maxsize=4096, ttl_seconds=7200.0)
query_cache: BoundedLRUCache[Any] = BoundedLRUCache(maxsize=1024, ttl_seconds=1800.0)
