"""Authentication endpoints.

Authentication is managed by Supabase Auth. The backend only verifies the
access token:

* ``GET /api/v1/auth/me`` — returns the identity from a verified token.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, get_current_user
from app.schemas.auth import MeData, to_user_out
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=SuccessResponse[MeData])
def me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> SuccessResponse[MeData]:
    """Return the authenticated user's identity from the verified token."""
    return SuccessResponse(data=MeData(user=to_user_out(current_user)))
