"""Document upload workflow and retry-safe processing states.

Workflow (docs/02_UX/USER-Flows.md §4 + §5):

    upload -> validate -> private storage -> record -> status

Responsibilities:

* Validate the untrusted file (MIME, extension, size, filename, content
  magic) via :mod:`app.services.file_validation`.
* Reject duplicate uploads per user by SHA-256 content hash.
* Store the original privately in Supabase Storage under a per-user key.
* Create the ``documents`` row in the ``UPLOADED`` state.
* Provide retry-safe status transitions: a transition only applies when the
  current state is an allowed predecessor, so replayed/retried transitions
  never corrupt the state machine or fabricate analysis results.

No AI interpretation runs here and no analysis data is ever generated.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.errors import (
    ApiError,
    ConflictError,
    DocumentNotFoundError,
    DuplicateDocumentError,
    ErrorCodes,
    FileTooLargeError,
    InvalidFileError,
    StorageError,
    UnsupportedFileTypeError,
)
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentOut, DocumentStatus, DocumentStatusData
from app.services.file_validation import (
    ValidationOutcome,
    sanitize_filename,
    validate_uploaded_file,
)
from app.services.storage.base import DocumentStorage

logger = logging.getLogger("app.documents")

DOCUMENT_UPLOAD_ACTION = "DOCUMENT_UPLOAD"

# A document may be moved to FAILED from any in-progress state so a retried
# processing job cannot wedge it; it may only be retried (FAILED -> UPLOADED)
# from FAILED.
CAN_FAIL_FROM: tuple[str, ...] = (
    "UPLOADED",
    "VALIDATING",
    "PROCESSING",
    "EXTRACTING",
    "ANALYZING",
)
CAN_RETRY_FROM: tuple[str, ...] = ("FAILED",)
RETRY_TO = DocumentStatus.UPLOADED.value

_STATUS_MESSAGES: dict[DocumentStatus, str] = {
    DocumentStatus.UPLOADED: "File uploaded and validated; waiting to be processed.",
    DocumentStatus.VALIDATING: "Validating the uploaded file.",
    DocumentStatus.PROCESSING: "Processing the document.",
    DocumentStatus.EXTRACTING: "Extracting text from the document.",
    DocumentStatus.ANALYZING: "Analyzing the document.",
    DocumentStatus.READY: "Document is ready.",
    DocumentStatus.FAILED: "Processing failed and can be retried.",
}


class DocumentService:
    """Orchestrates upload, metadata reads and retry-safe status transitions."""

    def __init__(
        self,
        *,
        repository: DocumentRepository,
        storage: DocumentStorage | None = None,
        audit: AuditLogRepository | None = None,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._audit = audit

    # -- upload -----------------------------------------------------------------

    def upload(self, *, user_id: UUID, filename: str, content: bytes) -> DocumentOut:
        """Validate, deduplicate, store privately and record an upload."""
        if self._storage is None:
            raise RuntimeError("DocumentService was built without document storage")

        outcome = validate_uploaded_file(filename, content)
        if not outcome.valid:
            raise _validation_error(outcome)

        checksum = hashlib.sha256(content).hexdigest()
        if self._repository.find_duplicate(user_id, checksum) is not None:
            raise DuplicateDocumentError()

        safe_name = sanitize_filename(filename)
        document_id = uuid4()
        try:
            storage_key = self._storage.store_original(
                user_id=user_id,
                document_id=document_id,
                filename=safe_name,
                content=content,
                content_type=outcome.mime_type or "application/octet-stream",
            )
        except StorageError:
            raise
        except Exception:
            logger.error("document storage upload failed unexpectedly", exc_info=True)
            raise StorageError() from None

        try:
            row = self._repository.create(
                document_id,
                user_id=user_id,
                original_filename=safe_name,
                display_name=None,
                mime_type=outcome.mime_type or "",
                file_size_bytes=len(content),
                storage_key=storage_key,
                checksum_sha256=checksum,
            )
        except Exception:
            self._best_effort_delete(storage_key)
            raise

        self._log_audit(DOCUMENT_UPLOAD_ACTION, user_id, document_id)
        return _to_document_out(row)

    # -- reads ------------------------------------------------------------------

    def get_metadata(self, *, user_id: UUID, document_id: UUID) -> DocumentOut:
        row = self._require_owned(user_id, document_id)
        return _to_document_out(row)

    def get_status(self, *, user_id: UUID, document_id: UUID) -> DocumentStatusData:
        row = self._require_owned(user_id, document_id)
        status = _status_of(row)
        message = (
            row.get("processing_error")
            if status is DocumentStatus.FAILED
            else _STATUS_MESSAGES.get(status, status.value)
        )
        return DocumentStatusData(
            id=row["id"],
            status=status,
            message=message,
        )

    # -- processing states --------------------------------------------------------

    def mark_failed(self, *, user_id: UUID, document_id: UUID, message: str) -> DocumentOut:
        """Mark an in-progress document as FAILED (retry-safe)."""
        row = self._repository.transition(
            user_id,
            document_id,
            from_statuses=CAN_FAIL_FROM,
            to_status=DocumentStatus.FAILED.value,
            extra={"processing_error": message, "processed_at": None},
        )
        if row is None:
            raise self._missing_or_conflict(user_id, document_id)
        return _to_document_out(row)

    def retry(self, *, user_id: UUID, document_id: UUID) -> DocumentOut:
        """Reset a FAILED document to UPLOADED so processing can resume."""
        row = self._repository.transition(
            user_id,
            document_id,
            from_statuses=CAN_RETRY_FROM,
            to_status=RETRY_TO,
            extra={"processing_error": None, "processed_at": None},
        )
        if row is None:
            raise self._missing_or_conflict(user_id, document_id)
        return _to_document_out(row)

    def transition(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        from_statuses: Sequence[str],
        to_status: str,
        extra: dict[str, Any] | None = None,
    ) -> DocumentOut:
        """Advance a document through a retry-safe state machine step.

        Used by the processing worker to move a document between pipeline
        stages. Raises when the document is missing or not in *from_statuses*,
        so a replayed/retried step cannot corrupt the state machine.
        """
        row = self._repository.transition(
            user_id,
            document_id,
            from_statuses=from_statuses,
            to_status=to_status,
            extra=extra,
        )
        if row is None:
            raise self._missing_or_conflict(user_id, document_id)
        return _to_document_out(row)

    def mark_ready(
        self, *, user_id: UUID, document_id: UUID, page_count: int
    ) -> DocumentOut:
        """Move a PROCESSING/ANALYZING document to READY, stamping its page count."""
        row = self._repository.transition(
            user_id,
            document_id,
            from_statuses=("PROCESSING", "ANALYZING"),
            to_status=DocumentStatus.READY.value,
            extra={
                "page_count": page_count,
                "processed_at": _now_iso(),
                "processing_error": None,
            },
        )
        if row is None:
            raise self._missing_or_conflict(user_id, document_id)
        return _to_document_out(row)

    # -- helpers -------------------------------------------------------------------

    def _require_owned(self, user_id: UUID, document_id: UUID) -> dict[str, Any]:
        row = self._repository.get_by_id_and_user(user_id, document_id)
        if row is None:
            raise DocumentNotFoundError()
        return row

    def _missing_or_conflict(self, user_id: UUID, document_id: UUID) -> ApiError:
        if self._repository.get_by_id_and_user(user_id, document_id) is None:
            return DocumentNotFoundError()
        return ConflictError("The document cannot be processed in its current state.")

    def _best_effort_delete(self, storage_key: str) -> None:
        if self._storage is None:
            return
        try:
            self._storage.delete(storage_key)
        except Exception:
            logger.warning("failed to clean up orphaned stored object", exc_info=True)

    def _log_audit(self, action: str, user_id: UUID, document_id: UUID) -> None:
        if self._audit is None:
            return
        try:
            self._audit.insert(
                action=action,
                user_id=user_id,
                resource_type="document",
                resource_id=document_id,
            )
        except Exception:
            logger.warning("audit insert failed", exc_info=True)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _status_of(row: dict[str, Any]) -> DocumentStatus:
    value = row.get("processing_status")
    try:
        return DocumentStatus(value) if value else DocumentStatus.UPLOADED
    except ValueError:
        return DocumentStatus.UPLOADED


def _to_document_out(row: dict[str, Any]) -> DocumentOut:
    """Project a ``documents`` row onto the safe API schema."""
    return DocumentOut(
        id=row.get("id"),
        filename=row.get("original_filename") or "",
        display_name=row.get("display_name"),
        mime_type=row.get("mime_type") or "",
        file_size_bytes=int(row.get("file_size_bytes") or 0),
        status=_status_of(row),
        processing_error=(
            row.get("processing_error") if isinstance(row.get("processing_error"), str) else None
        ),
        page_count=row.get("page_count"),
        checksum_sha256=row.get("checksum_sha256"),
        uploaded_at=row.get("uploaded_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _validation_error(outcome: ValidationOutcome) -> ApiError:
    """Map a failed validation outcome to the matching API error."""
    if outcome.error_code == ErrorCodes.UNSUPPORTED_FILE_TYPE:
        return UnsupportedFileTypeError(outcome.message)
    if outcome.error_code == ErrorCodes.FILE_TOO_LARGE:
        return FileTooLargeError(outcome.message)
    return InvalidFileError(outcome.message)
