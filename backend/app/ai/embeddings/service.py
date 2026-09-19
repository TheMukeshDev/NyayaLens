"""Embedding service: document indexing and query embedding.

Bridges the deterministic/extraction pipeline and pgvector:

    chunk -> embed -> vector storage

:class:`EmbeddingService.index_document` embeds every chunk of a processed
document and persists the vectors with their model metadata, so retrieval can
run as soon as processing finishes. Query embedding is a separate, small call.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.embeddings.provider import EmbeddingProvider, Vector
from app.ai.embeddings.repository import VectorRepository
from app.document_processing.models import ExtractedChunk


class EmbeddingService:
    """Embeds document chunks and queries against the configured provider."""

    def __init__(self, *, provider: EmbeddingProvider, vectors: VectorRepository) -> None:
        self._provider = provider
        self._vectors = vectors

    @property
    def model_name(self) -> str:
        """Name of the configured embedding model (recorded per chunk)."""
        return self._provider.model_name

    def embed_query(self, text: str) -> Vector:
        """Embed a single user question (never shared across users)."""
        return self._provider.embed_one(text)

    def index_document(
        self, *, document_id: UUID, user_id: UUID, chunks: list[ExtractedChunk]
    ) -> int:
        """Embed and store every chunk of one document; returns chunk count.

        The ``user_id`` here comes from the documents row owned by the uploader
        — never from request input — and is stored beside each vector so all
        later retrieval is ownership-scoped.
        """
        if not chunks:
            return 0
        vectors = self._provider.embed([chunk.content for chunk in chunks])
        self._vectors.store_embeddings(
            document_id=document_id,
            user_id=user_id,
            chunks=[(chunk.index, vector) for chunk, vector in zip(chunks, vectors, strict=True)],
            model_name=self._provider.model_name,
            dimension=self._provider.dimension,
        )
        return len(chunks)