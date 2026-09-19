"""Shared pytest fixtures.

The test suite is hermetic: it never requires a live database or network. A
fixed JWT secret is injected before the application imports its settings so
Supabase access tokens can be minted locally for verification tests.
"""

import os

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-0123456789abcdef0123456789abcdef")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """TestClient bound to the application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def jwt_secret() -> str:
    """The JWT secret the app verifies tokens against in tests."""
    from app.core.config import settings

    return settings.supabase_jwt_secret
