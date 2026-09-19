"""Persistence of extraction output (sections, clauses, chunks).

Writing follows a delete-then-insert strategy so processing is idempotent: a
retried/reprocessed document never accumulates stale fragments. Chunks are
written as plain text rows first; embeddings and their model metadata are
stored on top by the embedding layer (``app.ai.embeddings``). Chunk ownership
is denormalized onto each row (``user_id``) so similarity search can be
filtered by owner in SQL (migration 20260917000300).
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from supabase import Client

from app.core.supabase import get_supabase_client
from app.document_processing.models import (
    ExtractedChunk,
    ExtractedClause,
    ExtractedSection,
)

TABLES = ("sections", "clauses", "document_chunks")


class ProcessingRepository:
    """Insert/replace pipeline output for a document."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()

    def replace(
        self,
        document_id: UUID,
        *,
        user_id: UUID,
        sections: list[ExtractedSection],
        clauses: list[ExtractedClause],
        chunks: list[ExtractedChunk],
    ) -> None:
        """Replace all processing artifacts for *document_id* (idempotent)."""
        self.delete_for_document(document_id)
        self._insert_sections(document_id, sections)
        self._insert_clauses(document_id, clauses)
        self._insert_chunks(document_id, user_id, chunks)

    def delete_for_document(self, document_id: UUID) -> None:
        """Remove every stored artifact for *document_id* (no-op if none)."""
        for table in TABLES:
            self._client.table(table).delete().eq("document_id", str(document_id)).execute()

    # -- reads ---------------------------------------------------------------

    def list_sections(self, document_id: UUID) -> list[dict[str, Any]]:
        """Return a document's sections in document order (row dicts)."""
        response = (
            self._client.table("sections")
            .select("*")
            .eq("document_id", str(document_id))
            .order("sequence_number", desc=False)
            .execute()
        )
        return cast("list[dict[str, Any]]", response.data or [])

    def list_clauses(self, document_id: UUID) -> list[dict[str, Any]]:
        """Return a document's clauses in document order (row dicts)."""
        response = (
            self._client.table("clauses")
            .select("*")
            .eq("document_id", str(document_id))
            .order("sequence_number", desc=False)
            .execute()
        )
        return cast("list[dict[str, Any]]", response.data or [])

    # -- inserts ------------------------------------------------------------

    def _insert_sections(self, document_id: UUID, sections: list[ExtractedSection]) -> None:
        rows: list[dict[str, Any]] = []
        for section in sections:
            assert section.id is not None, "sections must carry ids before persistence"
            rows.append(
                {
                    "id": str(section.id),
                    "document_id": str(document_id),
                    "section_number": section.number,
                    "title": section.title,
                    "content": section.content,
                    "page_start": section.page_start,
                    "page_end": section.page_end,
                    "parent_section_id": (
                        str(section.parent_section_id) if section.parent_section_id else None
                    ),
                    "sequence_number": section.sequence,
                }
            )
        if rows:
            self._client.table("sections").insert(rows).execute()

    def _insert_clauses(self, document_id: UUID, clauses: list[ExtractedClause]) -> None:
        rows: list[dict[str, Any]] = []
        for clause in clauses:
            assert clause.id is not None, "clauses must carry ids before persistence"
            rows.append(
                {
                    "id": str(clause.id),
                    "document_id": str(document_id),
                    "section_id": str(clause.section_id) if clause.section_id else None,
                    "clause_number": clause.number,
                    "clause_type": clause.clause_type,
                    "title": clause.title,
                    "content": clause.content,
                    "page_start": clause.page_start,
                    "page_end": clause.page_end,
                    "sequence_number": clause.sequence,
                    "extraction_confidence": clause.confidence,
                }
            )
        if rows:
            self._client.table("clauses").insert(rows).execute()

    def _insert_chunks(
        self, document_id: UUID, user_id: UUID, chunks: list[ExtractedChunk]
    ) -> None:
        rows: list[dict[str, Any]] = [
            {
                "document_id": str(document_id),
                "user_id": str(user_id),
                "section_id": str(chunk.section_id) if chunk.section_id else None,
                "clause_id": str(chunk.clause_id) if chunk.clause_id else None,
                "chunk_index": chunk.index,
                "content": chunk.content,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]
        if rows:
            self._client.table("document_chunks").insert(rows).execute()