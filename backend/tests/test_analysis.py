"""Document understanding service + wiring tests (hermetic).

Covers, end to end against in-memory fakes:

* Processing a document through ANALYZING reaches READY and persists only
  schema-validated analyses (summary, clause extraction, attention) with
  evidence references.
* Attention items are normalized into rows and linked to their matching
  clauses; important dates/monetary terms come from deterministic extraction.
* An unconfigured LLM records honest FAILED analyses and the document still
  becomes READY — nothing is fabricated.
* Invalid/unavailable provider output records FAILED analyses (never blind
  acceptance), and the read model reports the analysis as unavailable.
* Reprocessing replaces earlier analyses (delete-then-insert idempotency).
* The understanding schema exposes no legal score or outcome verdict.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar, cast
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.ai.analysis.service import DocumentUnderstandingService
from app.ai.embeddings.provider import DeterministicEmbeddingProvider
from app.ai.embeddings.repository import VectorRepository
from app.ai.embeddings.service import EmbeddingService
from app.ai.llm.errors import LLMOutputValidationError
from app.ai.llm.models import ChatMessage
from app.ai.prompts.schemas import (
    AttentionItem,
    AttentionOutput,
    ClauseExtractionOutput,
    ClauseOutcome,
    ClauseType,
    EvidenceState,
    RelativeImportance,
    SummaryOutput,
)
from app.document_processing.chunker import Chunker
from app.document_processing.extractor import TextExtractor
from app.document_processing.pipeline import DocumentProcessingPipeline
from app.repositories.analysis import AnalysisRepository
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.schemas.analysis import DocumentUnderstandingOut
from app.services.documents import DocumentService
from app.services.processing import DocumentProcessingService
from app.services.storage.supabase import SupabaseDocumentStorage
from tests.fakes import BUCKET, FakeSupabase
from tests.sample_docs import pdf_bytes

AGREEMENT = (
    "THIS AGREEMENT is made on March 14, 2025 between Acme Corp and Jane Doe.",
    "",
    "1. TERMINATION",
    "1.1 Notice. Either Party may terminate this Agreement with 30 days notice.",
    "",
    "2. PAYMENT",
    "2.1 Payment. The Client shall pay 5,000 USD per month within 30 days of invoice.",
    "",
    "3. CONFIDENTIALITY",
    "3.1 Confidential Information. The Client shall keep Confidential Information secret.",
)

_T = TypeVar("_T", bound=BaseModel)


class StubLLM:
    """Scripted structured-generation stand-in (never touches a network)."""

    def __init__(
        self,
        *,
        outputs: dict[type[BaseModel], BaseModel] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.outputs = outputs or {}
        self.error = error
        self.calls: list[type[BaseModel]] = []
        self.model_name = "stub-model"

    def structured_generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[_T],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> _T:
        self.calls.append(schema)
        if self.error is not None:
            raise self.error
        instance = self.outputs.get(schema)
        if instance is None:
            raise AssertionError(f"no stub output registered for {schema.__name__}")
        return cast("_T", instance)


def _stub_fixtures() -> StubLLM:
    return StubLLM(
        outputs={
            SummaryOutput: SummaryOutput(
                evidence_state=EvidenceState.DOCUMENT_GROUNDED,
                overview="An employment agreement summarising the engagement terms.",
                document_type="Employment Agreement",
                purpose="Sets out termination, payment and confidentiality terms.",
                parties=["Acme Corp", "Jane Doe"],
                key_terms=["5,000 USD monthly fees"],
                obligations=["The Client shall pay monthly fees."],
                important_conditions=["Termination and confidentiality obligations apply."],
            ),
            ClauseExtractionOutput: ClauseExtractionOutput(
                evidence_state=EvidenceState.DOCUMENT_GROUNDED,
                clauses=[
                    ClauseOutcome(
                        clause_number="1.1",
                        clause_type=ClauseType.Termination,
                        title="Notice",
                        original_text=(
                            "1.1 Notice. Either Party may terminate this Agreement "
                            "with 30 days notice."
                        ),
                        explanation="Either party may end the agreement with 30 days notice.",
                    ),
                    ClauseOutcome(
                        clause_number="2.1",
                        clause_type=ClauseType.Payment,
                        title="Fees",
                        original_text=(
                            "2.1 Fees. The Client shall pay 5,000 USD per month "
                            "within 30 days of invoice."
                        ),
                        explanation="The client pays monthly fees within 30 days of invoicing.",
                    ),
                    ClauseOutcome(
                        clause_number="3.1",
                        clause_type=ClauseType.Confidentiality,
                        title="Scope",
                        original_text=(
                            "3.1 Scope. The Client shall keep Confidential Information secret."
                        ),
                        explanation="The client must keep confidential information secret.",
                    ),
                ],
            ),
            AttentionOutput: AttentionOutput(
                evidence_state=EvidenceState.DOCUMENT_GROUNDED,
                attention_items=[
                    AttentionItem(
                        attention_level=RelativeImportance.HIGH,
                        area="Termination notice period",
                        reason="A 30-day termination notice period may deserve review.",
                        source_support=(
                            "Either Party may terminate this Agreement with 30 days notice."
                        ),
                        practical_question="Is the 30-day notice period acceptable to you?",
                    ),
                    AttentionItem(
                        attention_level=RelativeImportance.MEDIUM,
                        area="Payment timing",
                        reason="Invoicing and payment timing is worth a closer look.",
                        source_support=(
                            "The Client shall pay 5,000 USD per month within 30 days of invoice."
                        ),
                        practical_question="Does the payment schedule match expectations?",
                    ),
                ],
            ),
        }
    )


@pytest.fixture()
def fake() -> FakeSupabase:
    return FakeSupabase()


def _document_service(fake: FakeSupabase) -> DocumentService:
    return DocumentService(
        repository=DocumentRepository(client=fake),
        storage=SupabaseDocumentStorage(client=fake, bucket=BUCKET),
        audit=AuditLogRepository(client=fake),
    )


def _understanding_service(
    fake: FakeSupabase, *, llm: StubLLM | None
) -> DocumentUnderstandingService:
    return DocumentUnderstandingService(
        llm=llm,
        analyses=AnalysisRepository(client=fake),
        processing=ProcessingRepository(client=fake),
        vectors=VectorRepository(client=fake),
    )


def _processing_service(
    fake: FakeSupabase, *, understanding: DocumentUnderstandingService | None = None
) -> DocumentProcessingService:
    pipeline = DocumentProcessingPipeline(
        extractor=TextExtractor(ocr_engine=None),
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
        understanding=understanding,
    )


def _upload_and_ready(
    fake: FakeSupabase, *, understanding: DocumentUnderstandingService | None
) -> dict[str, object]:
    user_id = uuid4()
    outcome = _document_service(fake).upload(
        user_id=user_id,
        filename="agreement.pdf",
        content=pdf_bytes("\n".join(AGREEMENT)),
    )
    service = _processing_service(fake, understanding=understanding)
    result = service.process(row=fake.rows_of("documents")[0])
    return {"user_id": user_id, "document_id": outcome.id, "result": result}


class TestAnalysisProcessing:
    def test_document_reaches_ready_with_validated_analyses(self, fake):
        stub = _stub_fixtures()
        understanding = _understanding_service(fake, llm=stub)
        uploaded = _upload_and_ready(fake, understanding=understanding)

        assert uploaded["result"].status == "READY"
        assert stub.calls == [
            SummaryOutput,
            ClauseExtractionOutput,
            AttentionOutput,
        ]

        analyses = fake.rows_of("analyses")
        assert len(analyses) == 3
        by_type = {row["analysis_type"]: row for row in analyses}
        summary = by_type["SUMMARY"]
        assert summary["status"] == "COMPLETED"
        assert summary["model_name"] == "stub-model"
        assert summary["prompt_version"] == "summary_prompt_v1"
        assert summary["result"]["evidence_state"] == "DOCUMENT-GROUNDED"
        assert summary["result"]["output"]["parties"] == ["Acme Corp", "Jane Doe"]
        assert summary["result"]["evidence"][0]["title"] == "Full document"

        clause_row = by_type["CLAUSE_EXTRACTION"]
        assert clause_row["status"] == "COMPLETED"
        assert len(clause_row["result"]["output"]["clauses"]) == 3

        attention_row = by_type["ATTENTION_ANALYSIS"]
        assert attention_row["status"] == "COMPLETED"

        items = fake.rows_of("attention_items")
        assert len(items) == 2
        assert all(item["clause_id"] is not None for item in items)
        assert all(item["category"] for item in items)
        assert all(item["attention_level"] in {"LOW", "MEDIUM", "HIGH"} for item in items)

    def test_attention_items_link_to_matching_clauses(self, fake):
        stub = _stub_fixtures()
        understanding = _understanding_service(fake, llm=stub)
        _upload_and_ready(fake, understanding=understanding)

        items = fake.rows_of("attention_items")
        clauses = fake.rows_of("clauses")
        linked = [item for item in items if item["clause_id"] is not None]
        assert len(linked) == 2
        clause_ids = {clause["id"] for clause in clauses}
        assert all(item["clause_id"] in clause_ids for item in linked)

    def test_unconfigured_llm_records_failed_but_document_is_ready(self, fake):
        understanding = _understanding_service(fake, llm=None)
        uploaded = _upload_and_ready(fake, understanding=understanding)

        assert uploaded["result"].status == "READY"
        analyses = fake.rows_of("analyses")
        assert len(analyses) == 3
        assert all(row["status"] == "FAILED" for row in analyses)
        assert all(
            row["error_message"] == "AI analysis is not configured for this environment."
            for row in analyses
        )
        assert fake.rows_of("attention_items") == []

        read = understanding.get_understanding(document_id=uploaded["document_id"])
        assert read.analysis_unavailable == "AI analysis is not configured for this environment."
        assert read.summary is None
        assert read.important_clauses == []
        assert read.attention_items == []
        assert read.evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE

    def test_invalid_provider_output_fails_honestly(self, fake):
        stub = StubLLM(
            error=LLMOutputValidationError(
                "The model returned output that did not match the required schema."
            )
        )
        understanding = _understanding_service(fake, llm=stub)
        uploaded = _upload_and_ready(fake, understanding=understanding)

        assert uploaded["result"].status == "READY"
        analyses = fake.rows_of("analyses")
        assert len(analyses) == 3
        assert all(row["status"] == "FAILED" for row in analyses)
        assert all("did not match the required schema" in row["error_message"] for row in analyses)
        assert fake.rows_of("attention_items") == []

        read = understanding.get_understanding(document_id=uploaded["document_id"])
        assert read.summary is None
        assert "did not match the required schema" in (read.analysis_unavailable or "")

    def test_analysis_runs_but_never_blocks_document_availability(self, fake):
        stub = _stub_fixtures()
        understanding = _understanding_service(fake, llm=stub)
        _upload_and_ready(fake, understanding=understanding)

        ready_row = fake.rows_of("documents")[0]
        assert ready_row["processing_status"] == "READY"
        assert ready_row["processed_at"] is not None
        assert ready_row["processing_error"] is None


class TestUnderstandingReadModel:
    def test_read_model_assembles_feature_set(self, fake):
        stub = _stub_fixtures()
        understanding = _understanding_service(fake, llm=stub)
        uploaded = _upload_and_ready(fake, understanding=understanding)

        read = understanding.get_understanding(document_id=uploaded["document_id"])

        assert read.evidence_state == EvidenceState.DOCUMENT_GROUNDED
        assert read.summary is not None
        assert read.summary.parties == ["Acme Corp", "Jane Doe"]
        assert read.summary.evidence[0].page_start == 1
        assert read.parties == ["Acme Corp", "Jane Doe"]
        assert read.obligations == ["The Client shall pay monthly fees."]
        assert read.analysis_unavailable is None

        assert any(
            date.value == "March 14, 2025" and date.page_start == 1
            for date in read.important_dates
        )
        assert any(
            term.value == "5,000 USD" and term.normalized == "5000"
            for term in read.monetary_terms
        )

        assert len(read.termination) == 1
        assert read.termination[0].clause_type == "Termination"
        assert read.termination[0].clause_id is not None
        assert read.termination[0].section == "TERMINATION"
        assert len(read.confidentiality) == 1
        assert len(read.important_clauses) == 3

        assert len(read.attention_items) == 2
        first = read.attention_items[0]
        assert first.title == "Termination notice period"
        assert first.attention_level == "HIGH"
        assert first.clause_id is not None

    def test_schema_exposes_no_legal_score_or_verdict(self):
        fields = set(DocumentUnderstandingOut.model_fields)
        assert not {"legal_score", "is_safe", "legality", "outcome", "decision"} & fields
        assert "important_clauses" in fields
        assert "attention_items" in fields
        assert "analysis_unavailable" in fields


class TestReprocessing:
    def test_reprocessing_replaces_previous_analyses(self, fake):
        stub = _stub_fixtures()
        understanding = _understanding_service(fake, llm=stub)
        document_id = uuid4()
        pipeline = DocumentProcessingPipeline(
            extractor=TextExtractor(ocr_engine=None),
            chunker=Chunker(),
        )
        result = pipeline.process(
            document_id=document_id,
            content=pdf_bytes("\n".join(AGREEMENT)),
            mime_type="application/pdf",
        )

        understanding.analyze(
            document_id=document_id, clauses=result.clauses, sections=result.sections
        )
        understanding.analyze(
            document_id=document_id, clauses=result.clauses, sections=result.sections
        )

        assert len(fake.rows_of("analyses")) == 3
        assert len(fake.rows_of("attention_items")) == 2
        assert stub.calls == [
            SummaryOutput,
            ClauseExtractionOutput,
            AttentionOutput,
            SummaryOutput,
            ClauseExtractionOutput,
            AttentionOutput,
        ]