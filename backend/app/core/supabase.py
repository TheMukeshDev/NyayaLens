"""Supabase client provisioning.

The backend talks to Supabase through the official ``supabase`` Python client
using the **service-role key**. Service-role operations bypass Row Level
Security, so every query must be ownership-scoped in application code
(see ``app.repositories``) and never accept a ``user_id`` from the client.

Security rules (docs/05_SECURITY/SECURITY-Architecture.md):

* The service-role key exists only here, server-side.
* The client is created lazily and reused for the process lifetime.
* Configuration is validated at ``Settings`` level (production requires a
  non-placeholder key).
"""

from __future__ import annotations

import logging
from functools import lru_cache

from supabase import Client, create_client

from .config import settings

logger = logging.getLogger("app.supabase")


@lru_cache(maxsize=1)
def _build_client() -> Client | None:
    """Create (once) the service-role Supabase client, or ``None``."""
    url = settings.supabase_url
    key = settings.supabase_service_role_key
    if not url or not key or key.startswith("YOUR_"):
        logger.warning(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing/placeholder; "
            "Supabase operations will not be available."
        )
        return None
    return create_client(url, key)


def get_supabase_client() -> Client:
    """Return the process-wide Supabase client (service-role).

    Raises ``RuntimeError`` when Supabase is not configured; callers should
    treat that as an unhandled configuration error (500).
    """
    client = _build_client()
    if client is None:
        raise RuntimeError("Supabase is not configured.")
    return client
