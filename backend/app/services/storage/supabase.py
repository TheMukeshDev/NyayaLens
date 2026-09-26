"""Supabase Storage implementation of :class:`DocumentStorage`.

Uses the official Supabase Python client's storage facade with the
**service-role key**, which is server-side only and must never be exposed to
the frontend. Objects land in a single private bucket (``legal-documents`` by
default) under ``users/{user_id}/documents/{document_id}/original`` so that
ownership is derivable from the object path and RLS policies on
``storage.objects`` can enforce per-user access as defense-in-depth.

Security properties:

* Bucket is private; no public-download URLs are ever produced here.
* Every read/mutation requires the service-role client server-side.
* Document contents are never written to logs.
* Supabase's internal ``storage`` schema is never modified by the application;
  the bucket and policies are created by a Supabase SQL migration.
"""

from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from supabase import Client

from app.core.errors import DocumentNotFoundError, StorageError
from app.core.supabase import get_supabase_client

from .base import DocumentStorage, SignedUpload

logger = logging.getLogger("app.storage")


def _first_str_field(response: Any, *names: str) -> str | None:
    """Return the first non-empty string value among *names* in a dict response.

    The Supabase storage API has used several spellings for the same fields
    across client versions, so callers list every accepted key.
    """
    if not isinstance(response, dict):
        return None
    for name in names:
        value = response.get(name)
        if isinstance(value, str) and value:
            return value
    return None


class SupabaseDocumentStorage(DocumentStorage):
    """DocumentStorage backed by a private Supabase Storage bucket."""

    def __init__(
        self,
        *,
        client: Client | None = None,
        bucket: str | None = None,
    ) -> None:
        from app.core.config import settings

        self._bucket = bucket or settings.storage_bucket
        self._client = client

    def _bucket_api(self) -> Any:
        """Return the storage bucket handle, creating the client lazily."""
        client = self._client or get_supabase_client()
        return client.storage.from_(self._bucket)

    @staticmethod
    def _object_key(user_id: UUID, document_id: UUID) -> str:
        return f"users/{user_id}/documents/{document_id}/original"

    @staticmethod
    def _report_key(user_id: UUID, document_id: UUID, report_id: UUID) -> str:
        return f"users/{user_id}/documents/{document_id}/reports/{report_id}.txt"

    # -- DocumentStorage -----------------------------------------------------

    def original_key(self, *, user_id: UUID, document_id: UUID) -> str:
        return self._object_key(user_id, document_id)

    def create_signed_upload_url(self, storage_key: str) -> SignedUpload:
        """Sign a single-use upload URL so the browser writes bytes directly.

        The signed URL is a bearer credential for exactly one object, so it is
        never logged and never returned from a list/read endpoint.
        """
        try:
            response = self._bucket_api().create_signed_upload_url(storage_key)
        except Exception:
            logger.error("Supabase Storage sign-upload failed", exc_info=True)
            raise StorageError() from None

        token = _first_str_field(response, "token")
        signed_url = _first_str_field(response, "signedUrl", "signed_url", "signedURL", "url")
        if not token or not signed_url:
            logger.error("Supabase Storage sign-upload returned incomplete data")
            raise StorageError()
        return SignedUpload(path=storage_key, token=token, signed_url=signed_url)

    def store_original(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> str:
        del filename  # never used in the object key; key carries only ids
        key = self._object_key(user_id, document_id)
        options: dict[str, Any] = {"content-type": content_type, "upsert": "true"}
        try:
            self._bucket_api().upload(key, content, options)
        except Exception:
            logger.error("Supabase Storage upload failed", exc_info=True)
            raise StorageError() from None
        return key

    def read(self, storage_key: str) -> bytes:
        try:
            return cast(bytes, self._bucket_api().download(storage_key))
        except Exception as exc:
            if self._is_not_found(exc):
                raise DocumentNotFoundError() from None
            logger.error("Supabase Storage read failed", exc_info=True)
            raise StorageError() from None

    def create_signed_url(
        self,
        storage_key: str,
        *,
        expires_in_seconds: int,
        content_type: str | None = None,
    ) -> str:
        del content_type  # signing key only; the stored content-type is served
        try:
            response = self._bucket_api().create_signed_url(storage_key, expires_in_seconds)
        except Exception:
            logger.error("Supabase Storage sign failed", exc_info=True)
            raise StorageError() from None

        signed = self._signed_url_from(response)
        if not signed:
            logger.error("Supabase Storage sign returned no URL")
            raise StorageError()
        return signed


    def delete(self, storage_key: str) -> None:
        try:
            self._bucket_api().remove([storage_key])
        except Exception as exc:
            if self._is_not_found(exc):
                return  # already gone — idempotent
            logger.error("Supabase Storage delete failed", exc_info=True)
            raise StorageError() from None

    def store_report(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        report_id: UUID,
        content: bytes,
    ) -> str:
        """Persist a generated report and return its report object key."""
        key = self._report_key(user_id, document_id, report_id)
        options: dict[str, Any] = {
            "content-type": "text/plain; charset=utf-8",
            "upsert": "true",
        }
        try:
            self._bucket_api().upload(key, content, options)
        except Exception:
            logger.error("Supabase Storage report upload failed", exc_info=True)
            raise StorageError() from None
        return key

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _signed_url_from(response: Any) -> str | None:
        return _first_str_field(response, "signedURL", "signed_url", "signedUrl") or (
            response if isinstance(response, str) and response else None
        )

    @staticmethod
    def _is_not_found(exc: Exception) -> bool:
        text = str(exc).lower()
        return "not found" in text or "404" in text
