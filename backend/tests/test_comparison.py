"""Document comparison tests (hermetic).

Covers the deterministic FR-013 pipeline against in-memory fakes:

* Identical documents -> every clause classified UNCHANGED, zero real changes.
* One changed clause -> exactly one MODIFIED with both sides quoted and cited.
* Added / removed clauses -> exactly one ADDED / REMOVED (no counterpart cited
  on the missing side).
* Multiple changes -> the full ADDED/REMOVED/MODIFIED/UNCHANGED mix.
* Unrelated sections -> clauses never match across different sections; every
  clause is reported ADDED or REMOVED.
* Ownership gate -> a comparison referencing any unowned document fails, and a
  persisted comparison is only readable by its owner.
* Honesty -> the model can never reclassify or drop a real change; on
  abstention, failure or a missing LLM the explanation falls back to a fixed
  message and MEDIUM importance instead of fabrication.
* API -> create/read round-trip on the three endpoints, auth + 404 behaviour.
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Sequence
from typing import TypeVar, cast
from uuid import UUID, uuid4

import jwt
import pytest
from pydantic import BaseModel

from app.ai.comparison.service import DocumentComparisonService
from app.ai.embeddings.provider import DeterministicEmbeddingProvider
from app.ai.embeddings.repository import VectorRepository
from app.ai.embeddings.service import EmbeddingService
from app.ai.llm.errors import LLMProviderUnavailableError
from app.ai.llm.models import ChatMessage
from app.ai.prompts.schemas import ChangeType, ComparisonOutput, EvidenceState, RelativeImportance
from app.api.deps import get_comparison_service
from app.core.errors import ComparisonError, ComparisonNotFoundError, DocumentNotFoundError
from app.document_processing.chunker import Chunker
from app.document_processing.extractor import TextExtractor
from app.document_processing.pipeline import DocumentProcessingPipeline
from app.main import app
from app.repositories.audit import AuditLogRepository
from app.repositories.comparisons import ComparisonRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.services.documents import DocumentService
from app.services.processing import DocumentProcessingService
from app.services.storage.supabase import SupabaseDocumentStorage
from tests.fakes import BUCKET, FakeSupabase
from tests.sample_docs import docx_bytes

MODEL = "test-model-v1"
DIMENSION = 256

P1 = (
    "1. TERMINATION",
    "1.1 Notice. The Employee may terminate this Agreement by giving "
    "30 days written notice.",
    "1.2 Severance. The Employer shall pay severance compensation for each "
    "completed year.",
    "",
    "2. COMPENSATION",
    "2.1 Salary. The Employee shall receive an annual salary of 100,000 USD.",
)

P1_LONGER_NOTICE = (
    "1. TERMINATION",
    "1.1 Notice. The Employee may terminate this Agreement by giving "
    "90 days written notice.",
    "1.2 Severance. The Employer shall pay severance compensation for each "
    "completed year.",
    "",
    "2. COMPENSATION",
    "2.1 Salary. The Employee shall receive an annual salary of 100,000 USD.",
)

P1_NON_COMPETE = P1[:3] + ("1.3 Non-compete. The Employee shall not compete "
    "with the Employer for 12 months.",) + P1[3:]

P1_NO_SEVERANCE = P1[:2] + P1[3:]

P1_MULTI = (
    "1. TERMINATION",
    "1.1 Notice. The Employee may terminate this Agreement by giving "
    "45 days written notice.",
    "1.3 Non-compete. The Employee shall not compete with the Employer for "
    "12 months.",
    "",
    "2. COMPENSATION",
    "2.1 Salary. The Employee shall receive an annual salary of 100,000 USD.",
)

UNRELATED_B = (
    "3. TRAVEL",
    "3.1 Hotels. The Client shall book business-class hotels for the "
    "consultant during assignments.",
    "",
    "4. EQUIPMENT",
    "4.1 Laptops. The Company shall provide a laptop and a mobile phone.",
)

# Same clauses as P1, but a differing preamble line so upload dedup does not
# reject it. The preamble is not a section heading or clause, so a clause-level
# comparison still sees two identical documents.
P1_COPY = ("Reference copy retained for internal records.",) + P1

_Q = TypeVar("_Q", bound=BaseModel)

_FALLBACK_EXPLANATION = (
    "This clause text differs between the two versions; the AI explanation is "
    "not available right now."
)


def _grounded(explanation: str, importance: RelativeImportance) -> ComparisonOutput:
    return ComparisonOutput(
        change_type=ChangeType.MODIFIED,
        before="before",
        after="after",
        explanation=explanation,
        importance=importance,
    )


class StubComparison:
    """Scripted structured comparison generation (never touches a network)."""

    def __init__(
        self,
        *,
        answers: dict[str, ComparisonOutput] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.answers = answers or {}
        self.error = error
        self.calls = 0
        self.model_name = "stub-model"

    def structured_generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[_Q],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> _Q:
        self.calls += 1
        if schema is not ComparisonOutput:
            raise AssertionError(f"unexpected schema: {schema.__name__}")
        if self.error is not None:
            raise self.error
        user_message = str(messages[-1].content)
        key = next((candidate for candidate in self.answers if candidate in user_message), None)
        instance = self.answers.get(key) if key is not None else None
        if instance is None:
            raise AssertionError("no stub answer registered for comparison input")
        return cast("_Q", instance)


def _document_service(fake: FakeSupabase) -> DocumentService:
    return DocumentService(
        repository=DocumentRepository(client=fake),
        storage=SupabaseDocumentStorage(client=fake, bucket=BUCKET),
        audit=AuditLogRepository(client=fake),
    )


def _upload_ready(fake: FakeSupabase, user_id: UUID, document: tuple[str, ...]) -> UUID:
    service = _document_service(fake)
    outcome = service.upload(
        user_id=user_id, filename="agreement.docx", content=docx_bytes(*document)
    )
    pipeline = DocumentProcessingPipeline(
        extractor=TextExtractor(ocr_engine=None),
        chunker=Chunker(),
    )
    processing = DocumentProcessingService(
        pipeline=pipeline,
        document_service=service,
        processing=ProcessingRepository(client=fake),
        storage=SupabaseDocumentStorage(client=fake, bucket=BUCKET),
        embeddings=_embedding_service(fake),
    )
    row = next(row for row in fake.rows_of("documents") if row["id"] == str(outcome.id))
    result = processing.process(row=row)
    assert result.status == "READY", "document must reach READY before comparing"
    return outcome.id


def _embedding_service(fake: FakeSupabase) -> EmbeddingService:
    return EmbeddingService(
        provider=DeterministicEmbeddingProvider(model_name=MODEL, dimension=DIMENSION),
        vectors=VectorRepository(client=fake),
    )


def _comparison_service(fake: FakeSupabase, *, llm) -> DocumentComparisonService:
    return DocumentComparisonService(
        llm=llm,
        documents=DocumentRepository(client=fake),
        processing=ProcessingRepository(client=fake),
        comparisons=ComparisonRepository(client=fake),
    )


@pytest.fixture()
def fake() -> FakeSupabase:
    return FakeSupabase()


def _types(changes) -> Counter:
    return Counter(change.type for change in changes)


class TestComparisonPipeline:
    def test_identical_documents_have_only_unchanged_clauses(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, P1_COPY)
        service = _comparison_service(fake, llm=None)

        result = service.compare(
            user_id=user_id, document_a_id=first, document_b_id=second
        )

        assert result.document_a_id == first
        assert result.document_b_id == second
        assert result.status == "COMPLETED"
        assert result.summary == "0 modified, 0 added, 0 removed, 3 unchanged."

        changes = service.list_changes(user_id, result.comparison_id).changes
        assert len(changes) == 3
        assert _types(changes) == {ChangeType.UNCHANGED: 3}
        for change in changes:
            assert change.citation_a is not None
            assert change.citation_b is not None
            assert change.citation_b.document_id == second

    def test_one_changed_clause_is_modified_with_both_sides_cited(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, P1_LONGER_NOTICE)
        stub = StubComparison(
            answers={
                "30 days": _grounded(
                    "The notice period increased from 30 to 90 days.",
                    RelativeImportance.HIGH,
                )
            }
        )
        service = _comparison_service(fake, llm=stub)

        result = service.compare(
            user_id=user_id, document_a_id=first, document_b_id=second
        )
        changes = service.list_changes(user_id, result.comparison_id).changes

        assert stub.calls == 1
        assert _types(changes) == {
            ChangeType.MODIFIED: 1,
            ChangeType.UNCHANGED: 2,
        }
        modified = next(change for change in changes if change.type == ChangeType.MODIFIED)
        assert modified.section == "1 TERMINATION"
        assert modified.clause == "1.1 Notice"
        assert "30 days" in modified.before
        assert "90 days" in modified.after
        assert modified.explanation == "The notice period increased from 30 to 90 days."
        assert modified.importance == RelativeImportance.HIGH
        assert modified.citation_a is not None
        assert modified.citation_b is not None
        assert modified.citation_a.document_id == first
        assert modified.citation_b.document_id == second
        assert modified.citation_a.source_text == modified.before
        assert modified.citation_b.source_text == modified.after

    def test_added_clause_has_only_a_b_citation(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, P1_NON_COMPETE)
        service = _comparison_service(fake, llm=None)

        result = service.compare(
            user_id=user_id, document_a_id=first, document_b_id=second
        )
        changes = service.list_changes(user_id, result.comparison_id).changes

        assert _types(changes) == {
            ChangeType.ADDED: 1,
            ChangeType.UNCHANGED: 3,
        }
        added = next(change for change in changes if change.type == ChangeType.ADDED)
        assert added.section == "1 TERMINATION"
        assert added.clause == "1.3 Non-compete"
        assert added.citation_a is None
        assert added.citation_b is not None
        assert added.citation_b.document_id == second
        assert "non" in added.citation_b.source_text.lower()

    def test_removed_clause_has_only_an_a_citation(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, P1_NO_SEVERANCE)
        service = _comparison_service(fake, llm=None)

        result = service.compare(
            user_id=user_id, document_a_id=first, document_b_id=second
        )
        changes = service.list_changes(user_id, result.comparison_id).changes

        assert _types(changes) == {
            ChangeType.REMOVED: 1,
            ChangeType.UNCHANGED: 2,
        }
        removed = next(change for change in changes if change.type == ChangeType.REMOVED)
        assert removed.section == "1 TERMINATION"
        assert removed.clause == "1.2 Severance"
        assert removed.citation_a is not None
        assert removed.citation_b is None
        assert removed.citation_a.document_id == first

    def test_multiple_changes_are_all_reported(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, P1_MULTI)
        stub = StubComparison(
            answers={"30 days": _grounded("The notice period changed.", RelativeImportance.MEDIUM)}
        )
        service = _comparison_service(fake, llm=stub)

        result = service.compare(
            user_id=user_id, document_a_id=first, document_b_id=second
        )
        changes = service.list_changes(user_id, result.comparison_id).changes

        assert stub.calls == 1
        assert result.summary == "1 modified, 1 added, 1 removed, 1 unchanged."
        assert _types(changes) == {
            ChangeType.MODIFIED: 1,
            ChangeType.ADDED: 1,
            ChangeType.REMOVED: 1,
            ChangeType.UNCHANGED: 1,
        }
        assert len(fake.rows_of("comparison_changes")) == 4
        by_clause = {change.clause: change for change in changes}
        assert by_clause["1.1 Notice"].type == ChangeType.MODIFIED
        assert by_clause["1.2 Severance"].type == ChangeType.REMOVED
        assert by_clause["1.3 Non-compete"].type == ChangeType.ADDED
        assert by_clause["2.1 Salary"].type == ChangeType.UNCHANGED

    def test_unrelated_sections_never_accidentally_match(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, UNRELATED_B)
        service = _comparison_service(fake, llm=None)

        result = service.compare(
            user_id=user_id, document_a_id=first, document_b_id=second
        )
        changes = service.list_changes(user_id, result.comparison_id).changes

        assert _types(changes) == {
            ChangeType.REMOVED: 3,
            ChangeType.ADDED: 2,
        }
        for change in changes:
            assert change.type in (ChangeType.REMOVED, ChangeType.ADDED)
        assert {change.section for change in changes} == {
            "1 TERMINATION",
            "2 COMPENSATION",
            "3 TRAVEL",
            "4 EQUIPMENT",
        }


class TestOwnershipGate:
    def test_both_documents_must_be_owned_by_the_same_user(self, fake):
        owner = uuid4()
        other = uuid4()
        doc_a = _upload_ready(fake, owner, P1)
        doc_b = _upload_ready(fake, other, P1_LONGER_NOTICE)
        service = _comparison_service(fake, llm=None)

        with pytest.raises(DocumentNotFoundError):
            service.compare(user_id=owner, document_a_id=doc_a, document_b_id=doc_b)
        with pytest.raises(DocumentNotFoundError):
            service.compare(user_id=other, document_a_id=doc_a, document_b_id=doc_b)
        assert fake.rows_of("comparisons") == []

    def test_missing_document_raises_before_any_comparison_work(self, fake):
        user_id = uuid4()
        doc_a = _upload_ready(fake, user_id, P1)
        service = _comparison_service(fake, llm=None)

        with pytest.raises(DocumentNotFoundError):
            service.compare(
                user_id=user_id, document_a_id=doc_a, document_b_id=uuid4()
            )

    def test_comparing_a_document_to_itself_is_rejected(self, fake):
        user_id = uuid4()
        doc_a = _upload_ready(fake, user_id, P1)
        service = _comparison_service(fake, llm=None)

        with pytest.raises(ComparisonError):
            service.compare(user_id=user_id, document_a_id=doc_a, document_b_id=doc_a)

    def test_comparison_reads_are_owner_scoped(self, fake):
        owner = uuid4()
        other = uuid4()
        doc_a = _upload_ready(fake, owner, P1)
        doc_b = _upload_ready(fake, owner, P1_LONGER_NOTICE)
        service = _comparison_service(fake, llm=None)

        result = service.compare(user_id=owner, document_a_id=doc_a, document_b_id=doc_b)
        comparison_id = result.comparison_id

        with pytest.raises(ComparisonNotFoundError):
            service.get(other, comparison_id)
        with pytest.raises(ComparisonNotFoundError):
            service.list_changes(other, comparison_id)
        assert service.get(owner, comparison_id).status == "COMPLETED"
        assert service.list_changes(owner, comparison_id).changes


class TestNeverInvent:
    def test_model_cannot_reclassify_or_drop_a_real_change(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, P1_LONGER_NOTICE)
        stub = StubComparison(
            answers={
                "30 days": ComparisonOutput(
                    change_type=ChangeType.UNCHANGED,
                    importance=RelativeImportance.LOW,
                    explanation="This looks like the same text to me.",
                )
            }
        )
        service = _comparison_service(fake, llm=stub)

        result = service.compare(
            user_id=user_id, document_a_id=first, document_b_id=second
        )
        changes = service.list_changes(user_id, result.comparison_id).changes

        modified = [change for change in changes if change.type == ChangeType.MODIFIED]
        assert len(modified) == 1
        assert modified[0].explanation == "This looks like the same text to me."
        assert modified[0].importance == RelativeImportance.LOW

    def test_model_abstention_falls_back_without_fabrication(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, P1_LONGER_NOTICE)
        stub = StubComparison(
            answers={
                "30 days": ComparisonOutput(
                    change_type=ChangeType.MODIFIED,
                    importance=RelativeImportance.HIGH,
                    explanation="unused",
                    evidence_state=EvidenceState.INSUFFICIENT_EVIDENCE,
                    abstention_reason="Cannot match the variants reliably.",
                )
            }
        )
        service = _comparison_service(fake, llm=stub)

        result = service.compare(
            user_id=user_id, document_a_id=first, document_b_id=second
        )
        changes = service.list_changes(user_id, result.comparison_id).changes

        modified = next(change for change in changes if change.type == ChangeType.MODIFIED)
        assert modified.explanation == _FALLBACK_EXPLANATION
        assert modified.importance == RelativeImportance.MEDIUM

    def test_llm_failure_and_missing_llm_still_return_real_changes(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, P1_LONGER_NOTICE)

        for llm in (
            StubComparison(error=LLMProviderUnavailableError()),
            None,
        ):
            service = _comparison_service(fake, llm=llm)
            result = service.compare(
                user_id=user_id, document_a_id=first, document_b_id=second
            )
            changes = service.list_changes(user_id, result.comparison_id).changes

            modified = [change for change in changes if change.type == ChangeType.MODIFIED]
            assert len(modified) == 1
            assert modified[0].explanation == _FALLBACK_EXPLANATION
            assert modified[0].importance == RelativeImportance.MEDIUM

    def test_no_added_or_removed_clauses_are_conjured(self, fake):
        user_id = uuid4()
        first = _upload_ready(fake, user_id, P1)
        second = _upload_ready(fake, user_id, P1_COPY)
        service = _comparison_service(fake, llm=None)

        result = service.compare(
            user_id=user_id, document_a_id=first, document_b_id=second
        )
        changes = service.list_changes(user_id, result.comparison_id).changes

        assert all(change.type == ChangeType.UNCHANGED for change in changes)


class TestComparisonEndpoint:
    @pytest.fixture()
    def comparison_env(self, client):
        fake = FakeSupabase()
        holder = {"service": _comparison_service(fake, llm=None)}
        app.dependency_overrides[get_comparison_service] = lambda: holder["service"]
        yield fake, holder
        app.dependency_overrides.clear()

    def _auth(self, jwt_secret: str, user_id: str) -> dict[str, str]:
        payload = {"sub": str(user_id), "exp": time.time() + 3600}
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def test_create_without_auth_is_401(self, client, comparison_env):
        response = client.post(
            "/api/v1/comparisons",
            json={"document_a_id": str(uuid4()), "document_b_id": str(uuid4())},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_create_with_unknown_document_is_404(self, client, comparison_env, jwt_secret):
        fake, _ = comparison_env
        user_id = uuid4()
        token = self._auth(jwt_secret, user_id)
        doc_a = _upload_ready(fake, user_id, P1)

        response = client.post(
            "/api/v1/comparisons",
            headers=token,
            json={"document_a_id": str(doc_a), "document_b_id": str(uuid4())},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
        assert fake.rows_of("comparisons") == []

    def test_create_with_other_users_document_is_404(self, client, comparison_env, jwt_secret):
        fake, _ = comparison_env
        owner = uuid4()
        other = uuid4()
        _upload_ready(fake, owner, P1)
        doc_b = _upload_ready(fake, other, P1_LONGER_NOTICE)
        token = self._auth(jwt_secret, other)

        response = client.post(
            "/api/v1/comparisons",
            headers=token,
            json={"document_a_id": str(uuid4()), "document_b_id": str(doc_b)},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_create_and_read_comparison_round_trip(self, client, comparison_env, jwt_secret):
        fake, holder = comparison_env
        user_id = uuid4()
        token = self._auth(jwt_secret, user_id)
        doc_a = _upload_ready(fake, user_id, P1)
        doc_b = _upload_ready(fake, user_id, P1_LONGER_NOTICE)
        holder["service"] = _comparison_service(
            fake,
            llm=StubComparison(
                answers={
                    "30 days": _grounded(
                        "The notice period increased from 30 to 90 days.",
                        RelativeImportance.HIGH,
                    )
                }
            ),
        )

        created = client.post(
            "/api/v1/comparisons",
            headers=token,
            json={"document_a_id": str(doc_a), "document_b_id": str(doc_b)},
        )

        assert created.status_code == 201
        data = created.json()["data"]
        assert data["status"] == "COMPLETED"
        assert data["summary"] == "1 modified, 0 added, 0 removed, 2 unchanged."
        comparison_id = data["comparison_id"]

        metadata = client.get(f"/api/v1/comparisons/{comparison_id}", headers=token)
        assert metadata.status_code == 200
        assert metadata.json()["data"]["comparison_id"] == comparison_id

        changes = client.get(f"/api/v1/comparisons/{comparison_id}/changes", headers=token)
        assert changes.status_code == 200
        entries = changes.json()["data"]["changes"]
        assert len(entries) == 3
        modified = next(entry for entry in entries if entry["type"] == "MODIFIED")
        assert modified["clause"] == "1.1 Notice"
        assert modified["citation_a"]["document_id"] == str(doc_a)
        assert modified["citation_b"]["document_id"] == str(doc_b)
        assert modified["importance"] == "HIGH"

    def test_unknown_comparison_is_404(self, client, comparison_env, jwt_secret):
        user_id = uuid4()
        token = self._auth(jwt_secret, user_id)

        response = client.get(
            f"/api/v1/comparisons/{uuid4()}", headers=token
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "COMPARISON_NOT_FOUND"