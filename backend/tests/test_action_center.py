"""Action Center service + wiring tests (hermetic).

Covers the Action Center (FR-014..FR-016, US-017..US-020) end to end against
in-memory fakes:

* ``generate`` builds a deterministic review checklist from open attention
  items and extracts important dates from clause text — no model involved,
  and regeneration is delete-then-insert idempotent.
* Follow-up items are schema-validated LLM output, and every one must resolve
  to a real clause: unresolvable items are dropped, and an unavailable or
  failed LLM is an open abstention, never fabricated follow-ups.
* Professional questions are only returned when they trace to a real clause;
  otherwise the service abstains.
* Reports are persisted as private objects and downloaded through a short-lived
  signed URL only; the text separates document evidence from AI-generated
  interpretation and disclaims legal advice (database rows never carry it).
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import TypeVar, cast
from uuid import UUID, uuid4

import jwt
import pytest
from pydantic import BaseModel
from supabase import Client

from app.ai.action_center.service import ActionCenterService
from app.ai.analysis.service import DocumentUnderstandingService
from app.ai.embeddings.provider import DeterministicEmbeddingProvider
from app.ai.embeddings.repository import VectorRepository
from app.ai.embeddings.service import EmbeddingService
from app.ai.llm.errors import LLMProviderUnavailableError
from app.ai.llm.models import ChatMessage
from app.ai.prompts.schemas import (
    ActionItem,
    ActionOutput,
    AttentionItem,
    AttentionOutput,
    ClauseExtractionOutput,
    ClauseOutcome,
    ClauseType,
    EvidenceState,
    ProfessionalItem,
    ProfessionalQuestionsOutput,
    RelativeImportance,
    SummaryOutput,
)
from app.api.deps import get_action_center_service
from app.core.errors import (
    ActionNotFoundError,
    DocumentNotFoundError,
    ReportGenerationError,
    ReportNotFoundError,
    StorageError,
)
from app.document_processing.chunker import Chunker
from app.document_processing.extractor import TextExtractor
from app.document_processing.pipeline import DocumentProcessingPipeline
from app.main import app
from app.repositories.actions import ActionsRepository
from app.repositories.analysis import AnalysisRepository
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.repositories.reports import ReportsRepository
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
    "2.1 Fees. The Client shall pay 5,000 USD per month within 30 days of invoice.",
    "2.2 Effective Date. The initial term begins on January 1, 2026 and ends "
    "on December 31, 2026.",
    "",
    "3. CONFIDENTIALITY",
    "3.1 Scope. The Client shall keep Confidential Information secret.",
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
        del messages, max_tokens, temperature
        self.calls.append(schema)
        if self.error is not None:
            raise self.error
        instance = self.outputs.get(schema)
        if instance is None:
            raise AssertionError(f"no stub output registered for {schema.__name__}")
        return cast("_T", instance)


def _analysis_stub() -> StubLLM:
    return StubLLM(
        outputs={
            SummaryOutput: SummaryOutput(
                evidence_state=EvidenceState.DOCUMENT_GROUNDED,
                overview="An agreement summarising the engagement terms.",
                document_type="Service Agreement",
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
                        clause_number="2.2",
                        clause_type=ClauseType.Other,
                        title="Effective Date",
                        original_text=(
                            "2.2 Effective Date. The initial term begins on "
                            "January 1, 2026 and ends on December 31, 2026."
                        ),
                        explanation="The initial term runs through calendar year 2026.",
                    ),
                    ClauseOutcome(
                        clause_number="3.1",
                        clause_type=ClauseType.Confidentiality,
                        title="Scope",
                        original_text=(
                            "3.1 Scope. The Client shall keep Confidential "
                            "Information secret."
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


def _client(fake: FakeSupabase) -> Client:
    return cast(Client, fake)


def _document_service(fake: FakeSupabase) -> DocumentService:
    client = _client(fake)
    return DocumentService(
        repository=DocumentRepository(client=client),
        storage=SupabaseDocumentStorage(client=client, bucket=BUCKET),
        audit=AuditLogRepository(client=client),
    )


def _understanding_service(
    fake: FakeSupabase, *, llm: StubLLM
) -> DocumentUnderstandingService:
    client = _client(fake)
    return DocumentUnderstandingService(
        llm=llm,
        analyses=AnalysisRepository(client=client),
        processing=ProcessingRepository(client=client),
        vectors=VectorRepository(client=client),
    )


def _processing_service(
    fake: FakeSupabase, *, llm: StubLLM
) -> DocumentProcessingService:
    pipeline = DocumentProcessingPipeline(
        extractor=TextExtractor(ocr_engine=None),
        chunker=Chunker(),
    )
    client = _client(fake)
    embeddings = EmbeddingService(
        provider=DeterministicEmbeddingProvider(dimension=256),
        vectors=VectorRepository(client=client),
    )
    return DocumentProcessingService(
        pipeline=pipeline,
        document_service=_document_service(fake),
        processing=ProcessingRepository(client=client),
        storage=SupabaseDocumentStorage(client=client, bucket=BUCKET),
        embeddings=embeddings,
        understanding=_understanding_service(fake, llm=llm),
    )


def _action_center_service(
    fake: FakeSupabase, *, llm: StubLLM | None
) -> ActionCenterService:
    client = _client(fake)
    return ActionCenterService(
        llm=llm,
        documents=DocumentRepository(client=client),
        processing=ProcessingRepository(client=client),
        analyses=AnalysisRepository(client=client),
        actions=ActionsRepository(client=client),
        reports=ReportsRepository(client=client),
        storage=SupabaseDocumentStorage(client=client, bucket=BUCKET),
        audit=AuditLogRepository(client=client),
    )


def _upload_ready(fake: FakeSupabase) -> tuple[UUID, UUID]:
    user_id = uuid4()
    outcome = _document_service(fake).upload(
        user_id=user_id,
        filename="agreement.pdf",
        content=pdf_bytes("\n".join(AGREEMENT)),
    )
    service = _processing_service(fake, llm=_analysis_stub())
    doc_row = next(r for r in fake.rows_of("documents") if str(r["id"]) == str(outcome.id))
    result = service.process(row=doc_row)
    assert result.status == "READY", "document must reach READY before the Action Center"
    return user_id, outcome.id


def _follow_up_output() -> ActionOutput:
    return ActionOutput(
        evidence_state=EvidenceState.DOCUMENT_GROUNDED,
        actions=[
            ActionItem(
                title="Ask a professional about the termination notice period",
                priority=RelativeImportance.HIGH,
                reason="A 30-day notice period is the only termination term in the agreement.",
                source={"section": "1 TERMINATION"},
                practical_question="Is the 30-day notice period acceptable to you?",
            ),
            ActionItem(
                title="Review the monthly fees",
                priority=RelativeImportance.MEDIUM,
                reason="The monthly fee is payable within 30 days of invoice.",
                source={"clause": "2.1"},
            ),
            ActionItem(
                title="Review a clause that does not exist",
                priority=RelativeImportance.LOW,
                reason="No such clause is present in the document.",
                source={"clause": "99.99"},
            ),
        ],
    )


def _question_output() -> ProfessionalQuestionsOutput:
    return ProfessionalQuestionsOutput(
        evidence_state=EvidenceState.DOCUMENT_GROUNDED,
        questions=[
            ProfessionalItem(
                question="Is the 30-day notice period acceptable to you?",
                source={"clause": "1.1"},
            ),
            ProfessionalItem(
                question="How does the confidentiality obligation work here?",
                source={"clause": "3.1"},
            ),
            ProfessionalItem(
                question="What happens if the agreement is signed late?",
                source={"clause": "99.9"},
            ),
        ],
    )


class FailingReportStorage(SupabaseDocumentStorage):
    """Storage whose report writes always fail (robustness test)."""

    def store_report(
        self, *, user_id: UUID, document_id: UUID, report_id: UUID, content: bytes
    ) -> str:
        del user_id, document_id, report_id, content
        raise StorageError()


# -- action board ------------------------------------------------------------


class TestActionBoard:
    def test_generate_builds_checklist_and_dates_deterministically(self, fake):
        user_id, document_id = _upload_ready(fake)
        service = _action_center_service(fake, llm=None)

        board = service.generate(user_id, document_id)

        assert board.evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE
        assert board.abstention_reason is not None  # follow-ups openly abstain
        assert len(board.checklist) == 2
        assert all(item.action_type.value == "REVIEW_CLAUSE" for item in board.checklist)
        assert all(item.attention_item_id is not None for item in board.checklist)
        assert [item.title for item in board.checklist] == [
            "Termination notice period",
            "Payment timing",
        ]
        assert board.checklist[0].priority == "HIGH"
        assert board.checklist[0].source.clause == "1.1 Notice"
        assert board.follow_ups == []

        normalized = {entry.normalized for entry in board.important_dates}
        assert "2026-01-01" in normalized
        assert "2026-12-31" in normalized
        dates_2026 = [
            entry for entry in board.important_dates if entry.normalized == "2026-01-01"
        ]
        assert dates_2026[0].label == "2.2 Effective Date"
        assert dates_2026[0].source.clause == "2.2 Effective Date"

        persisted = fake.rows_of("actions")
        assert len(persisted) == 2
        assert all(row["action_type"] == "REVIEW_CLAUSE" for row in persisted)

    def test_generate_requires_owned_document(self, fake):
        user_id, _ = _upload_ready(fake)
        service = _action_center_service(fake, llm=None)

        with pytest.raises(DocumentNotFoundError):
            service.generate(user_id, uuid4())

    def test_regeneration_is_idempotent(self, fake):
        user_id, document_id = _upload_ready(fake)
        service = _action_center_service(fake, llm=None)

        first = service.generate(user_id, document_id)
        second = service.generate(user_id, document_id)

        assert [item.id for item in first.checklist] != [item.id for item in second.checklist]
        assert len(fake.rows_of("actions")) == 2
        assert len(second.checklist) == 2

    def test_follow_ups_must_resolve_to_real_clauses(self, fake):
        user_id, document_id = _upload_ready(fake)
        service = _action_center_service(
            fake, llm=StubLLM(outputs={ActionOutput: _follow_up_output()})
        )

        board = service.generate(user_id, document_id)

        assert board.evidence_state == EvidenceState.DOCUMENT_GROUNDED
        assert board.abstention_reason is None
        types = [item.action_type.value for item in board.follow_ups]
        assert "ASK_PROFESSIONAL" in types
        assert "FOLLOW_UP" in types
        clauses = {item.source.clause for item in board.follow_ups}
        assert clauses == {"1.1 Notice", "2.1 Fees"}
        assert not any("99.99" in (item.source.clause or "") for item in board.follow_ups)
        assert all(item.source.clause for item in board.follow_ups)
        assert len(fake.rows_of("actions")) == 2 + 2

    def test_unresolvable_follow_ups_abstain_without_fabrication(self, fake):
        user_id, document_id = _upload_ready(fake)
        output = ActionOutput(
            evidence_state=EvidenceState.DOCUMENT_GROUNDED,
            actions=[
                ActionItem(
                    title="Verify an unrelated claim",
                    priority=RelativeImportance.MEDIUM,
                    reason="This has no basis in the document.",
                    source={"clause": "77.7"},
                )
            ],
        )
        service = _action_center_service(
            fake, llm=StubLLM(outputs={ActionOutput: output})
        )

        board = service.generate(user_id, document_id)

        assert board.follow_ups == []
        assert len(board.checklist) == 2
        assert len(fake.rows_of("actions")) == 2

    def test_llm_failure_is_an_open_abstention(self, fake):
        user_id, document_id = _upload_ready(fake)
        service = _action_center_service(
            fake, llm=StubLLM(error=LLMProviderUnavailableError())
        )

        board = service.generate(user_id, document_id)

        assert board.follow_ups == []
        assert board.evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE
        assert board.abstention_reason is not None
        assert "could not be completed" in board.abstention_reason
        assert len(fake.rows_of("actions")) == 2  # checklist still persisted

    def test_list_actions_filters_and_update_status(self, fake):
        user_id, document_id = _upload_ready(fake)
        service = _action_center_service(fake, llm=None)
        service.generate(user_id, document_id)

        all_actions = service.list_actions(user_id)
        assert len(all_actions) == 2
        assert [
            item for item in service.list_actions(user_id, document_id=document_id)
        ] == all_actions
        assert all(
            item.priority == "HIGH"
            for item in service.list_actions(user_id, priority="HIGH")
        )
        assert service.list_actions(user_id, status="COMPLETED") == []

        target = all_actions[0]
        updated = service.update_action_status(user_id, target.id, "COMPLETED")
        assert updated.status.value == "COMPLETED"
        completed = service.list_actions(user_id, status="COMPLETED")
        assert [item.id for item in completed] == [target.id]

        with pytest.raises(ActionNotFoundError):
            service.update_action_status(user_id, uuid4(), "COMPLETED")


# -- professional questions --------------------------------------------------


class TestProfessionalQuestions:
    def test_questions_are_traceable_and_unresolvable_dropped(self, fake):
        user_id, document_id = _upload_ready(fake)
        service = _action_center_service(
            fake, llm=StubLLM(outputs={ProfessionalQuestionsOutput: _question_output()})
        )

        result = service.questions(user_id, document_id)

        assert result.evidence_state == EvidenceState.DOCUMENT_GROUNDED
        assert len(result.questions) == 2
        clauses = {question.source.clause for question in result.questions}
        assert clauses == {"1.1 Notice", "3.1 Scope"}
        assert all(question.source.clause for question in result.questions)

    def test_questions_abstain_when_nothing_survives(self, fake):
        user_id, document_id = _upload_ready(fake)
        output = ProfessionalQuestionsOutput(
            evidence_state=EvidenceState.DOCUMENT_GROUNDED,
            questions=[
                ProfessionalItem(
                    question="What happens if I sign late?", source={"clause": "77.7"}
                )
            ],
        )
        service = _action_center_service(
            fake, llm=StubLLM(outputs={ProfessionalQuestionsOutput: output})
        )

        result = service.questions(user_id, document_id)

        assert result.evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE
        assert result.questions == []
        assert (
            result.abstention_reason is not None
            and "No professional question could be traced" in result.abstention_reason
        )

    def test_questions_abstain_without_llm(self, fake):
        user_id, document_id = _upload_ready(fake)
        service = _action_center_service(fake, llm=None)

        result = service.questions(user_id, document_id)

        assert result.evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE
        assert result.questions == []


# -- reports -----------------------------------------------------------------


class TestReports:
    def test_report_is_ready_stored_and_downloadable_via_signed_url(self, fake):
        user_id, document_id = _upload_ready(fake)
        service = _action_center_service(fake, llm=None)

        report = service.generate_report(user_id, document_id)

        assert report.status == "READY"
        assert report.report_type == "DOCUMENT_REVIEW"
        row = fake.rows_of("reports")[0]
        assert row["status"] == "READY"
        storage_key = row["storage_key"]
        assert storage_key == (
            f"users/{user_id}/documents/{document_id}/reports/{report.report_id}.txt"
        )

        bucket = fake.storage.from_(BUCKET)
        content = bucket.download(storage_key).decode("utf-8")
        assert "=== DOCUMENT EVIDENCE ===" in content
        assert "=== AI-GENERATED INTERPRETATION ===" in content
        assert "January 1, 2026" in content
        assert "December 31, 2026" in content
        assert "Important Dates" in content
        assert "Questions for Professional" in content
        assert "AI & Privacy Disclaimer" in content
        assert "does not constitute legal advice" in content

        # Required report sections and disclaimer
        assert "Document Title" in content
        assert "Generated Timestamp" in content
        assert "Summary" in content
        assert "Key Clauses" in content
        assert "Monetary Terms" in content
        assert "5,000 USD" in content
        assert "Attention Items" in content
        assert "Review Checklist" in content
        assert "Professional Questions" in content
        assert "Citations" in content
        assert "Responsible AI Disclaimer" in content
        assert (
            "This tool provides informational assistance and does not provide "
            "legal advice or legal representation."
            in content
        )

        audits = fake.rows_of("audit_logs")
        assert any(row["action"] == "report_generated" for row in audits)

        download = service.report_download_url(user_id, report.report_id)
        assert f"/object/sign/{storage_key}?token=abc" == download.download_url

        assert service.get_report(user_id, report.report_id).report_id == report.report_id
        assert [r.report_id for r in service.list_reports(user_id)] == [report.report_id]

    def test_report_storage_failure_marks_failed(self, fake):
        user_id, document_id = _upload_ready(fake)
        client = _client(fake)
        service = ActionCenterService(
            llm=None,
            documents=DocumentRepository(client=client),
            processing=ProcessingRepository(client=client),
            analyses=AnalysisRepository(client=client),
            actions=ActionsRepository(client=client),
            reports=ReportsRepository(client=client),
            storage=FailingReportStorage(client=client, bucket=BUCKET),
            audit=AuditLogRepository(client=client),
        )

        with pytest.raises(ReportGenerationError):
            service.generate_report(user_id, document_id)

        assert fake.rows_of("reports")[0]["status"] == "FAILED"

    def test_report_not_ready_or_unowned_is_guarded(self, fake):
        user_id, document_id = _upload_ready(fake)
        other = uuid4()
        service = _action_center_service(fake, llm=None)

        with pytest.raises(ReportNotFoundError):
            service.get_report(user_id, uuid4())
        with pytest.raises(ReportNotFoundError):
            service.report_download_url(user_id, uuid4())

        creating = ReportsRepository(client=_client(fake)).create(
            user_id=other,
            document_id=document_id,
            report_type="DOCUMENT_REVIEW",
            status="GENERATING",
        )
        with pytest.raises(ReportNotFoundError):
            service.report_download_url(user_id, UUID(str(creating["id"])))
        with pytest.raises(ReportGenerationError):
            service.report_download_url(other, UUID(str(creating["id"])))

    def test_report_user_isolation_and_authorization(self, fake):
        user_a, doc_a = _upload_ready(fake)
        user_b, _ = _upload_ready(fake)
        service = _action_center_service(fake, llm=None)

        # User A generates a report for doc A
        report_a = service.generate_report(user_a, doc_a)
        assert report_a.status == "READY"

        # User B cannot generate a report for User A's doc
        with pytest.raises(DocumentNotFoundError):
            service.generate_report(user_b, doc_a)

        # User B cannot get User A's report metadata
        with pytest.raises(ReportNotFoundError):
            service.get_report(user_b, report_a.report_id)

        # User B cannot download User A's report
        with pytest.raises(ReportNotFoundError):
            service.report_download_url(user_b, report_a.report_id)

        # User B's reports list does NOT include User A's report
        assert [r.report_id for r in service.list_reports(user_b)] == []


# -- HTTP wiring -------------------------------------------------------------


class TestActionCenterEndpoint:
    @pytest.fixture()
    def action_env(self, client):
        fake = FakeSupabase()
        holder: dict[str, ActionCenterService | None] = {"service": None}
        app.dependency_overrides[get_action_center_service] = lambda: holder["service"]
        yield fake, holder
        app.dependency_overrides.clear()

    @staticmethod
    def _auth(jwt_secret: str, user_id: UUID) -> dict[str, str]:
        payload = {"sub": str(user_id), "exp": time.time() + 3600}
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def test_generate_without_auth_is_401(self, client, action_env):
        response = client.post(f"/api/v1/documents/{uuid4()}/action-center")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_unknown_document_is_404(self, client, action_env, jwt_secret):
        fake, holder = action_env
        holder["service"] = _action_center_service(fake, llm=None)
        token = self._auth(jwt_secret, uuid4())

        response = client.post(f"/api/v1/documents/{uuid4()}/action-center", headers=token)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_generate_and_track_actions_round_trip(self, client, action_env, jwt_secret):
        fake, holder = action_env
        user_id, document_id = _upload_ready(fake)
        holder["service"] = _action_center_service(
            fake, llm=StubLLM(outputs={ActionOutput: _follow_up_output()})
        )
        token = self._auth(jwt_secret, user_id)

        created = client.post(
            f"/api/v1/documents/{document_id}/action-center", headers=token
        )
        assert created.status_code == 201
        data = created.json()["data"]
        assert len(data["checklist"]) == 2
        assert len(data["follow_ups"]) == 2
        assert data["evidence_state"] == "DOCUMENT-GROUNDED"
        assert "2026-01-01" in [
            entry["normalized"] for entry in data["important_dates"]
        ]

        listed = client.get("/api/v1/actions", headers=token)
        assert listed.status_code == 200
        assert len(listed.json()["data"]) == 4

        action_id = listed.json()["data"][0]["id"]
        updated = client.patch(
            f"/api/v1/actions/{action_id}", headers=token, json={"status": "COMPLETED"}
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["status"] == "COMPLETED"

        filtered = client.get("/api/v1/actions?priority=HIGH", headers=token)
        assert filtered.status_code == 200
        assert all(item["priority"] == "HIGH" for item in filtered.json()["data"])
        assert len(filtered.json()["data"]) == 2

    def test_patch_unknown_action_is_404(self, client, action_env, jwt_secret):
        fake, holder = action_env
        user_id, _ = _upload_ready(fake)
        holder["service"] = _action_center_service(fake, llm=None)
        token = self._auth(jwt_secret, user_id)

        response = client.patch(
            f"/api/v1/actions/{uuid4()}", headers=token, json={"status": "COMPLETED"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ACTION_NOT_FOUND"

    def test_questions_endpoint(self, client, action_env, jwt_secret):
        fake, holder = action_env
        user_id, document_id = _upload_ready(fake)
        holder["service"] = _action_center_service(
            fake,
            llm=StubLLM(outputs={ProfessionalQuestionsOutput: _question_output()}),
        )
        token = self._auth(jwt_secret, user_id)

        response = client.post(
            f"/api/v1/documents/{document_id}/questions/generate",
            headers=token,
            params={"user_context": "I am a small business owner."},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["evidence_state"] == "DOCUMENT-GROUNDED"
        assert [q["source"]["clause"] for q in data["questions"]] == [
            "1.1 Notice",
            "3.1 Scope",
        ]

    def test_report_lifecycle_over_http(self, client, action_env, jwt_secret):
        fake, holder = action_env
        user_id, document_id = _upload_ready(fake)
        holder["service"] = _action_center_service(fake, llm=None)
        token = self._auth(jwt_secret, user_id)

        created = client.post(
            f"/api/v1/documents/{document_id}/reports", headers=token
        )
        assert created.status_code == 201
        report_id = created.json()["data"]["report_id"]
        assert created.json()["data"]["status"] == "READY"

        listing = client.get("/api/v1/reports", headers=token)
        assert listing.status_code == 200
        assert [row["report_id"] for row in listing.json()["data"]] == [report_id]

        download = client.get(f"/api/v1/reports/{report_id}/download", headers=token)
        assert download.status_code == 200
        url = download.json()["data"]["download_url"]
        assert "/object/sign/users/" in url
        assert url.endswith(f"{report_id}.txt?token=abc")

        missing = client.get(f"/api/v1/reports/{uuid4()}/download", headers=token)
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "REPORT_NOT_FOUND"

    def test_report_http_authorization_and_isolation(
        self, client, action_env, jwt_secret
    ):
        fake, holder = action_env
        user_a, doc_a = _upload_ready(fake)
        user_b, _ = _upload_ready(fake)
        holder["service"] = _action_center_service(fake, llm=None)

        token_a = self._auth(jwt_secret, user_a)
        token_b = self._auth(jwt_secret, user_b)

        # Unauthenticated calls are 401
        assert client.post(f"/api/v1/documents/{doc_a}/reports").status_code == 401
        assert client.get("/api/v1/reports").status_code == 401
        assert client.get(f"/api/v1/reports/{uuid4()}").status_code == 401
        assert client.get(f"/api/v1/reports/{uuid4()}/download").status_code == 401

        # User A creates a report
        created = client.post(f"/api/v1/documents/{doc_a}/reports", headers=token_a)
        assert created.status_code == 201
        report_id = created.json()["data"]["report_id"]

        # User B cannot generate report for User A's document (404)
        b_create = client.post(f"/api/v1/documents/{doc_a}/reports", headers=token_b)
        assert b_create.status_code == 404
        assert b_create.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

        # User B listing reports does not see User A's report
        b_list = client.get("/api/v1/reports", headers=token_b)
        assert b_list.status_code == 200
        assert b_list.json()["data"] == []

        # User B cannot get User A's report metadata (404)
        b_get = client.get(f"/api/v1/reports/{report_id}", headers=token_b)
        assert b_get.status_code == 404
        assert b_get.json()["error"]["code"] == "REPORT_NOT_FOUND"

        # User B cannot download User A's report (404)
        b_dl = client.get(f"/api/v1/reports/{report_id}/download", headers=token_b)
        assert b_dl.status_code == 404
        assert b_dl.json()["error"]["code"] == "REPORT_NOT_FOUND"