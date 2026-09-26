"""Internal endpoints: scheduled background work, not part of the public API.

Serverless functions are stateless and are frozen when idle, so the long-lived
polling worker (``python -m app.workers.document_worker --interval``) cannot run
on Vercel. The same pipeline is instead drained on demand by
``POST /api/v1/internal/process-documents``, which ``vercel.json`` schedules as a
cron job. The per-document endpoint ``POST /api/v1/documents/{id}/process`` is
the fast path; this one is the safety net for anything left behind.

Authorization: ``Authorization: Bearer $CRON_SECRET``, which Vercel attaches
automatically to cron invocations. The router is excluded from the OpenAPI schema
and every route is disabled when ``CRON_SECRET`` is unset, so it can never
become an unauthenticated privileged surface.
"""

from __future__ import annotations

import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, Header, Query

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.schemas.common import SuccessResponse
from app.schemas.documents import ProcessBatchData

logger = logging.getLogger("app.internal")

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)

_BEARER_PREFIX = "bearer "


def _require_cron_secret(authorization: str | None) -> None:
    """Reject the request unless it carries the shared cron secret.

    Comparison is constant-time so the endpoint cannot be used as a timing
    oracle to recover the secret.
    """
    if not settings.cron_secret:
        raise UnauthorizedError("This endpoint is not enabled.")
    header = (authorization or "").strip()
    if not header.lower().startswith(_BEARER_PREFIX):
        raise UnauthorizedError("A cron authorization token is required.")
    presented = header[len(_BEARER_PREFIX) :].strip()
    if not hmac.compare_digest(presented, settings.cron_secret):
        raise UnauthorizedError("A cron authorization token is required.")


@router.post("/process-documents", response_model=SuccessResponse[ProcessBatchData])
def process_pending_documents(
    authorization: Annotated[str | None, Header()] = None,
    limit: Annotated[int, Query(ge=1, le=25)] = 3,
) -> SuccessResponse[ProcessBatchData]:
    """Drain up to *limit* pending documents through the processing pipeline.

    One document at a time by default: a serverless invocation has a hard
    execution-time ceiling, so a small batch is the only size that reliably
    completes. Per-document failures are recorded on the document itself and
    counted here rather than raised, so one bad file never blocks the queue.
    """
    _require_cron_secret(authorization)

    from app.repositories.documents import DocumentRepository
    from app.workers.document_worker import build_default_service, process_pending

    completed, failed = process_pending(
        document_repository=DocumentRepository(),
        processing_service=build_default_service(),
        limit=limit,
    )
    logger.info("drained pending documents: %s completed, %s failed", completed, failed)
    return SuccessResponse(
        data=ProcessBatchData(completed=completed, failed=failed, limit=limit)
    )
