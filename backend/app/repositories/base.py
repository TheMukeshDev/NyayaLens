"""Base repository for Supabase-backed tables.

Provides the shared plumbing (table handle + ownership scoping) that concrete
repositories build on. It intentionally exposes no table-specific methods yet:
concrete repositories are added alongside the features that need them.

Ownership rule (docs/03_TECH/System-Architecture.md §52): every query is
scoped to the authenticated user. The service-role key bypasses RLS, so this
scoping is a security boundary, not a convenience.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from supabase import Client

from app.core.supabase import get_supabase_client


class BaseRepository:
    """Common Supabase table access with an optional owner scope column."""

    table: str = ""
    owner_column: str | None = None

    def __init__(self, client: Client | None = None) -> None:
        if not self.table:
            raise ValueError(f"{type(self).__name__} must define a table name")
        self._client = client or get_supabase_client()

    def _table(self, user_id: UUID | None = None) -> Any:
        """Return a query builder, scoped to *user_id* when provided.

        When ``owner_column`` is set, ``user_id`` is required so callers cannot
        accidentally issue an unscoped query.
        """
        query: Any = self._client.table(self.table)
        if self.owner_column is not None:
            if user_id is None:
                raise ValueError("user_id is required for owner-scoped queries")
            query = query.eq(self.owner_column, str(user_id))
        return query

    def get_by_id(self, row_id: UUID, user_id: UUID | None = None) -> dict[str, Any] | None:
        """Return a single row by primary key, or ``None``."""
        response = self._table(user_id).select("*").eq("id", str(row_id)).limit(1).execute()
        rows = response.data or []
        return cast("dict[str, Any] | None", rows[0] if rows else None)
