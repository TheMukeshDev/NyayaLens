"""Persistence and reads for document comparisons.

Backs the comparison feature (Database-Schema.md §12, API-Specification.md
§19). ``comparisons`` holds one run (status, summary, timestamps);
``comparison_changes`` holds the per-clause classifications. All reads are
scoped to the owning user because the service-role client bypasses RLS
(``public.is_comparison_owner``), so ownership scoping is a security boundary,
not a convenience.

Writes are idempotent: a comparison is persisted once and its changes replaced
delete-then-insert, so a retried run never duplicates rows.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from supabase import Client

from app.core.supabase import get_supabase_client

COMPARISONS_TABLE = "comparisons"
CHANGES_TABLE = "comparison_changes"


class ComparisonRepository:
    """Owner-bound access to ``comparisons`` and ``comparison_changes``."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()

    # -- comparisons ---------------------------------------------------------

    def create(
        self,
        *,
        user_id: UUID,
        document_a_id: UUID,
        document_b_id: UUID,
        status: str = "PENDING",
        summary: str | None = None,
    ) -> dict[str, Any]:
        """Insert one comparison row and return it (validated payload only)."""
        payload: dict[str, Any] = {
            "user_id": str(user_id),
            "document_a_id": str(document_a_id),
            "document_b_id": str(document_b_id),
            "status": status,
            "summary": summary,
        }
        response = self._client.table(COMPARISONS_TABLE).insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError("comparison create returned no rows")
        return cast("dict[str, Any]", rows[0])

    def get(self, user_id: UUID, comparison_id: UUID) -> dict[str, Any] | None:
        """Return a comparison owned by *user_id*, or ``None``."""
        response = (
            self._client.table(COMPARISONS_TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .eq("id", str(comparison_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return cast("dict[str, Any] | None", rows[0] if rows else None)

    def mark(
        self,
        user_id: UUID,
        comparison_id: UUID,
        *,
        status: str,
        summary: str | None,
        completed_at: str | None,
    ) -> dict[str, Any] | None:
        """Update the status/summary/completion time of an owned comparison."""
        response = (
            self._client.table(COMPARISONS_TABLE)
            .update(
                {
                    "status": status,
                    "summary": summary,
                    "completed_at": completed_at,
                }
            )
            .eq("user_id", str(user_id))
            .eq("id", str(comparison_id))
            .execute()
        )
        rows = response.data or []
        return cast("dict[str, Any] | None", rows[0] if rows else None)

    # -- comparison_changes ---------------------------------------------------

    def replace_changes(
        self,
        *,
        comparison_id: UUID,
        changes: list[dict[str, Any]],
    ) -> None:
        """Replace all persisted changes of a comparison (idempotent)."""
        (
            self._client.table(CHANGES_TABLE)
            .delete()
            .eq("comparison_id", str(comparison_id))
            .execute()
        )
        if not changes:
            return
        created_at = _staggered_created_at(len(changes))
        rows: list[dict[str, Any]] = []
        for index, change in enumerate(changes):
            row = dict(change)
            row["comparison_id"] = str(comparison_id)
            row["created_at"] = created_at[index]
            rows.append(row)
        self._client.table(CHANGES_TABLE).insert(rows).execute()

    def list_changes(self, comparison_id: UUID) -> list[dict[str, Any]]:
        """Return every persisted change, in stored (deterministic) order."""
        response = (
            self._client.table(CHANGES_TABLE)
            .select("*")
            .eq("comparison_id", str(comparison_id))
            .order("created_at", desc=False)
            .execute()
        )
        return cast("list[dict[str, Any]]", response.data or [])


def _staggered_created_at(count: int) -> list[str]:
    """Return *count* strictly increasing ISO timestamps (deterministic order).

    Every row in a change batch is inserted together, so relying on the
    database default would leave ties; explicitly increasing microseconds keeps
    ``created_at`` ordering deterministic in a way that is also meaningful.
    """
    base = datetime.now(UTC)
    return [(base + timedelta(microseconds=index)).isoformat() for index in range(count)]