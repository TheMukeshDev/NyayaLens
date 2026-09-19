"""Persistence layer.

Repositories are the only place that talks to Supabase. Each repository:

* Uses the service-role Supabase client (``app.core.supabase``).
* Scopes every query to the authenticated ``user_id`` supplied by the caller —
  never a value taken from the request body.
* Returns plain dicts / Pydantic models; it never logs document content.
"""
