"""Embedding-layer errors.

Raised by providers, the embedding repository and the embedding service. Error
messages are safe for log/output (no document content, no provider details that
could leak credentials or internal endpoint information).
"""

from __future__ import annotations


class EmbeddingError(Exception):
    """Base class for embedding/vector failures."""


class EmbeddingProviderUnavailableError(EmbeddingError):
    """The configured embedding provider cannot produce vectors right now."""


class EmbeddingDimensionMismatchError(EmbeddingError):
    """A stored vector's dimension does not match the configured model."""