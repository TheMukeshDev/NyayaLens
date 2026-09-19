"""Storage service entry point.

``get_document_storage`` is the FastAPI dependency that injects a
:class:`DocumentStorage` instance. Routes depend on the abstract interface, so
no route hard-codes Supabase details. A singleton instance is reused across
requests.
"""

from __future__ import annotations

from .base import DocumentStorage
from .supabase import SupabaseDocumentStorage

__all__ = ["DocumentStorage", "SupabaseDocumentStorage", "get_document_storage"]

_document_storage: DocumentStorage | None = None


def get_document_storage() -> DocumentStorage:
    """Return the configured :class:`DocumentStorage` singleton."""
    global _document_storage
    if _document_storage is None:
        _document_storage = SupabaseDocumentStorage()
    return _document_storage
