"""Shared AI-provider call policy: retries, rate limiting, retryable states.

Both ``app.ai.llm`` and ``app.ai.embeddings`` providers implement the same call
policy against backend-only endpoints:

* **Timeout** — configured per provider and enforced by the HTTP client.
* **Retry policy** — exponential backoff with an optional jitter, applied only
  to transient failures (connection/transport errors, 5xx, 429).
* **Rate limit** — optional client-side minimum-interval throttle (0 = off) so
  the application respects upstream quotas and controls cost.

Nothing in this module performs any AI work; it only shapes how the providers
talk to their upstreams (docs/04_AI/AI-Architecture.md §21, Cost Control).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

_Monotonic = Callable[[], float]
_Sleeper = Callable[[float], None]


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential-backoff retry policy for transient provider failures.

    ``max_attempts`` counts the total HTTP attempts (1 = no retries). Delays are
    capped at ``max_delay_seconds`` and an optional fixed ``jitter_seconds`` is
    added to avoid thundering-herd synchronized retries.
    """

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 10.0
    jitter_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must not be negative")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be >= base_delay_seconds")
        if self.jitter_seconds < 0:
            raise ValueError("jitter_seconds must not be negative")

    def delay_for(self, attempt_index: int) -> float:
        """Backoff delay *before* a given retry attempt (1-based index)."""
        if attempt_index < 1:
            return 0.0
        backoff: float = min(
            self.base_delay_seconds * (2 ** (attempt_index - 1)),
            self.max_delay_seconds,
        )
        return backoff + self.jitter_seconds


def is_retryable_status(status: int) -> bool:
    """True when a status code signals a transient upstream condition."""
    return status == 429 or status >= 500


class RequestThrottle:
    """Blocking minimum-interval throttle between upstream calls.

    ``requests_per_minute > 0`` enforces that spacing; ``0`` disables the
    throttle entirely. The clock and sleep are injectable for hermetic tests.
    Safe for single-worker use; the lock preserves the invariant under
    concurrency.
    """

    def __init__(
        self,
        requests_per_minute: float = 0.0,
        *,
        monotonic: _Monotonic = time.monotonic,
        sleeper: _Sleeper = time.sleep,
    ) -> None:
        if requests_per_minute < 0:
            raise ValueError("requests_per_minute must not be negative")
        self._interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0.0
        self._next_allowed: float = 0.0
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._lock = Lock()

    def wait(self) -> None:
        """Block until a request slot is available, then consume it."""
        if self._interval <= 0.0:
            return
        with self._lock:
            now = self._monotonic()
            if now < self._next_allowed:
                self._sleeper(self._next_allowed - now)
                now = self._monotonic()
            self._next_allowed = now + self._interval