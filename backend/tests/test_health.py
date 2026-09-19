"""Tests for the health endpoints."""

from app.core.config import settings


def test_health_liveness(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_v1_health_structured(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["status"] == "ok"
    assert data["service"] == settings.app_name
    assert data["version"] == settings.app_version
    assert data["api_version"] == "1.0.0"
    assert data["environment"] == settings.environment


def test_health_response_has_request_id_header(client) -> None:
    response = client.get("/health")
    assert response.headers.get("x-request-id")


def test_health_does_not_leak_credentials(client) -> None:
    for path in ("/health", "/api/v1/health"):
        payload = client.get(path).text.lower()
        assert "jwt_secret" not in payload
        assert "superbase" not in payload
        assert "test-jwt-secret" not in payload


def test_health_has_security_headers(client) -> None:
    response = client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
