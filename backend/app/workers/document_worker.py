"""Document processing worker.

Polls for documents in ``UPLOADED`` state and runs them through the
deterministic pipeline (extraction -> sections -> clauses -> entities ->
chunks -> persistence -> embeddings). Run with::

    python -m app.workers.document_worker [--limit N]
    python -m app.workers.document_worker --ensure-embedding-index

``--ensure-embedding-index`` confirms the configured embedding model's
dimension against the database and builds the pgvector HNSW index — it must be
run once after the embedding model/dimension is configured (the vector
dimension is never hardcoded in a migration).

The worker is for server-side/queue execution only — it is never mounted on
the HTTP application. Document content is never written to logs.
"""

from __future__ import annotations

import argparse
import logging

from app.ai.analysis.service import DocumentUnderstandingService, StructuredLLM
from app.ai.embeddings.provider import EmbeddingProvider, build_embedding_provider
from app.ai.embeddings.repository import VectorRepository
from app.ai.embeddings.service import EmbeddingService
from app.ai.llm.provider import build_llm_provider
from app.core.config import settings
from app.core.supabase import get_supabase_client
from app.document_processing.chunker import Chunker
from app.document_processing.extractor import TextExtractor
from app.document_processing.ocr import TesseractOcrEngine
from app.document_processing.pipeline import DocumentProcessingPipeline
from app.repositories.analysis import AnalysisRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.services.documents import DocumentService
from app.services.processing import DocumentProcessingService
from app.services.storage.supabase import SupabaseDocumentStorage

logger = logging.getLogger("app.processing.worker")


def process_pending(
    *,
    document_repository: DocumentRepository,
    processing_service: DocumentProcessingService,
    limit: int = 10,
) -> tuple[int, int]:
    """Process up to *limit* pending documents.

    Returns ``(completed, failed)`` counts. Documents that reach ``READY`` are
    counted as completed; everything else — expected per-document failures and
    unexpected exceptions — is counted as failed and logged.
    """
    rows = document_repository.list_by_status("UPLOADED", limit=limit)
    completed = 0
    failed = 0
    for row in rows:
        try:
            out = processing_service.process(row=row)
            if out.status == "READY":
                completed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception(
                "document processing failed for %s", row.get("id")
            )
    return completed, failed


def build_default_service() -> DocumentProcessingService:
    """Assemble the production processing service from settings + Supabase."""
    client = get_supabase_client()
    storage = SupabaseDocumentStorage(client=client, bucket=settings.storage_bucket)
    pipeline = DocumentProcessingPipeline(
        extractor=TextExtractor(ocr_engine=TesseractOcrEngine()),
        chunker=Chunker(),
    )
    embeddings = EmbeddingService(
        provider=_build_provider(),
        vectors=VectorRepository(client=client),
    )
    understanding = DocumentUnderstandingService(
        llm=_build_llm(),
        analyses=AnalysisRepository(client=client),
        processing=ProcessingRepository(client=client),
        vectors=VectorRepository(client=client),
    )
    return DocumentProcessingService(
        pipeline=pipeline,
        document_service=DocumentService(
            repository=DocumentRepository(client=client), storage=storage
        ),
        processing=ProcessingRepository(client=client),
        storage=storage,
        embeddings=embeddings,
        understanding=understanding,
    )


def _build_llm() -> StructuredLLM | None:
    """Build the configured LLM provider, or ``None`` when not configured.

    Returns ``None`` without error when no model/endpoint is configured so the
    document pipeline still runs: the analysis layer then records honest
    ``FAILED`` analyses instead of fabricating understanding.
    """
    if not settings.llm_model or not settings.llm_api_url:
        return None
    return build_llm_provider(
        provider=settings.llm_provider,
        model_name=settings.llm_model,
        api_url=settings.llm_api_url,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_request_timeout_seconds,
        max_attempts=settings.llm_max_attempts,
        retry_base_delay_seconds=settings.llm_retry_base_delay_seconds,
        retry_max_delay_seconds=settings.llm_retry_max_delay_seconds,
        retry_jitter_seconds=settings.llm_retry_jitter_seconds,
        requests_per_minute=settings.llm_max_requests_per_minute,
    )


def _build_provider() -> EmbeddingProvider:
    return build_embedding_provider(
        provider=settings.embedding_provider,
        model_name=settings.embedding_model,
        dimension=settings.embedding_dimension,
        batch_size=settings.embedding_batch_size,
        api_url=settings.embedding_api_url,
        api_key=settings.embedding_api_key,
        timeout_seconds=settings.embedding_request_timeout_seconds,
        max_attempts=settings.embedding_max_attempts,
        retry_base_delay_seconds=settings.embedding_retry_base_delay_seconds,
        retry_max_delay_seconds=settings.embedding_retry_max_delay_seconds,
        requests_per_minute=settings.embedding_max_requests_per_minute,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending legal documents.")
    parser.add_argument("--limit", type=int, default=10, help="maximum documents per run")
    parser.add_argument(
        "--ensure-embedding-index",
        action="store_true",
        help="confirm the embedding dimension and build the vector index",
    )
    args = parser.parse_args()
    logging.basicConfig(level=settings.log_level)

    client = get_supabase_client()
    if args.ensure_embedding_index:
        provider = _build_provider()
        try:
            dimension = provider.dimension
        except Exception as exc:
            raise SystemExit(
                f"embedding dimension could not be resolved: {exc}"
            ) from exc
        VectorRepository(client=client).ensure_embedding_index(dimension=dimension)
        logger.info(
            "vector index confirmed for dimension %s (model %s)",
            dimension,
            provider.model_name,
        )
        return

    service = build_default_service()
    completed, failed = process_pending(
        document_repository=DocumentRepository(client=client),
        processing_service=service,
        limit=args.limit,
    )
    logger.info("processed %s document(s); %s failed", completed, failed)


if __name__ == "__main__":
    main()