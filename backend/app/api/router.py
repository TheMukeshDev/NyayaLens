"""Router registrations.

All public API routes are versioned under ``/api/v1``. Breaking changes
require a new API version (docs/03_TECH/API-Specification.md §30).
"""

from fastapi import APIRouter

from .routes import (
    action_center,
    analysis,
    auth,
    comparisons,
    documents,
    health,
    internal,
    ping,
    qa,
)

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(auth.router)
api_v1.include_router(documents.router)
api_v1.include_router(analysis.router)
api_v1.include_router(qa.router)
api_v1.include_router(comparisons.router)
api_v1.include_router(action_center.router)
api_v1.include_router(ping.router)
api_v1.include_router(internal.router)
api_v1.include_router(health.api_router)

__all__ = ["api_v1"]
