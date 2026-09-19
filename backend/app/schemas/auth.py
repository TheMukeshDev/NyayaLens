"""Auth-related response schemas.

Authentication is managed by Supabase Auth. The backend only verifies access
tokens (docs/03_TECH/API-Specification.md §4); it never handles passwords or
mints tokens itself.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.auth import AuthenticatedUser


class UserOut(BaseModel):
    """Authenticated user identity returned to clients."""

    id: str
    email: str | None = None
    role: str = "authenticated"


class MeData(BaseModel):
    user: UserOut


def to_user_out(user: AuthenticatedUser) -> UserOut:
    """Project a verified token identity onto ``UserOut``."""
    return UserOut(id=str(user.id), email=user.email, role=user.role)
