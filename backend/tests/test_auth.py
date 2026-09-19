"""Tests for JWT verification and the /api/v1/auth/me endpoint.

These tests are hermetic: token verification is offline (PyJWT + HS256 using
the configured Supabase JWT secret) and never touches Supabase.
"""

import time
from uuid import uuid4

import jwt


def _mint_token(secret: str, *, sub: str, exp: float | None = None) -> str:
    payload: dict = {"sub": sub, "exp": exp if exp is not None else time.time() + 3600}
    return jwt.encode(payload, secret, algorithm="HS256")


def test_me_no_token_returns_401(client) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "AUTH_REQUIRED"


def test_me_valid_token_returns_user(client, jwt_secret) -> None:
    user_id = str(uuid4())
    token = _mint_token(jwt_secret, sub=user_id)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["user"]["id"] == user_id
    assert body["data"]["user"]["role"] == "authenticated"


def test_me_invalid_token_returns_401(client, jwt_secret) -> None:
    token = _mint_token(jwt_secret, sub=str(uuid4()))
    garbage = token[:-1] + ("=" if token[-1] != "=" else "x")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {garbage}"})
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_token_signed_with_wrong_secret_returns_401(client) -> None:
    token = _mint_token("a-different-signing-secret-0123456789abcdef", sub=str(uuid4()))
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_expired_token_returns_401(client, jwt_secret) -> None:
    token = _mint_token(jwt_secret, sub=str(uuid4()), exp=time.time() - 10)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_malformed_bearer_returns_401(client) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
