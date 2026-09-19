"""Persistence and reads for AI document understanding.

Writes validated AI outputs to ``analyses`` (JSONB result + provenance) and
normalized review signals to ``attention_items`` (Database-Schema.md §9). The
write path is delete-then-insert per document so reprocessing is idempotent;
attention rows cascade when their analysis row is deleted (FK ``ON DELETE
CASCADE``). Ownership is derived from the document row (RLS via
``public.is_document_owner``); this repository uses the service-role client and
therefore scopes by document only.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from supabase import Client

from app.core.supabase import get_supabase_client

ANALYSES_TABLE = "analyses"
ATTENTION_TABLE = "attention_items"


class AnalysisRepository:
    """Owner-bound access to ``analyses`` and ``attention_items``."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()

    def create(
        self,
        *,
        document_id: UUID,
        analysis_type: str,
        model_name: str | None,
        prompt_version: str | None,
        status: str,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
        completed_at: str | None = None,
    ) -> dict[str, Any]:
        """Insert one analysis row and return it (validated payload only)."""
        payload: dict[str, Any] = {
            "document_id": str(document_id),
            "analysis_type": analysis_type,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "status": status,
            "result": result,
            "error_message": error_message,
            "completed_at": completed_at,
        }
        response = self._client.table(ANALYSES_TABLE).insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError("analysis create returned no rows")
        return cast("dict[str, Any]", rows[0])

    def delete_for_document(self, document_id: UUID) -> None:
        """Remove every analysis (and its attention items) for a document."""
        (
            self._client.table(ATTENTION_TABLE)
            .delete()
            .eq("document_id", str(document_id))
            .execute()
        )
        (
            self._client.table(ANALYSES_TABLE)
            .delete()
            .eq("document_id", str(document_id))
            .execute()
        )

    def latest(self, document_id: UUID, analysis_type: str) -> dict[str, Any] | None:
        """Return the most recently created analysis row of *analysis_type*."""
        response = (
            self._client.table(ANALYSES_TABLE)
            .select("*")
            .eq("document_id", str(document_id))
            .eq("analysis_type", analysis_type)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return cast("dict[str, Any] | None", rows[0] if rows else None)

    def replace_attention_items(
        self,
        *,
        document_id: UUID,
        analysis_id: UUID,
        items: list[dict[str, Any]],
    ) -> None:
        """Replace the attention items of one analysis (idempotent)."""
        (
            self._client.table(ATTENTION_TABLE)
            .delete()
            .eq("document_id", str(document_id))
            .eq("analysis_id", str(analysis_id))
            .execute()
        )
        if not items:
            return
        rows: list[dict[str, Any]] = []
        for item in items:
            row = dict(item)
            row["analysis_id"] = str(analysis_id)
            row["document_id"] = str(document_id)
            rows.append(row)
        self._client.table(ATTENTION_TABLE).insert(rows).execute()

    def attention_items_for(self, document_id: UUID) -> list[dict[str, Any]]:
        """Return every attention item for a document, oldest first."""
        response = (
            self._client.table(ATTENTION_TABLE)
            .select("*")
            .eq("document_id", str(document_id))
            .order("created_at", desc=False)
            .execute()
        )
        return cast("list[dict[str, Any]]", response.data or [])