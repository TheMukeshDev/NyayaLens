"""Embedding layer: provider abstraction, pgvector persistence, orchestration.

Satisfies the RAG indexing half of the pipeline
(docs/04_AI/AI-Architecture.md §16, RAG-Architecture.md §6):

    chunk -> embedding -> vector storage

* ``provider`` — model-agnostic embedding providers.
* ``repository`` — pgvector storage + ownership-scoped similarity search.
* ``service`` — embeds document chunks and query texts.
"""

from __future__ import annotations

from app.ai.embeddings.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingError,
    EmbeddingProviderUnavailableError,
)
from app.ai.embeddings.provider import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    Vector,
    build_embedding_provider,
)
from app.ai.embeddings.repository import VectorRepository
from app.ai.embeddings.service import EmbeddingService

__all__ = [
    "DeterministicEmbeddingProvider",
    "EmbeddingDimensionMismatchError",
    "EmbeddingError",
    "EmbeddingProvider",
    "EmbeddingProviderUnavailableError",
    "EmbeddingService",
    "OpenAICompatibleEmbeddingProvider",
    "Vector",
    "VectorRepository",
    "build_embedding_provider",
]