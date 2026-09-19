"""Persistence and reads for ``public.actions`` (Database-Schema.md §13).

Action rows are the Action Center board: generated checklist items and
follow-ups the user can track and mark complete. Writes are owner-scoped
through ``BaseRepository`` (service-role client + explicit ``user_id`` filter)
and regeneration is delete-then-insert per document, mirroring the analysis
repository, so a re-generated board never accumulates stale items.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from app.repositories.base import BaseRepository

ACTIONS_TABLE = "actions"


class ActionsRepository(BaseRepository):
    """Owner-bound access to ``public.actions``."""

    table = ACTIONS_TABLE
    owner_column = "user_id"

    def create(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        action_type: str,
        title: str,
        description: str | None,
        priority: str,
        status: str = "TODO",
        attention_item_id: UUID | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Insert one action row and return it."""
        payload: dict[str, Any] = {
            "user_id": str(user_id),
            "document_id": str(document_id),
            "action_type": action_type,
            "title": title,
            "description": description,
            "priority": priority,
            "status": status,
        }
        if attention_item_id is not None:
            payload["attention_item_id"] = str(attention_item_id)
        if due_date is not None:
            payload["due_date"] = due_date
        response = self._client.table(self.table).insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError("action create returned no rows")
        return cast("dict[str, Any]", rows[0])

    def replace_for_document(
        self,
        user_id: UUID,
        document_id: UUID,
        rows: list[dict[str, Any]],
    ) -> None:
        """Replace a document's actions (idempotent board regeneration).

        Any existing actions for the document are removed first, then *rows*
        are inserted (each stamped with ``user_id`` and ``document_id``).
        """
        self._client.table(self.table).delete().eq("document_id", str(document_id)).execute()
        if not rows:
            return
        stamped: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["user_id"] = str(user_id)
            item["document_id"] = str(document_id)
            stamped.append(item)
        self._client.table(self.table).insert(stamped).execute()

    def list(
        self,
        user_id: UUID,
        *,
        document_id: UUID | None = None,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the user's actions, oldest first, with optional filters."""
        query = self._table(user_id).select("*")
        if document_id is not None:
            query = query.eq("document_id", str(document_id))
        if status is not None:
            query = query.eq("status", status)
        if priority is not None:
            query = query.eq("priority", priority)
        response = query.order("created_at", desc=False).execute()
        return cast("list[dict[str, Any]]", response.data or [])

    def get(self, user_id: UUID, action_id: UUID) -> dict[str, Any] | None:
        """Return one owned action row, or ``None``."""
        response = self._table(user_id).select("*").eq("id", str(action_id)).limit(1).execute()
        rows = response.data or []
        return cast("dict[str, Any] | None", rows[0] if rows else None)

    def set_status(
        self,
        user_id: UUID,
        action_id: UUID,
        status: str,
    ) -> dict[str, Any] | None:
        """Update one owned action's status, or ``None`` when not found."""
        response = (
            self._table(user_id)
            .update({"status": status})
            .eq("id", str(action_id))
            .execute()
        )
        rows = response.data or []
        return cast("dict[str, Any] | None", rows[0] if rows else None)