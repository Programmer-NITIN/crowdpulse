"""
middleware/rate_limiter.py
--------------------------
Sliding-window rate limiter using collections.deque.

Design:
  - Each rate limiter tracks request timestamps per IP.
  - Sliding window: only timestamps within the last `window_seconds` count.
  - Returns 429 with Retry-After header when exceeded.
  - Test-safe: store.clear() resets all buckets.
"""

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Request, HTTPException


class _SlidingWindowRateLimiter:
    """Per-IP sliding window counter backed by deques."""

    __slots__ = ("max_requests", "window_seconds", "store")

    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.store: defaultdict[str, Deque[float]] = defaultdict(deque)

    def _get_client_ip(self, request: Request) -> str:
        """Extract the client IP, respecting X-Forwarded-For for Cloud Run."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "0.0.0.0"

    def _prune(self, window: Deque[float], now: float) -> None:
        """Remove timestamps older than the sliding window."""
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()

    async def __call__(self, request: Request) -> None:
        """FastAPI dependency — raises 429 if limit is exceeded."""
        ip = self._get_client_ip(request)
        now = time.time()
        window = self.store[ip]
        self._prune(window, now)

        if len(window) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests — please wait and try again.",
                headers={"Retry-After": str(self.window_seconds)},
            )

        window.append(now)

    async def is_rate_limited(self, request: Request) -> bool:
        """Check if the given IP would be rate-limited (non-raising).

        Returns True if the request would be rejected, False otherwise.
        """
        ip = self._get_client_ip(request)
        now = time.time()
        window = self.store[ip]
        self._prune(window, now)
        return len(window) >= self.max_requests


def make_rate_limiter(
    max_requests: int,
    window_seconds: int = 60,
) -> _SlidingWindowRateLimiter:
    """Factory for creating per-route rate limiters.

    Returns:
        A callable FastAPI dependency that enforces the rate limit.
    """
    return _SlidingWindowRateLimiter(max_requests, window_seconds)


# ── Pre-configured limiters ──────────────────────────────────────────────────
navigation_rate_limit = make_rate_limiter(max_requests=10, window_seconds=60)
chat_rate_limit = make_rate_limiter(max_requests=20, window_seconds=60)
analytics_rate_limit = make_rate_limiter(max_requests=15, window_seconds=60)
crowd_rate_limit = make_rate_limiter(max_requests=30, window_seconds=60)
