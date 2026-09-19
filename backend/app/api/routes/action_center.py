"""Action Center endpoints (docs/03_TECH/API-Specification.md §20-§22).

``POST /documents/{document_id}/action-center`` generates and persists the
Action Center board (review checklist, follow-up items, important dates).
``POST /documents/{document_id}/questions/generate`` produces traceable
professional questions. Actions are listed and completed with
``GET /actions`` / ``PATCH /actions/{action_id}``. Review reports are created
with ``POST /documents/{document_id}/reports`` and downloaded through a
short-lived signed URL only.

Security model matches the other document endpoints: identity comes from the
verified bearer token, ownership of the document/action/report is enforced in
the service, and no report content is ever served from a public URL.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.ai.action_center.service import ActionCenterService
from app.api.deps import get_action_center_service
from app.core.auth import AuthenticatedUser, get_current_user
from app.schemas.action_center import (
    ActionCenterOut,
    ActionOut,
    ActionStatusUpdate,
    ProfessionalQuestionsOut,
    ReportDownloadOut,
    ReportOut,
)
from app.schemas.common import SuccessResponse

router = APIRouter(tags=["action-center"])

StatusFilter = Literal["TODO", "IN_PROGRESS", "COMPLETED", "DISMISSED"]
PriorityFilter = Literal["LOW", "MEDIUM", "HIGH"]


@router.post(
    "/documents/{document_id}/action-center",
    response_model=SuccessResponse[ActionCenterOut],
    status_code=201,
)
def generate_action_center(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ActionCenterService, Depends(get_action_center_service)],
    document_id: UUID,
) -> SuccessResponse[ActionCenterOut]:
    """Generate the review checklist, follow-up items and important dates."""
    return SuccessResponse(
        data=service.generate(user_id=current_user.id, document_id=document_id)
    )


@router.post(
    "/documents/{document_id}/questions/generate",
    response_model=SuccessResponse[ProfessionalQuestionsOut],
)
def generate_questions(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ActionCenterService, Depends(get_action_center_service)],
    document_id: UUID,
    user_context: Annotated[str | None, Query(max_length=2000)] = None,
) -> SuccessResponse[ProfessionalQuestionsOut]:
    """Generate questions to discuss with a qualified legal professional."""
    return SuccessResponse(
        data=service.questions(
            user_id=current_user.id,
            document_id=document_id,
            user_context=user_context,
        )
    )


@router.get("/actions", response_model=SuccessResponse[list[ActionOut]])
def list_actions(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ActionCenterService, Depends(get_action_center_service)],
    document_id: UUID | None = None,
    status: StatusFilter | None = None,
    priority: PriorityFilter | None = None,
) -> SuccessResponse[list[ActionOut]]:
    """List the user's actions (optionally filtered)."""
    return SuccessResponse(
        data=service.list_actions(
            user_id=current_user.id,
            document_id=document_id,
            status=status,
            priority=priority,
        )
    )


@router.patch(
    "/actions/{action_id}", response_model=SuccessResponse[ActionOut]
)
def update_action(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ActionCenterService, Depends(get_action_center_service)],
    action_id: UUID,
    payload: ActionStatusUpdate,
) -> SuccessResponse[ActionOut]:
    """Update an action's status (e.g. mark it completed)."""
    return SuccessResponse(
        data=service.update_action_status(
            user_id=current_user.id, action_id=action_id, status=payload.status.value
        )
    )


@router.post(
    "/documents/{document_id}/reports",
    response_model=SuccessResponse[ReportOut],
    status_code=201,
)
def create_report(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ActionCenterService, Depends(get_action_center_service)],
    document_id: UUID,
) -> SuccessResponse[ReportOut]:
    """Generate and persist a downloadable review report."""
    return SuccessResponse(
        data=service.generate_report(user_id=current_user.id, document_id=document_id)
    )


@router.get("/reports", response_model=SuccessResponse[list[ReportOut]])
def list_reports(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ActionCenterService, Depends(get_action_center_service)],
    document_id: UUID | None = None,
) -> SuccessResponse[list[ReportOut]]:
    """List the user's generated reports, newest first."""
    return SuccessResponse(
        data=service.list_reports(user_id=current_user.id, document_id=document_id)
    )


@router.get("/reports/{report_id}", response_model=SuccessResponse[ReportOut])
def get_report(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ActionCenterService, Depends(get_action_center_service)],
    report_id: UUID,
) -> SuccessResponse[ReportOut]:
    """Return one owned report's metadata and status."""
    return SuccessResponse(
        data=service.get_report(user_id=current_user.id, report_id=report_id)
    )


@router.get(
    "/reports/{report_id}/download",
    response_model=SuccessResponse[ReportDownloadOut],
)
def download_report(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ActionCenterService, Depends(get_action_center_service)],
    report_id: UUID,
) -> SuccessResponse[ReportDownloadOut]:
    """Return a short-lived signed URL for an owned READY report."""
    return SuccessResponse(
        data=service.report_download_url(user_id=current_user.id, report_id=report_id)
    )