"""Health endpoints.

* ``GET /health`` — root liveness probe, no dependencies (docs/03_TECH/API-Specification.md §23).
* ``GET /api/v1/health`` — versioned structured health payload.

Neither endpoint touches the database or exposes credentials.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import SuccessResponse
from app.schemas.health import HealthData

# Mounted at the app root: GET /health
router = APIRouter(tags=["health"])

# Mounted under the versioned router: GET /api/v1/health
api_router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the API server."""
    return {"status": "ok"}


@api_router.get("/health", response_model=SuccessResponse[HealthData])
def health_v1() -> SuccessResponse[HealthData]:
    """Structured health payload for the versioned API."""
    return SuccessResponse(
        data=HealthData(
            status="ok",
            service=settings.app_name,
            version=settings.app_version,
            api_version=settings.api_version,
            environment=settings.environment,
        )
    )
