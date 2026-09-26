"""Internal endpoint tests (hermetic).

The internal router exists only because a serverless platform cannot run the
long-lived polling worker. It is a privileged, non-user-facing surface, so the
authorization behaviour is the thing worth pinning down.
"""

import time
from uuid import uuid4

import jwt
import pytest

from app.core.config import settings

_CRON_PATH = "/api/v1/internal/process-documents"


@pytest.fixture()
def cron_secret(monkeypatch):
    secret = "test-cron-secret"
    monkeypatch.setattr(settings, "cron_secret", secret, raising=False)
    yield secret


def _token(jwt_secret: str, user_id: str) -> str:
    payload = {"sub": user_id, "exp": time.time() + 3600}
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def _drain_calls(monkeypatch) -> list[int]:
    """Replace the pipeline drain so no AI provider or database is touched."""
    calls: list[int] = []

    def fake_process_pending(*, document_repository, processing_service, limit):
        del document_repository, processing_service
        calls.append(limit)
        return 1, 0

    monkeypatch.setattr("app.workers.document_worker.process_pending", fake_process_pending)
    return calls


class TestProcessDocumentsEndpoint:
    def test_is_absent_from_the_public_api_schema(self, client):
        response = client.get("/api/v1/openapi.json")
        if response.status_code == 404:  # docs disabled outside development
            pytest.skip("OpenAPI schema is disabled in this environment")
        assert _CRON_PATH not in response.text
        assert "/internal" not in response.text

    def test_rejects_request_without_authorization(self, client, cron_secret):
        assert client.post(_CRON_PATH).status_code == 401

    @pytest.mark.parametrize(
        "header",
        ["Bearer wrong-secret", "Bearer ", "cron-secret", "Basic test-cron-secret"],
        ids=["wrong-secret", "empty-token", "no-scheme", "wrong-scheme"],
    )
    def test_rejects_request_with_wrong_token(self, client, cron_secret, header):
        response = client.post(_CRON_PATH, headers={"Authorization": header})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_is_disabled_when_no_secret_is_configured(self, client, monkeypatch):
        monkeypatch.setattr(settings, "cron_secret", "", raising=False)

        response = client.post(_CRON_PATH, headers={"Authorization": "Bearer anything"})

        assert response.status_code == 401

    def test_authorized_request_drains_one_batch(self, client, cron_secret, monkeypatch):
        calls = _drain_calls(monkeypatch)

        response = client.post(
            _CRON_PATH, headers={"Authorization": f"Bearer {cron_secret}"}
        )

        assert response.status_code == 200
        assert response.json()["data"] == {"completed": 1, "failed": 0, "limit": 3}
        assert calls == [3]

    def test_authorized_request_respects_limit(self, client, cron_secret, monkeypatch):
        calls = _drain_calls(monkeypatch)

        response = client.post(
            f"{_CRON_PATH}?limit=7", headers={"Authorization": f"Bearer {cron_secret}"}
        )

        assert response.status_code == 200
        assert response.json()["data"]["limit"] == 7
        assert calls == [7]

    def test_limit_is_bounded(self, client, cron_secret, monkeypatch):
        _drain_calls(monkeypatch)

        response = client.post(
            f"{_CRON_PATH}?limit=500", headers={"Authorization": f"Bearer {cron_secret}"}
        )

        assert response.status_code == 422

    def test_never_accepts_a_user_access_token(self, client, cron_secret, jwt_secret):
        """A valid Supabase JWT must not grant internal access."""
        response = client.post(
            _CRON_PATH, headers={"Authorization": f"Bearer {_token(jwt_secret, str(uuid4()))}"}
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"
