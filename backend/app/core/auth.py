"""Supabase Auth token verification and the current-user dependency.

Authentication is managed by Supabase Auth (docs/03_TECH/API-Specification.md
§4). The browser obtains an access token from Supabase Auth and presents it as
a Bearer token; the backend verifies it offline against the project JWT secret
(HS256) and never manages passwords.

Security properties:

* Tokens are verified by signature and expiry; the ``sub`` claim must be a
  UUID.
* No token, password or secret is ever logged.
* ``get_current_user`` raises 401 on any invalid, missing or expired token —
  it never returns a "partially authenticated" object.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from .config import settings
from .errors import InvalidCredentialsError, UnauthorizedError

logger = logging.getLogger("app.auth")

_bearer = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Identity extracted from a verified Supabase Auth access token."""

    id: UUID
    email: str | None = None
    role: str = "authenticated"


def _extract_user(payload: dict[str, Any]) -> AuthenticatedUser | None:
    """Return an :class:`AuthenticatedUser` from verified claims, or None."""
    sub = payload.get("sub")
    role = payload.get("role") or "authenticated"
    if not sub:
        return None
    try:
        user_id = UUID(str(sub))
    except (ValueError, TypeError):
        return None
    email = payload.get("email")
    return AuthenticatedUser(
        id=user_id,
        email=str(email) if isinstance(email, str) and email else None,
        role=str(role),
    )


def verify_access_token(token: str) -> AuthenticatedUser:
    """Verify a Supabase Auth access token and return its identity.

    Raises:
        InvalidCredentialsError: token is malformed, expired, or signature
            verification fails. The raised message never reveals why.
    """
    secret = settings.supabase_jwt_secret
    if not secret or secret.startswith("YOUR_"):
        logger.warning(
            "SUPABASE_JWT_SECRET is missing/placeholder; token verification "
            "cannot run. Authentication is unavailable."
        )
        raise InvalidCredentialsError("Invalid token.")

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise InvalidCredentialsError("Invalid token.") from None
    except jwt.InvalidTokenError:
        raise InvalidCredentialsError("Invalid token.") from None

    user = _extract_user(payload)
    if user is None:
        raise InvalidCredentialsError("Invalid token.")
    return user


async def get_current_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    """FastAPI dependency returning the authenticated user from the Bearer token.

    Raises ``UnauthorizedError`` (401) when the token is absent and
    ``InvalidCredentialsError`` (401) when it is invalid or expired.
    """
    if cred is None or not cred.credentials:
        raise UnauthorizedError()
    return verify_access_token(cred.credentials)
