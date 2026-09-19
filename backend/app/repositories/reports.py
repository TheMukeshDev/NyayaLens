"""Persistence and reads for ``public.reports`` (Database-Schema.md §14).

A report row tracks the lifecycle of a generated review document whose content
lives in private object storage under ``reports.storage_key``. Reads are
owner-scoped through ``BaseRepository``.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from app.repositories.base import BaseRepository

REPORTS_TABLE = "reports"


class ReportsRepository(BaseRepository):
    """Owner-bound access to ``public.reports``."""

    table = REPORTS_TABLE
    owner_column = "user_id"

    def create(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        report_type: str,
        status: str = "GENERATING",
        storage_key: str | None = None,
    ) -> dict[str, Any]:
        """Insert one report row and return it."""
        payload: dict[str, Any] = {
            "user_id": str(user_id),
            "document_id": str(document_id),
            "report_type": report_type,
            "status": status,
            "storage_key": storage_key,
        }
        response = self._client.table(self.table).insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError("report create returned no rows")
        return cast("dict[str, Any]", rows[0])

    def list(self, user_id: UUID, document_id: UUID | None = None) -> list[dict[str, Any]]:
        """Return the user's reports, newest first."""
        query = self._table(user_id).select("*")
        if document_id is not None:
            query = query.eq("document_id", str(document_id))
        response = query.order("created_at", desc=True).execute()
        return cast("list[dict[str, Any]]", response.data or [])

    def get(self, user_id: UUID, report_id: UUID) -> dict[str, Any] | None:
        """Return one owned report row, or ``None``."""
        response = self._table(user_id).select("*").eq("id", str(report_id)).limit(1).execute()
        rows = response.data or []
        return cast("dict[str, Any] | None", rows[0] if rows else None)

    def mark(
        self,
        user_id: UUID,
        report_id: UUID,
        *,
        status: str,
        storage_key: str | None = None,
        completed_at: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an owned report's lifecycle fields, or ``None`` when missing."""
        payload: dict[str, Any] = {"status": status}
        if storage_key is not None:
            payload["storage_key"] = storage_key
        if completed_at is not None:
            payload["completed_at"] = completed_at
        response = self._table(user_id).update(payload).eq("id", str(report_id)).execute()
        rows = response.data or []
        return cast("dict[str, Any] | None", rows[0] if rows else None)