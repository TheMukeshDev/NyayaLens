"""Structured JSON logging and per-request context.

Logging follows the safe logging rules in docs/05_SECURITY/Security-Architecture.md:

Log only:
    request_id, endpoint, method, status_code, latency, error_code

Never log:
    passwords, tokens, API keys, full documents, extracted text, prompts
"""

from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from collections.abc import MutableMapping
from datetime import UTC, datetime
from typing import Any

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

_EXTRA_KEYS = ("request_id", "method", "path", "status_code", "duration_ms", "error_code")

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the request id bound to this request, or an empty string."""
    return request_id_context.get()


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line with safe metadata."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: str | int = logging.INFO) -> None:
    """Configure the root logger with JSON formatting.

    The verbose default uvicorn access log is suppressed in favour of the
    request logging performed by :class:`RequestContextMiddleware`.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)

    # uvicorn logs request access lines itself; suppress the default so each
    # request is logged exactly once with full metadata by our middleware.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class RequestContextMiddleware:
    """Attach a request id, time the request and emit one structured log line.

    The request id is echoed back to clients in the ``X-Request-ID`` response
    header so support can correlate client reports with logs.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._logger = logging.getLogger("app.request")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        status_code: int | None = None

        async def send_wrapper(message: MutableMapping[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            self._logger.info(
                "request completed",
                extra={
                    "request_id": request_id,
                    "method": scope.get("method", ""),
                    "path": scope.get("path", ""),
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            request_id_context.reset(token)
