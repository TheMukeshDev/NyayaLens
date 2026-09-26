"""In-memory rate limiting middleware with sliding window algorithm.

Enforces per-client and per-user request rate limits (docs/05_SECURITY/SECURITY-Architecture.md §18).
Protects system resources against request flooding, DoS, and runaway automated clients.

Resource & Memory Guarantees:
* O(1) sliding window check per request.
* Bounded memory footprint: stale client entries are evicted on a periodic interval.
* Zero external dependencies (Redis not required for single-worker / serverless runtime).
* Clean JSON error envelope with standard error code RATE_LIMITED and Retry-After header.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Final

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.errors import ErrorCodes, error_payload

# Default limits (requests per minute)
DEFAULT_RATE_LIMIT_PER_MINUTE: Final[int] = 120
UPLOAD_RATE_LIMIT_PER_MINUTE: Final[int] = 30
AI_RATE_LIMIT_PER_MINUTE: Final[int] = 60
_CLEANUP_INTERVAL_SECONDS: Final[float] = 60.0
_MAX_TRACKED_CLIENTS: Final[int] = 10000


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter with automatic stale-entry eviction."""

    def __init__(
        self,
        default_limit_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE,
        *,
        enabled: bool = True,
    ) -> None:
        self.default_limit = default_limit_per_minute
        self.enabled = enabled
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._last_cleanup = time.monotonic()

    def is_rate_limited(
        self,
        key: str,
        limit_per_minute: int | None = None,
        now: float | None = None,
    ) -> tuple[bool, int]:
        """Check if *key* has exceeded the request quota in the past 60 seconds.

        Returns (is_limited, retry_after_seconds).
        """
        if not self.enabled:
            return False, 0

        limit = limit_per_minute or self.default_limit
        if limit <= 0:
            return False, 0

        current_time = now if now is not None else time.monotonic()
        window_start = current_time - 60.0

        with self._lock:
            # Evict stale tracking records periodically
            if current_time - self._last_cleanup > _CLEANUP_INTERVAL_SECONDS:
                self._cleanup(window_start)
                self._last_cleanup = current_time

            # Safety cap to prevent memory bloat under massive client IP rotation
            if len(self._requests) > _MAX_TRACKED_CLIENTS:
                self._cleanup(window_start)

            timestamps = self._requests[key]
            # Discard timestamps outside the 60-second window
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()

            if len(timestamps) >= limit:
                oldest_timestamp = timestamps[0]
                retry_after = max(1, int(oldest_timestamp + 60.0 - current_time))
                return True, retry_after

            timestamps.append(current_time)
            return False, 0

    def _cleanup(self, window_start: float) -> None:
        """Prune empty or fully expired deques to keep memory bounded."""
        stale_keys = [
            key
            for key, timestamps in self._requests.items()
            if not timestamps or timestamps[-1] < window_start
        ]
        for key in stale_keys:
            del self._requests[key]

    def reset(self) -> None:
        """Clear all tracked request counters (useful for unit tests)."""
        with self._lock:
            self._requests.clear()
            self._last_cleanup = time.monotonic()


# Global limiter instance
rate_limiter = SlidingWindowRateLimiter()


def get_client_identifier(request: Request) -> str:
    """Derive unique client identifier from auth token or IP address."""
    # If Authorization header exists, use token signature segment for per-user isolation
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        parts = token.split(".")
        if len(parts) == 3:
            return f"user:{parts[2]}"  # Use signature part
        return f"token:{token[:32]}"

    # Fall back to client IP address
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client and request.client.host:
        client_ip = request.client.host
    else:
        client_ip = "127.0.0.1"
    return f"ip:{client_ip}"


def get_route_limit(path: str) -> int:
    """Determine the rate limit budget for a given request path."""
    if path.startswith("/api/v1/documents/upload-intent") or path.endswith("/process"):
        return UPLOAD_RATE_LIMIT_PER_MINUTE
    if any(
        endpoint in path
        for endpoint in ("/qa", "/ask", "/comparisons", "/action-center", "/reports")
    ):
        return AI_RATE_LIMIT_PER_MINUTE
    return DEFAULT_RATE_LIMIT_PER_MINUTE


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces rate limits on incoming API requests with proper Retry-After headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Bypass rate limiting for health probes and static docs
        if path in ("/health", "/api/v1/health", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"):
            return await call_next(request)

        # In testing environments, if rate limiting is disabled, pass through
        if not rate_limiter.enabled:
            return await call_next(request)

        client_key = get_client_identifier(request)
        route_limit = get_route_limit(path)

        is_limited, retry_after = rate_limiter.is_rate_limited(client_key, route_limit)
        if is_limited:
            response_content = error_payload(
                ErrorCodes.RATE_LIMITED,
                f"Rate limit exceeded. Too many requests. Please wait {retry_after} seconds before retrying.",
            )
            return JSONResponse(
                status_code=429,
                content=response_content,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(route_limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(route_limit)
        return response
