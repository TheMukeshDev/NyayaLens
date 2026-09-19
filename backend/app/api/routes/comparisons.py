"""Document comparison endpoints (docs/03_TECH/API-Specification.md §19).

``POST /comparisons`` compares two owned documents; the result is persisted and
returned. ``GET /comparisons/{id}`` returns metadata/status and
``GET /comparisons/{id}/changes`` returns every detected change with citations
for both sides. Security model matches the other document endpoints:

1. Authenticate from the bearer token.
2. Verify ownership of BOTH documents (and of the comparison on reads).
3. Never trust a ``user_id`` from the body — identity comes from the token only.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai.comparison.service import DocumentComparisonService
from app.api.deps import get_comparison_service
from app.core.auth import AuthenticatedUser, get_current_user
from app.schemas.common import SuccessResponse
from app.schemas.comparison import ComparisonChangesData, ComparisonOut, ComparisonRequest

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("", status_code=201, response_model=SuccessResponse[ComparisonOut])
def create_comparison(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[DocumentComparisonService, Depends(get_comparison_service)],
    payload: ComparisonRequest,
) -> SuccessResponse[ComparisonOut]:
    """Compare two documents owned by the authenticated user."""
    result = service.compare(
        user_id=current_user.id,
        document_a_id=payload.document_a_id,
        document_b_id=payload.document_b_id,
    )
    return SuccessResponse(data=result)


@router.get("/{comparison_id}", response_model=SuccessResponse[ComparisonOut])
def get_comparison(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[DocumentComparisonService, Depends(get_comparison_service)],
    comparison_id: UUID,
) -> SuccessResponse[ComparisonOut]:
    """Return the metadata and status of an owned comparison."""
    return SuccessResponse(data=service.get(user_id=current_user.id, comparison_id=comparison_id))


@router.get("/{comparison_id}/changes", response_model=SuccessResponse[ComparisonChangesData])
def get_comparison_changes(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[DocumentComparisonService, Depends(get_comparison_service)],
    comparison_id: UUID,
) -> SuccessResponse[ComparisonChangesData]:
    """Return every detected change of an owned comparison, both sides cited."""
    return SuccessResponse(
        data=service.list_changes(user_id=current_user.id, comparison_id=comparison_id)
    )