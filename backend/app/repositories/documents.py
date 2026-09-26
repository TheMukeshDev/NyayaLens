"""Document persistence via the Supabase service-role client.

Every read/write is scoped to the authenticated user id supplied by the
caller (from the verified token) — never from the request body
(docs/05_SECURITY/SECURITY-Architecture.md §5). The service-role key bypasses
RLS, so this scoping is a security boundary, not a convenience.

Status transitions are retry-safe: ``transition`` only applies when the current
status is in the caller-supplied predecessor set, so a retried/duplicated
transition cannot corrupt the state machine.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    """Owner-scoped access to ``public.documents``."""

    table = "documents"
    owner_column = "user_id"

    def create(
        self,
        document_id: UUID,
        *,
        user_id: UUID,
        original_filename: str,
        display_name: str | None,
        mime_type: str,
        file_size_bytes: int,
        storage_key: str,
        checksum_sha256: str | None,
    ) -> dict[str, Any]:
        """Insert a new document row in the ``UPLOADED`` state.

        ``checksum_sha256`` is ``None`` until the stored object has been read
        back and verified (``complete_upload``), so an unverified upload can
        never be mistaken for a deduplicated one.
        """
        response = (
            self._client.table(self.table)
            .insert(
                {
                    "id": str(document_id),
                    "user_id": str(user_id),
                    "original_filename": original_filename,
                    "display_name": display_name,
                    "mime_type": mime_type,
                    "file_size_bytes": file_size_bytes,
                    "storage_key": storage_key,
                    "checksum_sha256": checksum_sha256,
                    "processing_status": "UPLOADED",
                }
            )
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError("document create returned no rows")
        return cast("dict[str, Any]", rows[0])

    def get_by_id_and_user(self, user_id: UUID, document_id: UUID) -> dict[str, Any] | None:
        """Return a document owned by *user_id*, or ``None``."""
        response = self._table(user_id).select("*").eq("id", str(document_id)).limit(1).execute()
        rows = response.data or []
        return rows[0] if rows else None

    def list_by_user(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        limit: int = 30,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return the user's non-deleted documents (newest first) and the total.

        Pagination uses ``range`` with an exact PostgREST count so list reads
        stay owner-scoped without fetching every row on the client side.
        """
        offset = (page - 1) * limit
        query = (
            self._table(user_id)
            .select("*", count="exact")
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
        )
        if status:
            query = query.eq("processing_status", status)
        response = query.range(offset, offset + limit - 1).execute()
        rows = response.data or []
        total = getattr(response, "count", None)
        return (
            [cast("dict[str, Any]", row) for row in rows],
            int(total) if total is not None else len(rows),
        )

    def list_by_status(self, status: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Return non-deleted documents in *status* (worker/admin context only).

        This query intentionally bypasses the owner scope: it is used by the
        document-processing worker, which serves every user's queue. It must
        never be reachable from a request handler.
        """
        response = (
            self._client.table(self.table)
            .select("*")
            .eq("processing_status", status)
            .is_("deleted_at", "null")
            .limit(limit)
            .execute()
        )
        rows = response.data or []
        return [cast("dict[str, Any]", row) for row in rows]

    def find_duplicate(
        self,
        user_id: UUID,
        checksum_sha256: str,
        *,
        exclude_document_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        """Return a non-deleted document owned by *user_id* with same content hash.

        ``exclude_document_id`` keeps a re-run of ``complete_upload`` for the
        same document from matching the row it is verifying.
        """
        response = (
            self._table(user_id)
            .select("id")
            .eq("checksum_sha256", checksum_sha256)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        candidate = cast("dict[str, Any]", rows[0])
        if exclude_document_id is not None and candidate.get("id") == str(exclude_document_id):
            return None
        return candidate

    def transition(
        self,
        user_id: UUID,
        document_id: UUID,
        *,
        from_statuses: Sequence[str],
        to_status: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Atomically move a document from one of *from_statuses* to *to_status*.

        Returns the updated row when the transition applied, or ``None`` when
        the document does not exist or its current status is not in
        *from_statuses* (caller disambiguates existence vs. status).
        """
        payload: dict[str, Any] = {"processing_status": to_status}
        if extra:
            payload.update(extra)
        response = (
            self._table(user_id)
            .update(payload)
            .eq("id", str(document_id))
            .in_("processing_status", list(from_statuses))
            .execute()
        )
        rows = response.data or []
        return cast("dict[str, Any] | None", rows[0] if rows else None)
