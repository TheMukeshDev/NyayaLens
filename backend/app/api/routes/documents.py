"""Document endpoints: upload, metadata, processing status, retry.

Security model (docs/03_TECH/API-Specification.md §7):

1. Authenticate the user from the bearer token.
2. Verify ownership on every document operation.
3. Never trust a ``user_id`` from the request body — identity comes from the
   verified token only.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import (
    get_audit_repository,
    get_document_repository,
    get_document_storage,
)
from app.core.auth import AuthenticatedUser, get_current_user
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.schemas.common import SuccessResponse
from app.schemas.documents import DocumentOut, DocumentStatusData, UploadDocumentData
from app.services.documents import DocumentService
from app.services.storage.base import DocumentStorage

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", status_code=201, response_model=SuccessResponse[UploadDocumentData])
async def upload_document(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
    audit: Annotated[AuditLogRepository, Depends(get_audit_repository)],
    file: Annotated[UploadFile, File()],
) -> SuccessResponse[UploadDocumentData]:
    """Upload a supported legal document (PDF, DOCX, JPG, PNG)."""
    content = await file.read()
    service = DocumentService(repository=repository, storage=storage, audit=audit)
    document = service.upload(
        user_id=current_user.id,
        filename=file.filename or "",
        content=content,
    )
    return SuccessResponse(data=UploadDocumentData(document=document))


@router.get("/{document_id}", response_model=SuccessResponse[DocumentOut])
def get_document(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    document_id: UUID,
) -> SuccessResponse[DocumentOut]:
    """Return the owning user's document metadata."""
    service = DocumentService(repository=repository)
    document = service.get_metadata(user_id=current_user.id, document_id=document_id)
    return SuccessResponse(data=document)


@router.get("/{document_id}/status", response_model=SuccessResponse[DocumentStatusData])
def get_document_status(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    document_id: UUID,
) -> SuccessResponse[DocumentStatusData]:
    """Return the owning user's document processing status."""
    service = DocumentService(repository=repository)
    status = service.get_status(user_id=current_user.id, document_id=document_id)
    return SuccessResponse(data=status)


@router.post("/{document_id}/retry", response_model=SuccessResponse[DocumentOut])
def retry_document(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    document_id: UUID,
) -> SuccessResponse[DocumentOut]:
    """Retry processing for a FAILED document, resetting it to UPLOADED."""
    service = DocumentService(repository=repository)
    document = service.retry(user_id=current_user.id, document_id=document_id)
    return SuccessResponse(data=document, message="Document processing will be retried.")
