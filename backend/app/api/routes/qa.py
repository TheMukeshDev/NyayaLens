"""Document-grounded Q&A endpoint (docs/03_TECH/API-Specification.md §15-§16).

``POST /documents/{document_id}/ask`` answers a single question about an owned
document. Security model matches the other document endpoints:

1. Authenticate from the bearer token.
2. Verify ownership on the document.
3. Never trust a ``user_id`` from the body — identity comes from the token only.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai.qa.service import QuestionAnsweringService
from app.api.deps import get_qa_service
from app.core.auth import AuthenticatedUser, get_current_user
from app.schemas.common import SuccessResponse
from app.schemas.qa import QAAnswerOut, QuoteRequest

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/{document_id}/ask", response_model=SuccessResponse[QAAnswerOut])
def ask_question(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[QuestionAnsweringService, Depends(get_qa_service)],
    document_id: UUID,
    payload: QuoteRequest,
) -> SuccessResponse[QAAnswerOut]:
    """Answer *question* grounded in the owning user's document."""
    result = service.answer(
        user_id=current_user.id,
        document_id=document_id,
        question=payload.question,
    )
    return SuccessResponse(data=result)