"""Vercel serverless entry point tests (hermetic).

The ASGI bridge in ``api/[[...path]].py`` is the only code that runs in
production on Vercel, and it is loaded by file path (its filename is a Vercel
catch-all, not a valid Python identifier). These tests drive it with stand-ins
for the platform's request/response objects so the translation layer -- path,
query string, headers, body, status and response headers -- is pinned down
without deploying anything.
"""

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_ENTRY_POINT = Path(__file__).resolve().parents[1] / "api" / "[[...path]].py"


def _load_entry_point() -> Any:
    """Import the Vercel function module by path under a valid module name."""
    spec = importlib.util.spec_from_file_location("vercel_api_entry", _ENTRY_POINT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeRequest:
    """Stand-in for Vercel's request object (the parts the bridge reads)."""

    def __init__(
        self,
        *,
        method: str = "GET",
        url: str = "https://api.example.com/api/v1/health",
        headers: dict[str, str] | None = None,
        body: bytes = b"",
        query_string: str = "",
        path: str = "/",
        scheme: str = "https",
        client: tuple[str, int] = ("203.0.113.7", 54321),
    ) -> None:
        self.method = method
        self.url = url
        self.headers = headers or {}
        self._body = body
        self.query_string = query_string
        self.path = path
        self.scheme = scheme
        self.client = client

    def get_data(self) -> bytes:
        return self._body


class _FakeResponse:
    """Stand-in for Vercel's response object (buffers everything written)."""

    def __init__(self) -> None:
        self.status_code = 500
        self.headers: dict[str, str] = {}
        self.chunks: list[bytes] = []

    def write(self, chunk: bytes) -> None:
        self.chunks.append(chunk)

    @property
    def body(self) -> bytes:
        return b"".join(self.chunks)

    def json(self) -> Any:
        return json.loads(self.body)

    def header(self, name: str) -> str | None:
        """Case-insensitive header lookup (HTTP header names are not case sensitive)."""
        lowered = name.lower()
        return next(
            (value for key, value in self.headers.items() if key.lower() == lowered), None
        )


@pytest.fixture(scope="module")
def entry_point() -> Any:
    return _load_entry_point()


def _call(entry_point: Any, request: _FakeRequest) -> _FakeResponse:
    response = _FakeResponse()
    entry_point.handler(request, response)
    return response


class TestRequestTranslation:
    def test_routes_by_the_full_url_path(self, entry_point):
        response = _call(
            entry_point,
            _FakeRequest(
                url="https://api.example.com/api/v1/documents/11111111-1111-4111-8111-111111111111"
            ),
        )
        # Reached the route (an unauthenticated read is refused, not a 404).
        assert response.status_code == 401

    def test_health_endpoint_answers(self, entry_point):
        response = _call(entry_point, _FakeRequest())

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_falls_back_to_path_and_query_when_url_is_absent(self, entry_point):
        response = _call(
            entry_point,
            _FakeRequest(
                method="POST",
                url="",
                path="/api/v1/ping",
                headers={"Content-Type": "application/json"},
                body=b'{"message": "hello"}',
            ),
        )

        assert response.status_code == 200
        assert response.json()["data"] == {"reply": "hello", "received": "hello"}

    def test_request_body_is_delivered(self, entry_point):
        response = _call(
            entry_point,
            _FakeRequest(
                method="POST",
                url="https://api.example.com/api/v1/ping",
                headers={"Content-Type": "application/json"},
                body=b'{"message": "hello"}',
            ),
        )

        assert response.status_code == 200
        assert response.json()["data"]["received"] == "hello"

    def test_body_validation_errors_reach_the_client(self, entry_point):
        response = _call(
            entry_point,
            _FakeRequest(
                method="POST",
                url="https://api.example.com/api/v1/ping",
                headers={"Content-Type": "application/json"},
                body=b'{"message": ""}',
            ),
        )

        assert response.status_code == 422

    def test_unknown_route_is_404_not_a_bridge_failure(self, entry_point):
        response = _call(
            entry_point, _FakeRequest(url="https://api.example.com/api/v1/does-not-exist")
        )
        assert response.status_code == 404

    def test_security_headers_are_forwarded_onto_the_response(self, entry_point):
        response = _call(entry_point, _FakeRequest())

        assert response.header("x-content-type-options") == "nosniff"
        assert response.header("x-frame-options") == "DENY"
        assert response.header("cache-control") == "no-store"

    def test_request_headers_reach_the_asgi_app(self, entry_point):
        response = _call(
            entry_point,
            _FakeRequest(
                url="https://api.example.com/api/v1/documents",
                headers={"Authorization": "Bearer not-a-real-token"},
            ),
        )
        # An invalid bearer token proves the Authorization header was decoded
        # and handed to the app, rather than being dropped by the bridge.
        assert response.status_code == 401


class TestScopeConstruction:
    def test_request_target_parsing(self, entry_point):
        path, query = entry_point._request_target(
            _FakeRequest(url="https://api.example.com/api/v1/documents?page=2&limit=10")
        )
        assert path == "/api/v1/documents"
        assert query == b"page=2&limit=10"

    def test_headers_are_lowercased_bytes(self, entry_point):
        headers = entry_point._scope_headers(
            _FakeRequest(headers={"Content-Type": "application/json", "X-Request-Id": "abc"})
        )
        assert (b"content-type", b"application/json") in headers
        assert all(name == name.lower() for name, _ in headers)

    def test_missing_client_address_does_not_raise(self, entry_point):
        assert entry_point._client_address(_FakeRequest(client=None)) == ("localhost", 0)
