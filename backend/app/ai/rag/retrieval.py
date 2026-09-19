"""Vector retrieval orchestration (retrieval only — no answer generation).

Implements the retrieval pipeline from docs/04_AI/RAG-Architecture.md §9-§13:

    query embedding -> similarity search (ownership-scoped SQL)
    -> metadata filtering -> reranking -> evidence threshold -> context builder

The authenticated ``user_id`` is supplied by the caller from the verified
token and is enforced inside the database function; a query against another
user's chunks returns no rows, never an error.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from app.ai.embeddings.repository import VectorRepository
from app.ai.embeddings.service import EmbeddingService
from app.ai.rag.context import ContextBuilder
from app.ai.rag.models import RetrievalResult, RetrievedChunk
from app.ai.rag.reranking import SimpleReranker


class VectorRetrievalService:
    """Runs one retrieval request end to end for an authenticated user."""

    def __init__(
        self,
        *,
        embeddings: EmbeddingService,
        vectors: VectorRepository,
        context_builder: ContextBuilder,
        top_k: int = 10,
        min_similarity: float = 0.35,
        reranker: SimpleReranker | None = None,
    ) -> None:
        self._embeddings = embeddings
        self._vectors = vectors
        self._context_builder = context_builder
        self._top_k = top_k
        self._min_similarity = min_similarity
        self._reranker = reranker

    def retrieve(
        self,
        *,
        user_id: UUID,
        query: str,
        document_id: UUID | None = None,
        top_k: int | None = None,
        metadata_filter: Mapping[str, object] | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant chunks for *query*, scoped to *user_id*."""
        query_text = query.strip()
        if not query_text:
            raise ValueError("query must not be empty")
        limit = top_k or self._top_k

        query_vector = self._embeddings.embed_query(query_text)
        rows = self._vectors.search(
            user_id=user_id,
            query_embedding=query_vector,
            top_k=limit,
            document_id=document_id,
        )
        chunks = [_to_retrieved_chunk(row) for row in rows]

        chunks = _apply_metadata_filter(chunks, metadata_filter)

        if self._reranker is not None:
            chunks = self._reranker.rerank(chunks, query_text)

        sufficient = [chunk for chunk in chunks if chunk.score >= self._min_similarity]
        if not sufficient:
            return RetrievalResult(
                query=query_text,
                document_id=document_id,
                evidence_state="INSUFFICIENT_EVIDENCE",
                sources=[],
                context=self._context_builder.build([]),
            )
        context = self._context_builder.build(sufficient)
        return RetrievalResult(
            query=query_text,
            document_id=document_id,
            evidence_state="DOCUMENT_GROUNDED",
            sources=sufficient,
            context=context,
        )


def _apply_metadata_filter(
    chunks: list[RetrievedChunk], metadata_filter: Mapping[str, object] | None
) -> list[RetrievedChunk]:
    if not metadata_filter:
        return chunks
    return [
        chunk
        for chunk in chunks
        if all(chunk.metadata.get(key) == value for key, value in metadata_filter.items())
    ]


def _to_retrieved_chunk(row: dict[str, Any]) -> RetrievedChunk:
    similarity = cast("float", row.get("similarity") or 0.0)
    return RetrievedChunk(
        chunk_id=UUID(str(row["id"])),
        document_id=UUID(str(row["document_id"])),
        user_id=UUID(str(row["user_id"])),
        section_id=_uuid_or_none(row.get("section_id")),
        clause_id=_uuid_or_none(row.get("clause_id")),
        chunk_index=int(row.get("chunk_index") or 0),
        content=str(row.get("content") or ""),
        page_start=_int_or_none(row.get("page_start")),
        page_end=_int_or_none(row.get("page_end")),
        token_count=_int_or_none(row.get("token_count")),
        metadata=dict(row.get("metadata") or {}),
        similarity=similarity,
        score=similarity,
        embedding_model=_str_or_none(row.get("embedding_model")),
        embedding_dimension=_int_or_none(row.get("embedding_dimension")),
    )


def _uuid_or_none(value: object) -> UUID | None:
    return UUID(str(value)) if value else None


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    return None


def _str_or_none(value: object) -> str | None:
    return str(value) if value is not None else None