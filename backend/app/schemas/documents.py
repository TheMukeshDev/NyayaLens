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

from pydantic import BaseModel, Field


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


class UploadIntentRequest(BaseModel):
    """Client-declared upload metadata for a direct-to-storage upload.

    These values are a pre-check only: ``complete_upload`` re-validates the
    stored object's magic bytes, real size and checksum server-side, so nothing
    declared here is ever trusted as the record of what was uploaded.
    """

    filename: str = Field(min_length=1, max_length=400)
    size_bytes: int = Field(ge=1)


class DocumentUploadTicket(BaseModel):
    """Short-lived signed URL a browser ``PUT``s the file bytes to.

    Issued for exactly one reserved object key, which is why the file never has
    to pass through the API process.
    """

    path: str
    token: str
    signed_url: str
    expires_in_seconds: int


class UploadIntentData(BaseModel):
    document: DocumentOut
    upload: DocumentUploadTicket


class ProcessBatchData(BaseModel):
    """Result of one drained batch of pending documents (internal endpoint)."""

    completed: int
    failed: int
    limit: int


class DocumentStatusData(BaseModel):
    """Processing status payload (API-Specification §11)."""

    id: UUID
    status: DocumentStatus
    message: str | None = None
    progress: int | None = None


class Pagination(BaseModel):
    """Standard list pagination (API-Specification §27)."""

    page: int
    limit: int
    total: int
    pages: int


class DocumentListData(BaseModel):
    """The authenticated user's documents (API-Specification §8)."""

    items: list[DocumentOut] = Field(default_factory=list)
    pagination: Pagination
