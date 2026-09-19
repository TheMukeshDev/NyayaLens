"""Citation persistence: owner-scoped chunk resolution for validated citations.

Document-grounded Q&A resolves every citation against the backend's own data
(docs/04_AI/CITATION-Strategy.md §7-§8, API-Specification.md §15-§16). A cited
chunk is accepted only when it exists, belongs to the requested document,
belongs to the authenticated user and carries section/page metadata.

``document_chunks`` rows carry ``user_id`` — the document owner, denormalized
at processing time — so one owner-scoped query proves existence, document
membership and ownership in SQL at the same time. The service-role key bypasses
RLS, so this scoping is a security boundary, not a convenience
(docs/05_SECURITY/SECURITY-Architecture.md §5).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from app.core.supabase import get_supabase_client
from app.repositories.base import BaseRepository

CHUNKS_TABLE = "document_chunks"

_CHUNK_COLUMNS = (
    "id",
    "document_id",
    "user_id",
    "section_id",
    "clause_id",
    "page_start",
    "page_end",
    "content",
    "metadata",
)


class CitationRepository(BaseRepository):
    """Owner-scoped resolution of cited chunks against ``document_chunks``."""

    table = CHUNKS_TABLE

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or get_supabase_client()

    def owned_chunks(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        chunk_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        """Return owned ``document_chunks`` rows whose ids are in *chunk_ids*.

        Empty or duplicated ``chunk_ids`` short-circuit to an empty list so no
        query is issued and no rows are accidentally returned.
        """
        ids = list(dict.fromkeys(str(chunk_id) for chunk_id in chunk_ids))
        if not ids:
            return []
        response = (
            self._client.table(self.table)
            .select(*_CHUNK_COLUMNS)
            .eq("user_id", str(user_id))
            .eq("document_id", str(document_id))
            .in_("id", ids)
            .execute()
        )
        rows = response.data or []
        return [cast("dict[str, Any]", row) for row in rows]