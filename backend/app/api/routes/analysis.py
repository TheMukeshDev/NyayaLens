"""Document understanding read endpoints (API-Specification §12-§14).

``GET /documents/{document_id}/summary``, ``/attention`` and ``/clauses``
serve the persisted, already-validated analysis rows. They never generate
content: if an analysis has not been produced (or the provider abstained),
the endpoint returns an honest empty/absent payload rather than inventing one.

Security model matches the other document endpoints: identity comes from the
verified bearer token and ownership is enforced before any data is returned
(no existence leak — an unknown/cross-user document is a 404).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai.analysis.service import DocumentUnderstandingService
from app.api.deps import get_document_repository, get_understanding_service
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.errors import DocumentNotFoundError
from app.repositories.documents import DocumentRepository
from app.schemas.analysis import (
    AttentionListData,
    ClauseListData,
    UnderstandingSummary,
)
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/documents", tags=["documents"])


def _require_owned(
    current_user: AuthenticatedUser,
    repository: DocumentRepository,
    document_id: UUID,
) -> None:
    if repository.get_by_id_and_user(current_user.id, document_id) is None:
        raise DocumentNotFoundError()


@router.get(
    "/{document_id}/summary",
    response_model=SuccessResponse[UnderstandingSummary | None],
)
def get_document_summary(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    service: Annotated[DocumentUnderstandingService, Depends(get_understanding_service)],
    document_id: UUID,
) -> SuccessResponse[UnderstandingSummary | None]:
    """Return the document's plain-language summary, or a null payload."""
    _require_owned(current_user, repository, document_id)
    return SuccessResponse(data=service.get_summary(document_id=document_id))


@router.get(
    "/{document_id}/attention",
    response_model=SuccessResponse[AttentionListData],
)
def get_document_attention(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    service: Annotated[DocumentUnderstandingService, Depends(get_understanding_service)],
    document_id: UUID,
) -> SuccessResponse[AttentionListData]:
    """Return the document's areas requiring attention."""
    _require_owned(current_user, repository, document_id)
    return SuccessResponse(
        data=AttentionListData(items=service.get_attention_items(document_id=document_id))
    )


@router.get(
    "/{document_id}/clauses",
    response_model=SuccessResponse[ClauseListData],
)
def get_document_clauses(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    service: Annotated[DocumentUnderstandingService, Depends(get_understanding_service)],
    document_id: UUID,
) -> SuccessResponse[ClauseListData]:
    """Return the document's detected/analyzed clauses."""
    _require_owned(current_user, repository, document_id)
    return SuccessResponse(
        data=ClauseListData(clauses=service.get_important_clauses(document_id=document_id))
    )