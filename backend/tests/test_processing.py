"""Document processing pipeline + worker tests (hermetic).

Covers, end to end against in-memory fakes:

* PDF / DOCX / OCR-image processing to READY with persisted sections,
  clauses and retrieval chunks (with source-location metadata).
* DOCX page-break approximation (page 2 detected).
* Low OCR confidence -> recorded uncertainty; OCR unavailable -> FAILED
  (never fabricated text).
* Empty/unreadable documents -> FAILED with a recorded reason.
* Retry-safe processing: only UPLOADED may start; reprocessing is
  delete-then-insert idempotent.
* The worker drain loop over a batch (completed vs failed).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.ai.embeddings.provider import DeterministicEmbeddingProvider
from app.ai.embeddings.repository import VectorRepository
from app.ai.embeddings.service import EmbeddingService
from app.core.errors import ConflictError
from app.document_processing.chunker import Chunker
from app.document_processing.extractor import TextExtractor
from app.document_processing.ocr import OcrResult
from app.document_processing.pipeline import DocumentProcessingPipeline
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.services.documents import DocumentService
from app.services.processing import DocumentProcessingService
from app.services.storage.supabase import SupabaseDocumentStorage
from app.workers.document_worker import process_pending
from tests.fakes import BUCKET, FakeSupabase
from tests.sample_docs import docx_bytes, pdf_bytes, png_bytes

EMP_CONTRACT = (
    "THIS AGREEMENT is made on the 15th day of June, 2024 between the Employer and the Employee.",
    "",
    "1. NON-COMPETE",
    "1.1 Restrictions. The Employee shall not compete with the Employer for 12 months.",
    "1.2 Remedies. The Employer may claim damages for any breach of this Clause.",
    "",
    "2. PAYMENT",
    "The Client shall pay 5,000 USD per month within 30 days of invoice.",
    "",
    "3. GOVERNING LAW",
    "This Agreement is governed by the laws of the Republic of India.",
)

OCR_TEXT = (
    "THIS AGREEMENT is made on June 1, 2023 between Party A and Party B.\n"
    "1. PAYMENT\n"
    "The Client shall pay 1,250 USD promptly upon receipt of an invoice."
)


class FakeOcrEngine:
    """Deterministic OCR stand-in (never depends on a real binary)."""

    def __init__(self, text: str, confidence: float | None = None) -> None:
        self._text = text
        self._confidence = confidence

    def ocr(self, image_bytes: bytes) -> OcrResult:
        return OcrResult(text=self._text, confidence=self._confidence)


@pytest.fixture()
def fake() -> FakeSupabase:
    return FakeSupabase()


def _document_service(fake: FakeSupabase) -> DocumentService:
    return DocumentService(
        repository=DocumentRepository(client=fake),
        storage=SupabaseDocumentStorage(client=fake, bucket=BUCKET),
        audit=AuditLogRepository(client=fake),
    )


def _processing_service(
    fake: FakeSupabase, *, ocr: FakeOcrEngine | None = None
) -> DocumentProcessingService:
    pipeline = DocumentProcessingPipeline(
        extractor=TextExtractor(ocr_engine=ocr),
        chunker=Chunker(),
    )
    embeddings = EmbeddingService(
        provider=DeterministicEmbeddingProvider(dimension=256),
        vectors=VectorRepository(client=fake),
    )
    return DocumentProcessingService(
        pipeline=pipeline,
        document_service=_document_service(fake),
        processing=ProcessingRepository(client=fake),
        storage=SupabaseDocumentStorage(client=fake, bucket=BUCKET),
        embeddings=embeddings,
    )


def _upload(fake: FakeSupabase, filename: str, content: bytes) -> dict[str, object]:
    user_id = uuid4()
    outcome = _document_service(fake).upload(
        user_id=user_id, filename=filename, content=content
    )
    return {"user_id": user_id, "document": outcome}


def _rows(fake: FakeSupabase, table: str) -> list[dict[str, object]]:
    return fake.rows_of(table)


def _chunk_messages(fake: FakeSupabase) -> list[list[object]]:
    _messages: list[list[object]] = []
    for row in _rows(fake, "document_chunks"):
        _messages.append(row["metadata"].get("uncertainties", []))
    return _messages


class TestPdfAndDocxProcessing:
    @pytest.mark.parametrize(
        "filename,content,expected_pages",
        [
            ("agreement.pdf", pdf_bytes("\n".join(EMP_CONTRACT)), 1),
            ("agreement.docx", docx_bytes(*EMP_CONTRACT), 1),
        ],
        ids=["pdf", "docx"],
    )
    def test_valid_document_reaches_ready_with_persisted_artifacts(
        self, fake, filename, content, expected_pages
    ):
        uploaded = _upload(fake, filename, content)
        document = uploaded["document"]

        service = _processing_service(fake)
        row = _rows(fake, "documents")[0]
        result = service.process(row=row)

        assert result.status == "READY"
        assert result.page_count == expected_pages

        stored = _rows(fake, "documents")[0]
        assert stored["processing_status"] == "READY"
        assert stored["processing_error"] is None
        assert stored["processed_at"] is not None

        sections = _rows(fake, "sections")
        assert any(section["title"] == "NON-COMPETE" for section in sections)
        clauses = _rows(fake, "clauses")
        assert any(clause["clause_number"] == "1.1" for clause in clauses)
        chunks = _rows(fake, "document_chunks")
        assert chunks
        assert all(chunk["document_id"] == str(document.id) for chunk in chunks)
        source = chunks[0]["metadata"]["source_location"]
        assert isinstance(source, str) and source.startswith("Page")

    def test_docx_page_break_yields_two_pages(self, fake):
        content = docx_bytes(
            *EMP_CONTRACT,
            insert_page_break_after=[len(EMP_CONTRACT) - 1],
        )
        _upload(fake, "multi.docx", content)

        service = _processing_service(fake)
        stored = _rows(fake, "documents")[0]
        result = service.process(row=stored)

        assert result.status == "READY"
        assert result.page_count == 2
        chunks = _rows(fake, "document_chunks")
        assert any(chunk["page_end"] == 2 for chunk in chunks)

    def test_pipeline_entities_are_deterministic(self, fake):
        content = pdf_bytes(
            "This Agreement (Clause 4.2) is dated March 14 2025.",
            "The Client shall pay 5,000 USD and the Employer owes 1.5.",
            "",
            "3. GOVERNING LAW",
            "Either Party may bring a claim under Section 3.1 or 3.2.",
        )
        service = _processing_service(fake)
        _upload(fake, "entities.pdf", content)
        row = _rows(fake, "documents")[0]
        service.process(row=row)

        chunks = _rows(fake, "document_chunks")
        entities = [
            entity
            for chunk in chunks
            for entity in chunk["metadata"]["entities"]
        ]
        by_type = {entity["type"] for entity in entities}
        assert "DATE" in by_type
        assert "AMOUNT" in by_type
        assert "CROSS_REFERENCE" in by_type
        assert any(
            entity["type"] == "AMOUNT" and entity["normalized"] == "5000"
            for entity in entities
        )


class TestOcrProcessing:
    def test_image_with_ocr_success(self, fake):
        content = png_bytes(*OCR_TEXT.split("\n"))
        _upload(fake, "scan.png", content)
        service = _processing_service(fake, ocr=FakeOcrEngine(text=OCR_TEXT, confidence=0.9))

        result = service.process(row=_rows(fake, "documents")[0])

        assert result.status == "READY"
        chunks = _rows(fake, "document_chunks")
        assert any("1,250 USD" in chunk["content"] for chunk in chunks)
        messages = _chunk_messages(fake)
        assert not any(messages)

    def test_low_ocr_confidence_records_uncertainty(self, fake):
        content = png_bytes("garbled ghost text")
        _upload(fake, "fuzzy.png", content)
        service = _processing_service(fake, ocr=FakeOcrEngine(text=OCR_TEXT, confidence=0.3))

        result = service.process(row=_rows(fake, "documents")[0])

        assert result.status == "READY"
        messages = _chunk_messages(fake)
        # The uncertainty must be recorded beside the possibly-wrong text.
        assert any(any("confidence" in str(message) for message in page) for page in messages)

    def test_ocr_unavailable_fails_with_recorded_reason(self, fake):
        content = png_bytes("text")
        _upload(fake, "scan.png", content)
        service = _processing_service(fake, ocr=None)  # no OCR engine configured

        result = service.process(row=_rows(fake, "documents")[0])

        assert result.status == "FAILED"
        assert "OCR" in (result.processing_error or "")
        assert _rows(fake, "document_chunks") == []


class TestFailureHandling:
    def test_empty_document_fails_without_fabrication(self, fake):
        content = docx_bytes("", "")
        _upload(fake, "blank.docx", content)
        service = _processing_service(fake)

        result = service.process(row=_rows(fake, "documents")[0])

        assert result.status == "FAILED"
        assert "No extractable text" in (result.processing_error or "")
        assert _rows(fake, "sections") == []
        assert _rows(fake, "document_chunks") == []

    def test_process_rejects_non_uploaded_state(self, fake):
        content = docx_bytes(*EMP_CONTRACT)
        _upload(fake, "already.docx", content)
        row = _rows(fake, "documents")[0]
        row["processing_status"] = "READY"
        service = _processing_service(fake)

        with pytest.raises(ConflictError):
            service.process(row=row)


class TestReprocessing:
    def test_reprocess_replaces_stale_artifacts(self, fake):
        uploaded = _upload(fake, "retry.docx", docx_bytes(*EMPLOYEE_AGREEMENT))
        user_id = uploaded["user_id"]
        document = uploaded["document"]
        service = _processing_service(fake)

        first = service.process(row=_rows(fake, "documents")[0])
        assert first.status == "READY"
        assert _rows(fake, "document_chunks")

        # Mark failed, retry, and re-process with different bytes: the stored
        # sections/clauses/chunks must be replaced, never accumulated.
        DocumentRepository(client=fake).transition(
            user_id,
            document.id,
            from_statuses=("READY",),
            to_status="FAILED",
            extra={"processing_error": "reprocessing"},
        )
        service._documents.retry(user_id=user_id, document_id=document.id)

        key = f"users/{user_id}/documents/{document.id}/original"
        fake.storage.from_(BUCKET).objects[key] = docx_bytes(*SHORT_AGREEMENT)

        result = service.process(row=_rows(fake, "documents")[0])
        assert result.status == "READY"
        # Delete-then-insert: only the NEW content's artifacts remain.
        section_titles = {section["title"] for section in _rows(fake, "sections")}
        assert section_titles == {"TERMINATION"}
        assert len(_rows(fake, "document_chunks")) == 1


class TestWorker:
    def test_process_pending_drains_batch(self, fake):
        document_service = _document_service(fake)
        user_a = uuid4()
        user_b = uuid4()
        document_service.upload(
            user_id=user_a,
            filename="a.pdf",
            content=pdf_bytes(*EMP_CONTRACT[2:]),
        )
        document_service.upload(
            user_id=user_b,
            filename="b.docx",
            content=docx_bytes("", ""),  # empty -> FAILED
        )

        service = _processing_service(fake)
        completed, failed = process_pending(
            document_repository=DocumentRepository(client=fake),
            processing_service=service,
            limit=10,
        )

        assert (completed, failed) == (1, 1)
        statuses = {row["processing_status"] for row in _rows(fake, "documents")}
        assert statuses == {"READY", "FAILED"}


# Short fixtures used by the tests above.
EMPLOYEE_AGREEMENT = (
    "1. TERMINATION",
    "1.1 Notice. Either Party may terminate this Agreement with 30 days notice.",
    "",
    "2. NOTICE",
    "Notices shall be sent by registered post.",
)
SHORT_AGREEMENT = (
    "1. TERMINATION",
    "1.1 Notice. Either Party may terminate this Agreement with 30 days notice.",
)