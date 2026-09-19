"""Document upload and processing-state schemas.

Statuses (docs/03_TECH/API-Specification.md §11, migration 20260917):

    UPLOADED, VALIDATING, PROCESSING, EXTRACTING, ANALYZING, READY, FAILED

The upload endpoint stores files privately and records metadata; there is no
AI interpretation and no fabricated analysis yet.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class DocumentStatus(StrEnum):
    """Canonical processing statuses for a document."""

    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    PROCESSING = "PROCESSING"
    EXTRACTING = "EXTRACTING"
    ANALYZING = "ANALYZING"
    READY = "READY"
    FAILED = "FAILED"


class DocumentOut(BaseModel):
    """Document metadata returned to clients.

    ``storage_key`` is intentionally excluded: the private object layout is an
    internal implementation detail and never exposed to clients.
    """

    id: UUID
    filename: str
    display_name: str | None = None
    mime_type: str
    file_size_bytes: int
    status: DocumentStatus
    processing_error: str | None = None
    page_count: int | None = None
    checksum_sha256: str | None = None
    uploaded_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UploadDocumentData(BaseModel):
    document: DocumentOut


class DocumentStatusData(BaseModel):
    """Processing status payload (API-Specification §11)."""

    id: UUID
    status: DocumentStatus
    message: str | None = None
    progress: int | None = None
