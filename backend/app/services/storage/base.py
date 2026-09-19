"""Document storage abstraction.

The application depends on ``DocumentStorage`` — never on a concrete backend
or hardcoded object-key scheme. Routes receive a storage instance through the
``get_document_storage`` dependency; swapping storage backends requires no
route changes.

Contract notes:

* Object keys are opaque strings created by the implementation and stored in
  ``documents.storage_key``.
* ``read`` raises ``DocumentNotFoundError`` when the object does not exist.
* No method ever accepts or logs document contents as part of error/log
  payloads; implementations must keep secrets and content out of logs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class DocumentStorage(ABC):
    """Abstract interface for private document object storage."""

    @abstractmethod
    def store_original(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """Persist the original file and return the opaque storage key.

        The implementation decides the key layout (including any per-user
        namespacing). Raises ``StorageError`` on failure.
        """

    @abstractmethod
    def read(self, storage_key: str) -> bytes:
        """Return the object bytes for *storage_key*.

        Raises ``StorageError`` on backend failure and
        ``DocumentNotFoundError`` when the object does not exist.
        """

    @abstractmethod
    def create_signed_url(
        self,
        storage_key: str,
        *,
        expires_in_seconds: int,
        content_type: str | None = None,
    ) -> str:
        """Return a short-lived signed URL for direct browser access.

        The URL must expire after ``expires_in_seconds`` and must never be a
        permanent public link. Raises ``StorageError`` on backend failure.
        """

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Delete the object. Idempotent; missing objects are not an error."""

    @abstractmethod
    def store_report(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        report_id: UUID,
        content: bytes,
    ) -> str:
        """Persist a generated report object and return its opaque storage key.

        The key layout (including per-user namespacing) is decided by the
        implementation. The stored ``storage_key`` is what
        :meth:`read` / :meth:`create_signed_url` accept later. Raises
        ``StorageError`` on failure.
        """
