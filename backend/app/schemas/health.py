"""Health endpoint response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class HealthData(BaseModel):
    """Structured health payload returned by ``/api/v1/health``."""

    status: str
    service: str
    version: str
    api_version: str
    environment: str
    supabase_configured: bool
    database_connected: bool
