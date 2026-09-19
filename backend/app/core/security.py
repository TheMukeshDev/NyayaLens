"""Security headers middleware.

Sets defensive headers on every HTTP response. The list is deliberately
conservative for an API backend that serves JSON only.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    "X-XSS-Protection": "0",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware:
    """Add security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = {key: value for key, value in message.get("headers", [])}
                for name, value in _SECURITY_HEADERS.items():
                    headers[name.encode("latin-1")] = value.encode("latin-1")
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_wrapper)
