"""NyayaLens FastAPI application.

Foundation wiring:

* Versioned public API under ``/api/v1``.
* Consistent error envelope (no stack traces, DB errors, paths or secrets).
* Pydantic request validation on all endpoints.
* Structured JSON logging with per-request ids.
* CORS restricted to configured browser origins.
* Security headers on every response.
* Liveness (``/health``) and versioned structured health (``/api/v1/health``).

Authentication is Supabase Auth; the backend verifies access tokens. AI
features and business endpoints are intentionally not implemented yet.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router import api_v1
from .api.routes import health
from .core.config import settings
from .core.errors import register_exception_handlers
from .core.logging import RequestContextMiddleware, setup_logging
from .core.security import SecurityHeadersMiddleware

setup_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="NyayaLens backend API.",
    docs_url="/api/v1/docs" if settings.docs_enabled else None,
    redoc_url="/api/v1/redoc" if settings.docs_enabled else None,
    openapi_url="/api/v1/openapi.json" if settings.docs_enabled else None,
)

register_exception_handlers(app)

# Middleware is applied in reverse order of registration, so CORS is the
# outermost layer, then security headers, then request context.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(api_v1)
