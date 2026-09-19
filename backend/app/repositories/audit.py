"""Audit log persistence (server-side).

``audit_logs`` has no client-facing RLS policies (verified in the live DB
review); only the service-role client writes here. Log entries carry metadata,
never document content or secrets (docs/05_SECURITY/SECURITY-Architecture.md
§10).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository):
    """Best-effort insertion into ``public.audit_logs``."""

    table = "audit_logs"

    def insert(
        self,
        *,
        action: str,
        user_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
    ) -> None:
        payload: dict[str, Any] = {"action": action}
        if user_id is not None:
            payload["user_id"] = str(user_id)
        if resource_type is not None:
            payload["resource_type"] = resource_type
        if resource_id is not None:
            payload["resource_id"] = str(resource_id)
        self._client.table(self.table).insert(payload).execute()
