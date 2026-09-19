"""LLM-layer errors.

Every failure is surfaced as a controlled, typed error with a safe message:
no stack traces, no API keys, no URLs and no document content are included in
message text. Callers (and future API handlers) can map these to a stable
error envelope without leaking provider details.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base class for all LLM provider failures."""


class LLMProviderUnavailableError(LLMError):
    """The configured LLM provider cannot complete a generation right now.

    Raised when the provider is unreachable, returns an invalid response, or is
    not configured. Never results in a fabricated answer.
    """


class LLMRateLimitError(LLMError):
    """The upstream rejected a request as rate-limited (HTTP 429)."""


class LLMTimeoutError(LLMError):
    """A request exceeded the configured timeout (treated as retryable)."""


class LLMOutputValidationError(LLMError):
    """The provider returned text that did not validate against the schema.

    Raised instead of blindly accepting malformed structured output
    (docs/04_AI/PROMPT-Strategy.md §18).
    """