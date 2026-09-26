"""Document endpoints: upload, metadata, processing status, retry.

Security model (docs/03_TECH/API-Specification.md §7):

1. Authenticate the user from the bearer token.
2. Verify ownership on every document operation.
3. Never trust a ``user_id`` from the request body — identity comes from the
   verified token only.

Uploads are two-step (``upload-intent`` then ``{id}/complete``) so the file
bytes go straight from the browser to private storage instead of through the
API process — see ``DocumentService.create_upload_intent``.

Route ordering matters: ``/documents/upload-intent`` is declared before
``/documents/{document_id}`` because the path parameter is a UUID that would
otherwise capture the literal intent path and fail to parse.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_audit_repository,
    get_document_repository,
    get_document_storage,
    get_processing_service,
)
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.errors import ConflictError, DocumentNotFoundError
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.schemas.common import SuccessResponse
from app.schemas.documents import (
    DocumentListData,
    DocumentOut,
    DocumentStatus,
    DocumentStatusData,
    UploadIntentData,
    UploadIntentRequest,
)
from app.services.documents import DocumentService
from app.services.processing import DocumentProcessingService
from app.services.storage.base import DocumentStorage

router = APIRouter(prefix="/documents", tags=["documents"])

RepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]
StorageDep = Annotated[DocumentStorage, Depends(get_document_storage)]
AuditDep = Annotated[AuditLogRepository, Depends(get_audit_repository)]
ProcessingDep = Annotated[DocumentProcessingService, Depends(get_processing_service)]
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


@router.post("/upload-intent", status_code=201, response_model=SuccessResponse[UploadIntentData])
def create_upload_intent(
    current_user: CurrentUser,
    repository: RepositoryDep,
    storage: StorageDep,
    audit: AuditDep,
    payload: UploadIntentRequest,
) -> SuccessResponse[UploadIntentData]:
    """Reserve a private object key and return a short-lived upload ticket.

    The client then ``PUT``s the file bytes to ``upload.signed_url`` and calls
    ``{document_id}/complete``, which verifies the stored object server-side.
    Nothing the client declares here is trusted as the record of the upload.
    """
    service = DocumentService(repository=repository, storage=storage, audit=audit)
    data = service.create_upload_intent(
        user_id=current_user.id,
        filename=payload.filename,
        size_bytes=payload.size_bytes,
    )
    return SuccessResponse(data=data)


@router.post("/{document_id}/complete", response_model=SuccessResponse[DocumentOut])
def complete_upload(
    current_user: CurrentUser,
    repository: RepositoryDep,
    storage: StorageDep,
    audit: AuditDep,
    document_id: UUID,
) -> SuccessResponse[DocumentOut]:
    """Verify the uploaded object and finalize the document record."""
    service = DocumentService(repository=repository, storage=storage, audit=audit)
    document = service.complete_upload(user_id=current_user.id, document_id=document_id)
    return SuccessResponse(data=document, message="Upload verified.")


@router.post("/{document_id}/process", response_model=SuccessResponse[DocumentOut])
def process_document(
    current_user: CurrentUser,
    repository: RepositoryDep,
    processing: ProcessingDep,
    document_id: UUID,
) -> SuccessResponse[DocumentOut]:
    """Run the processing pipeline for one uploaded document.

    Serverless platforms have no long-lived worker process, so processing is
    requested per document instead of being polled in the background. It is
    owner-scoped and idempotent-safe: a document that is not ``UPLOADED``
    returns 409 rather than being processed twice.
    """
    row = repository.get_by_id_and_user(current_user.id, document_id)
    if row is None:
        raise DocumentNotFoundError()
    if row.get("processing_status") != DocumentStatus.UPLOADED.value:
        raise ConflictError("The document is already being processed.")

    document = processing.process(row=row)
    return SuccessResponse(data=document, message="Document processing finished.")


@router.get("", response_model=SuccessResponse[DocumentListData])
def list_documents(
    current_user: CurrentUser,
    repository: RepositoryDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    status: Annotated[DocumentStatus | None, Query()] = None,
) -> SuccessResponse[DocumentListData]:
    """Return the authenticated user's documents, newest first."""
    service = DocumentService(repository=repository)
    data = service.list(
        user_id=current_user.id,
        page=page,
        limit=limit,
        status=status.value if status else None,
    )
    return SuccessResponse(data=data)


@router.get("/{document_id}", response_model=SuccessResponse[DocumentOut])
def get_document(
    current_user: CurrentUser,
    repository: RepositoryDep,
    document_id: UUID,
) -> SuccessResponse[DocumentOut]:
    """Return the owning user's document metadata."""
    service = DocumentService(repository=repository)
    document = service.get_metadata(user_id=current_user.id, document_id=document_id)
    return SuccessResponse(data=document)


@router.get("/{document_id}/status", response_model=SuccessResponse[DocumentStatusData])
def get_document_status(
    current_user: CurrentUser,
    repository: RepositoryDep,
    document_id: UUID,
) -> SuccessResponse[DocumentStatusData]:
    """Return the owning user's document processing status."""
    service = DocumentService(repository=repository)
    status = service.get_status(user_id=current_user.id, document_id=document_id)
    return SuccessResponse(data=status)


@router.post("/{document_id}/retry", response_model=SuccessResponse[DocumentOut])
def retry_document(
    current_user: CurrentUser,
    repository: RepositoryDep,
    document_id: UUID,
) -> SuccessResponse[DocumentOut]:
    """Retry processing for a FAILED document, resetting it to UPLOADED."""
    service = DocumentService(repository=repository)
    document = service.retry(user_id=current_user.id, document_id=document_id)
    return SuccessResponse(data=document, message="Document processing will be retried.")
