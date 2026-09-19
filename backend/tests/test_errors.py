"""Tests for the standard error and success envelopes."""


def test_unknown_route_returns_404_envelope(client) -> None:
    response = client.get("/no/such/route")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
    assert isinstance(body["error"]["message"], str)


def test_wrong_method_returns_405_envelope(client) -> None:
    response = client.delete("/health")
    assert response.status_code == 405
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_validation_error_has_details(client) -> None:
    response = client.post("/api/v1/ping", json={"message": ""})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


def test_ping_success_envelope(client) -> None:
    response = client.post("/api/v1/ping", json={"message": "hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == {"reply": "hello", "received": "hello"}


def test_errors_never_leak_internal_paths(client) -> None:
    response = client.post("/api/v1/ping", json={"message": ""})
    text = response.text
    assert "Traceback" not in text
    assert "app\\" not in text and "app/" not in text
    assert "test-jwt-secret" not in text
    assert "supabase" not in text or "supabase.co" not in text
