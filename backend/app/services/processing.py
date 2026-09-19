"""Document processing orchestration for the background worker.

Drives one document through the retry-safe state machine while running the
deterministic extraction pipeline, persisting its output, indexing its chunks
for retrieval and running the AI document-understanding analyses (when an LLM
is configured):

    UPLOADED -> EXTRACTING -> PROCESSING -> ANALYZING -> READY
       |                                        ^
       +-> FAILED (recorded) -------------------+

``EXTRACTING`` covers extraction + parsing; ``PROCESSING`` covers persisting
sections/clauses/chunks and computing their embeddings; ``ANALYZING`` runs the
schema-validated document analyses and is skipped (PROCESSING -> READY) when no
LLM is configured. ``VALIDATING`` happens at upload and is not entered here
(see docs/03_TECH/System-Architecture.md §19 and FR-003).

Honesty guarantees (AGENT.md "no fake implementations"):
* A document with no readable text, an unreadable file, unavailable OCR or a
  failing embedding provider is marked FAILED with the exact reason — the
  pipeline never invents text and never reports READY without a searchable
  index.
* Persisting is delete-then-insert, so reprocessing is idempotent (embeddings
  are rebuilt for the fresh chunk rows each run).
* Document contents and embedding vectors never enter log output.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.ai.analysis.service import DocumentUnderstandingService
from app.ai.embeddings.errors import EmbeddingError
from app.ai.embeddings.service import EmbeddingService
from app.core.errors import ConflictError, DocumentNotFoundError, StorageError
from app.document_processing.extractor import ExtractionError
from app.document_processing.ocr import OcrUnavailableError
from app.document_processing.pipeline import (
    DocumentProcessingPipeline,
    ProcessingTextEmptyError,
)
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.schemas.documents import DocumentOut
from app.services.documents import DocumentService
from app.services.storage.base import DocumentStorage

logger = logging.getLogger("app.processing")

_MESSAGE_LIMIT = 500


class DocumentProcessingService:
    """Runs a single document through extraction, persistence and indexing."""

    def __init__(
        self,
        *,
        pipeline: DocumentProcessingPipeline,
        document_service: DocumentService,
        processing: ProcessingRepository,
        storage: DocumentStorage,
        embeddings: EmbeddingService,
        understanding: DocumentUnderstandingService | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._documents = document_service
        self._processing = processing
        self._storage = storage
        self._embeddings = embeddings
        self._understanding = understanding

    def process(self, row: dict[str, Any]) -> DocumentOut:
        """Process one ``documents`` row (must be in ``UPLOADED`` state)."""
        user_id = UUID(str(row["user_id"]))
        document_id = UUID(str(row["id"]))
        if row.get("processing_status") != "UPLOADED":
            raise ConflictError("The document cannot be processed in its current state.")

        self._documents.transition(
            user_id=user_id,
            document_id=document_id,
            from_statuses=("UPLOADED",),
            to_status="EXTRACTING",
        )

        try:
            content = self._storage.read(str(row["storage_key"]))
            result = self._pipeline.process(
                document_id=document_id,
                content=content,
                mime_type=str(row["mime_type"] or ""),
            )
        except (ProcessingTextEmptyError, ExtractionError, OcrUnavailableError) as exc:
            return self._record_failure(user_id, document_id, _message(exc))
        except (DocumentNotFoundError, StorageError) as exc:
            self._record_failure(
                user_id, document_id, "The original file could not be read from storage."
            )
            raise exc from None
        except Exception:
            logger.exception("document extraction failed unexpectedly")
            self._record_failure(user_id, document_id, "Extraction failed unexpectedly.")
            raise

        try:
            self._documents.transition(
                user_id=user_id,
                document_id=document_id,
                from_statuses=("EXTRACTING",),
                to_status="PROCESSING",
            )
            self._processing.replace(
                document_id,
                user_id=user_id,
                sections=result.sections,
                clauses=result.clauses,
                chunks=result.chunks,
            )
            self._embeddings.index_document(
                document_id=document_id, user_id=user_id, chunks=result.chunks
            )
            self._documents.transition(
                user_id=user_id,
                document_id=document_id,
                from_statuses=("PROCESSING",),
                to_status="ANALYZING",
            )
            if self._understanding is not None:
                try:
                    self._understanding.analyze(
                        document_id=document_id,
                        clauses=result.clauses,
                        sections=result.sections,
                    )
                except Exception:
                    # Analysis failures must not block document availability:
                    # the service records them honestly and the extraction
                    # artifacts remain usable (see AI-Architecture.md §15).
                    logger.exception("AI document analysis failed unexpectedly")
            return self._documents.mark_ready(
                user_id=user_id, document_id=document_id, page_count=result.page_count
            )
        except EmbeddingError as exc:
            return self._record_failure(
                user_id,
                document_id,
                "The document was extracted but could not be added to the "
                f"search index: {_message(exc)}",
            )
        except Exception:
            try:
                self._record_failure(
                    user_id,
                    document_id,
                    "Persisting the extracted content failed and processing stopped.",
                )
            except Exception:
                logger.warning("failed to record processing failure for %s", document_id)
            raise

    # -- helpers -------------------------------------------------------------

    def _record_failure(self, user_id: UUID, document_id: UUID, message: str) -> DocumentOut:
        """Mark the document FAILED with a safe message (state-machine safe)."""
        return self._documents.mark_failed(
            user_id=user_id, document_id=document_id, message=message
        )


def build_processing_service(
    *,
    documents: DocumentRepository,
    processing: ProcessingRepository,
    storage: DocumentStorage,
    pipeline: DocumentProcessingPipeline,
    embeddings: EmbeddingService,
) -> DocumentProcessingService:
    """Assemble a processing service with all its collaborators."""
    document_service = DocumentService(repository=documents, storage=storage)
    return DocumentProcessingService(
        pipeline=pipeline,
        document_service=document_service,
        processing=processing,
        storage=storage,
        embeddings=embeddings,
    )


def _message(exc: Exception) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text[: _MESSAGE_LIMIT]