"""Vercel serverless entry point for the NyayaLens FastAPI application.

Vercel treats every file under ``api/`` as a Python serverless function. The
double-bracket filename makes this a **catch-all**, so every public route below
``/api`` (``/api/v1/...``) reaches the ASGI app with the request path intact --
no ``vercel.json`` rewrite is involved, so the ASGI ``path`` always matches the
public URL exactly. ``vercel.json`` only maps the top-level ``/health`` probe
onto the versioned endpoint.

Why a hand-written bridge instead of ``vercel.serverless``:
``vercel.serverless.http`` ships with the platform runtime and is not
installable from PyPI, so depending on it would make the app unimportable
outside Vercel. This module therefore uses the standard library only.

Operational consequences of running on Vercel (see docs/03_TECH/DEPLOYMENT.md):

* The process is stateless and is frozen when idle -- there is no place to run
  the long-lived polling worker. Document processing is therefore triggered
  per-document by the client (``POST /api/v1/documents/{id}/process``) and
  drained on demand by the cron endpoint in ``app.api.routes.internal``.
* Uploads must never stream file bytes through a function (the request-body
  limit is far below ``MAX_UPLOAD_SIZE_MB``), so the browser PUTs the file
  directly to Supabase Storage with a short-lived signed upload ticket.
* The app object is imported once per warm container, so ``Settings`` is
  validated once and the Supabase client is reused across invocations.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

# Vercel invokes the function with the project root as the working directory,
# but the importable application lives in ``backend/app``. Pin the project root
# on ``sys.path`` so the import works regardless of the working directory.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.main import app  # noqa: E402  (sys.path setup must run before the import)

# Vercel's request/response objects are duck-typed on purpose: the platform
# types live in the non-installable ``vercel.serverless`` package, so importing
# them would make this module unimportable outside Vercel.
_Request = Any
_Response = Any

_FALLBACK_HOST = "localhost"
_TLS_PORT = 443


def _request_target(request: _Request) -> tuple[str, bytes]:
    """Return the ``(path, query_string)`` pair for the ASGI scope.

    ``request.url`` is authoritative (it already carries the decoded query
    string); ``request.path`` / ``request.query_string`` are used as fallbacks
    for runtimes that do not populate the full URL.
    """
    url = getattr(request, "url", "") or ""
    parsed = urlsplit(url) if url else None
    path = (parsed.path if parsed is not None else "") or getattr(request, "path", "") or "/"

    query = (parsed.query if parsed is not None else "") or getattr(request, "query_string", "")
    if isinstance(query, bytes):
        query = query.decode("latin-1")

    return path or "/", str(query).encode("latin-1")


def _scope_headers(request: _Request) -> list[tuple[bytes, bytes]]:
    """Return the request headers as lower-cased ASGI ``(name, value)`` bytes."""
    raw = getattr(request, "headers", None) or {}
    items = raw.items() if hasattr(raw, "items") else raw
    return [
        (str(name).lower().encode("latin-1"), str(value).encode("latin-1"))
        for name, value in items
    ]


def _client_address(request: _Request) -> tuple[str, int]:
    """Return the caller's ``(host, port)`` for the ASGI scope."""
    client = getattr(request, "client", None)
    if isinstance(client, (tuple, list)) and len(client) >= 2:  # noqa: UP038
        try:
            return str(client[0]), int(client[1])
        except (TypeError, ValueError):
            return _FALLBACK_HOST, 0
    return _FALLBACK_HOST, 0


async def _dispatch(request: _Request, response: _Response) -> None:
    """Run one HTTP request through the ASGI application."""
    body = getattr(request, "get_data", lambda: b"")() or b""
    path, query_string = _request_target(request)
    headers = _scope_headers(request)
    host = next(
        (value.decode("latin-1") for name, value in headers if name == b"host"), _FALLBACK_HOST
    )

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": str(getattr(request, "method", "GET") or "GET").upper(),
        "scheme": getattr(request, "scheme", None) or "https",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": query_string,
        "root_path": "",
        "headers": headers,
        "client": _client_address(request),
        "server": (host, _TLS_PORT),
        "state": {},
    }

    body_delivered = False

    async def receive() -> dict[str, Any]:
        # The body is fully buffered by the platform, so a single
        # ``http.request`` message followed by ``http.disconnect`` is exact.
        nonlocal body_delivered
        if body_delivered:
            return {"type": "http.disconnect"}
        body_delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            response.status_code = int(message["status"])
            for name, value in message.get("headers", []):
                response.headers[name.decode("latin-1")] = value.decode("latin-1")
            return
        if message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            if chunk:
                response.write(chunk)

    await app(scope, receive, send)  # type: ignore[arg-type]


def handler(request: _Request, response: _Response) -> None:
    """Vercel function entry point (``handler(request, response)``)."""
    asyncio.run(_dispatch(request, response))
