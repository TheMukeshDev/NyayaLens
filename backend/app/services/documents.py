"""Document upload workflow and retry-safe processing states.

Workflow (docs/02_UX/USER-Flows.md §4 + §5):

    upload -> validate -> private storage -> record -> status

Uploads are two-step so the API never buffers a file body:

    1. ``create_upload_intent`` -- pre-check the client declaration, reserve a
       per-user object key, sign a short-lived upload URL, record the document
       in ``UPLOADED``.
    2. the browser ``PUT``s the bytes straight to private storage.
    3. ``complete_upload`` -- read the object back and validate its magic bytes,
       real size and SHA-256 checksum server-side, then finalize the record.

That split exists because the API runs on a serverless platform with a hard
request-body limit far below ``MAX_UPLOAD_SIZE_MB``; only the verified object
is ever trusted (see AGENT.md "no fake implementations" / FR-003).

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
import math
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.config import settings
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
from app.schemas.documents import (
    DocumentListData,
    DocumentOut,
    DocumentStatus,
    DocumentStatusData,
    DocumentUploadTicket,
    Pagination,
    UploadIntentData,
)
from app.services.file_validation import (
    ValidationOutcome,
    sanitize_filename,
    validate_upload_declaration,
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
        """Store and record an upload in a single server-side call.

        Runs the exact same checks as the browser flow -- declaration
        pre-check, magic-byte verification, deduplication, finalization -- by
        composing :meth:`create_upload_intent` and :meth:`complete_upload`; only
        the transport of the bytes differs.

        The API deliberately does **not** use this: a serverless function must
        never buffer a file body, so clients use the two-step signed-upload flow
        instead. This is the seam for hosts that do accept the body directly
        (local development, fixtures, one-off scripts).
        """
        if self._storage is None:
            raise RuntimeError("DocumentService was built without document storage")

        intent = self.create_upload_intent(
            user_id=user_id, filename=filename, size_bytes=len(content)
        )
        document_id = intent.document.id
        try:
            self._storage.store_original(
                user_id=user_id,
                document_id=document_id,
                filename=intent.document.filename,
                content=content,
                content_type=intent.document.mime_type or "application/octet-stream",
            )
        except StorageError:
            self._abort_upload(
                user_id, document_id, intent.upload.path, "The file could not be stored."
            )
            raise
        return self.complete_upload(user_id=user_id, document_id=document_id)

    def create_upload_intent(
        self, *, user_id: UUID, filename: str, size_bytes: int
    ) -> UploadIntentData:
        """Reserve a private object key and sign a direct upload URL.

        The file bytes never pass through the API: the browser ``PUT``s them
        straight to private storage using the returned short-lived ticket, then
        calls :meth:`complete_upload` for server-side verification. This keeps
        the API process free of file buffering, which a serverless platform with
        a hard request-body limit requires.

        Only the declaration is checked here. The stored object is validated
        again -- against its real magic bytes, size and checksum -- by
        :meth:`complete_upload`, which is the security boundary.
        """
        if self._storage is None:
            raise RuntimeError("DocumentService was built without document storage")

        outcome = validate_upload_declaration(filename, size_bytes)
        if not outcome.valid:
            raise _validation_error(outcome)

        document_id = uuid4()
        storage_key = self._storage.original_key(user_id=user_id, document_id=document_id)
        try:
            ticket = self._storage.create_signed_upload_url(storage_key)
        except StorageError:
            raise
        except Exception:
            logger.error("signing an upload URL failed unexpectedly", exc_info=True)
            raise StorageError() from None

        row = self._repository.create(
            document_id,
            user_id=user_id,
            original_filename=sanitize_filename(filename),
            display_name=None,
            mime_type=outcome.mime_type or "",
            file_size_bytes=size_bytes,
            storage_key=storage_key,
            checksum_sha256=None,
        )
        return UploadIntentData(
            document=_to_document_out(row),
            upload=DocumentUploadTicket(
                path=ticket.path,
                token=ticket.token,
                signed_url=ticket.signed_url,
                expires_in_seconds=settings.signed_url_expires_seconds,
            ),
        )

    def complete_upload(self, *, user_id: UUID, document_id: UUID) -> DocumentOut:
        """Verify the uploaded object server-side and record its real metadata.

        The object is read back once so the magic bytes, the real byte count and
        the SHA-256 checksum are established from the bytes themselves rather
        than from anything the client declared. An object that fails validation
        is deleted and the document is marked ``FAILED`` with the reason, so a
        rejected upload never lingers as a processable row.
        """
        if self._storage is None:
            raise RuntimeError("DocumentService was built without document storage")

        row = self._require_owned(user_id, document_id)
        storage_key = str(row.get("storage_key") or "")
        if not storage_key:
            raise StorageError()

        try:
            content = self._storage.read(storage_key)
        except DocumentNotFoundError:
            # The client never delivered the bytes. Record the reason so the
            # row is not left looking processable to the scheduled drain.
            self._abort_upload(
                user_id, document_id, storage_key, "The uploaded file was not received."
            )
            raise InvalidFileError(
                "The uploaded file was not received. Please upload it again."
            ) from None
        except StorageError:
            raise

        outcome = validate_uploaded_file(str(row.get("original_filename") or ""), content)
        if not outcome.valid:
            self._abort_upload(
                user_id, document_id, storage_key, outcome.message or "Invalid file."
            )
            raise _validation_error(outcome)

        checksum = hashlib.sha256(content).hexdigest()
        duplicate = self._repository.find_duplicate(
            user_id, checksum, exclude_document_id=document_id
        )
        if duplicate is not None:
            self._abort_upload(
                user_id, document_id, storage_key, "This document has already been uploaded."
            )
            raise DuplicateDocumentError()

        updated = self._repository.transition(
            user_id,
            document_id,
            from_statuses=(DocumentStatus.UPLOADED.value,),
            to_status=DocumentStatus.UPLOADED.value,
            extra={
                "file_size_bytes": len(content),
                "mime_type": outcome.mime_type or "",
                "checksum_sha256": checksum,
            },
        )
        if updated is None:
            raise ConflictError("The upload cannot be completed in its current state.")

        self._log_audit(DOCUMENT_UPLOAD_ACTION, user_id, document_id)
        return _to_document_out(updated)

    # -- reads ------------------------------------------------------------------

    def list(
        self,
        *,
        user_id: UUID,
        page: int = 1,
        limit: int = 30,
        status: str | None = None,
    ) -> DocumentListData:
        """Return the user's documents, newest first (API-Specification §8)."""
        rows, total = self._repository.list_by_user(
            user_id, page=page, limit=limit, status=status
        )
        return DocumentListData(
            items=[_to_document_out(row) for row in rows],
            pagination=Pagination(
                page=page,
                limit=limit,
                total=total,
                pages=_page_count(total, limit),
            ),
        )

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

    def _abort_upload(
        self, user_id: UUID, document_id: UUID, storage_key: str, message: str
    ) -> None:
        """Discard a rejected upload so it is never left processable.

        Best-effort by design: it runs while another error is already being
        raised, so a storage hiccup must not replace the real reason the upload
        was rejected.
        """
        self._best_effort_delete(storage_key)
        try:
            self.mark_failed(user_id=user_id, document_id=document_id, message=message)
        except ApiError:
            logger.warning("failed to mark a rejected upload as FAILED", exc_info=True)

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


def _page_count(total: int, limit: int) -> int:
    if total <= 0 or limit <= 0:
        return 0
    return math.ceil(total / limit)


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
