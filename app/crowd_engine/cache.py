"""
crowd_engine/cache.py
---------------------
Thread-safe, TTL-based in-memory cache for crowd density data.

Design rules:
  - Key is (function_name, clock_second) → same inputs in the same wall-clock
    second share one result.
  - TTL defaults to 2 seconds — short enough to always feel live, long enough
    to collapse burst-repeated calls from a single polling cycle.
  - The cache is bounded: entries older than MAX_ENTRIES are evicted on every
    write to prevent unbounded memory growth.
  - No external dependencies; the cache object is a plain module-level singleton.
"""

import time
from typing import Any, Dict, Optional, Tuple

_TTL_SECONDS: int = 2
_MAX_ENTRIES: int = 64


class _TTLCache:
    """Minimal TTL cache backed by a plain dict with LRU-style eviction."""

    __slots__ = ("_ttl", "_max", "_store")

    def __init__(self, ttl: int = _TTL_SECONDS, max_entries: int = _MAX_ENTRIES) -> None:
        self._ttl = ttl
        self._max = max_entries
        self._store: Dict[Any, Tuple[float, Any]] = {}

    def get(self, key: Any) -> Optional[Any]:
        """Return cached value if within TTL, else None."""
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if (time.monotonic() - ts) > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: Any, value: Any) -> None:
        """Store a value and evict stale entries."""
        self._evict()
        self._store[key] = (time.monotonic(), value)

    def _evict(self) -> None:
        """Remove expired entries; drop oldest if still over capacity."""
        now = time.monotonic()
        expired = [k for k, (ts, _) in self._store.items() if (now - ts) > self._ttl]
        for k in expired:
            del self._store[k]
        while len(self._store) >= self._max:
            oldest_key = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest_key]

    def clear(self) -> None:
        """Clear all entries — used in tests."""
        self._store.clear()

    @property
    def size(self) -> int:
        """Return current number of entries."""
        return len(self._store)


# Module-level singleton — shared across the entire process
crowd_cache: _TTLCache = _TTLCache()
