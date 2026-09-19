"""Vector persistence and similarity search via the Supabase client.

Stores/model metadata are written onto the ``document_chunks`` row
(``embedding``, ``embedding_model``, ``embedding_dimension``). Retrieval runs
the ``public.match_documents`` database function, which filters by
``user_id`` (and optionally ``document_id``) inside SQL so a query can never
return another user's chunks — the server always injects the authenticated
user id itself (docs/04_AI/RAG-Architecture.md §7, Citation-Strategy.md §8).

The vector index is reconciled separately via ``public.ensure_embedding_index``
once the configured model's dimension is confirmed (never hardcoded before).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from supabase import Client

from app.ai.embeddings.errors import EmbeddingError
from app.ai.embeddings.provider import Vector
from app.core.supabase import get_supabase_client

CHUNKS_TABLE = "document_chunks"
MATCH_FUNCTION = "match_documents"
INDEX_FUNCTION = "ensure_embedding_index"


class VectorRepository:
    """pgvector-backed embedding storage and similarity search."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()

    def store_embeddings(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        chunks: Sequence[tuple[int, Vector]],
        model_name: str,
        dimension: int,
    ) -> None:
        """Write one embedding per ``(chunk_index, vector)`` pair.

        Rows are identified by ``document_id`` + ``user_id`` + ``chunk_index``
        (chunk ids are database-generated at insert time).
        """
        for chunk_index, vector in chunks:
            response = (
                self._client.table(CHUNKS_TABLE)
                .update(
                    {
                        "embedding": vector,
                        "embedding_model": model_name,
                        "embedding_dimension": dimension,
                    }
                )
                .eq("document_id", str(document_id))
                .eq("user_id", str(user_id))
                .eq("chunk_index", chunk_index)
                .execute()
            )
            if not (response.data or []):
                raise EmbeddingError(
                    f"A processed chunk could not be found for index {chunk_index}"
                )

    def search(
        self,
        *,
        user_id: UUID,
        query_embedding: Vector,
        top_k: int,
        document_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Return the top-*top_k* chunks for *user_id* by cosine similarity.

        ``document_id`` is an additional filter when the caller requires a
        specific document; user ownership is always enforced inside SQL.
        """
        if top_k < 1:
            raise ValueError("top_k must be a positive integer")
        params: dict[str, Any] = {
            "query_embedding": query_embedding,
            "match_count": top_k,
            "p_user_id": str(user_id),
        }
        if document_id is not None:
            params["p_document_id"] = str(document_id)
        response = self._client.rpc(MATCH_FUNCTION, params).execute()
        rows = cast("list[dict[str, Any]]", response.data or [])
        return rows

    def ensure_embedding_index(self, *, dimension: int) -> None:
        """Confirm the vector dimension and build/lock the HNSW cosine index.

        Idempotent; call after the embedding model + dimension are configured.
        """
        if dimension < 1:
            raise ValueError("dimension must be a positive integer")
        self._client.rpc(INDEX_FUNCTION, {"dim": dimension}).execute()

    def chunk_entities(self, document_id: UUID) -> list[dict[str, Any]]:
        """Return per-chunk source rows (with entity metadata) for a document.

        Used by the document-understanding read model to build page-referenced
        important dates and monetary terms from deterministic extraction.
        """
        response = (
            self._client.table(CHUNKS_TABLE)
            .select("id", "clause_id", "content", "page_start", "page_end", "metadata")
            .eq("document_id", str(document_id))
            .order("chunk_index", desc=False)
            .execute()
        )
        return cast("list[dict[str, Any]]", response.data or [])