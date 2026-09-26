"""Document read endpoints: list, summary, attention, clauses (hermetic).

Covers the endpoints the workspace pages depend on:

* ``GET /documents`` — owner-scoped list with pagination and status filter,
  cross-user isolation and the standard success/failure cases.
* ``GET /documents/{id}/summary`` / ``attention`` / ``clauses`` — return the
  persisted, validated analysis rows; an absent/failed analysis yields an
  honest empty payload (never a fabricated one); cross-user/unknown documents
  are 404 with no existence leak.

All persistence and storage are in-memory fakes — no network or real DB.
"""

from __future__ import annotations

import time
from uuid import UUID, uuid4

import jwt
import pytest

from app.api.deps import (
    get_audit_repository,
    get_document_repository,
    get_document_storage,
    get_understanding_service,
)
from app.main import app
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.services.documents import DocumentService
from app.services.storage.supabase import SupabaseDocumentStorage
from tests.fakes import BUCKET, FakeSupabase
from tests.sample_docs import pdf_bytes
from tests.test_analysis import (
    AGREEMENT,
    _document_service,
    _processing_service,
    _stub_fixtures,
    _understanding_service,
)


@pytest.fixture()
def read_env(client) -> FakeSupabase:
    """Wire the app to in-memory repositories, storage and understanding."""
    fake = FakeSupabase()
    understanding = _understanding_service(fake, llm=None)
    app.dependency_overrides[get_document_repository] = lambda: DocumentRepository(
        client=fake
    )
    app.dependency_overrides[get_document_storage] = lambda: SupabaseDocumentStorage(
        client=fake, bucket=BUCKET
    )
    app.dependency_overrides[get_audit_repository] = lambda: AuditLogRepository(
        client=fake
    )
    app.dependency_overrides[get_understanding_service] = lambda: understanding
    yield fake
    app.dependency_overrides.clear()


def _token(jwt_secret: str, user_id: str) -> str:
    payload = {"sub": user_id, "exp": time.time() + 3600}
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def _auth(jwt_secret: str, user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(jwt_secret, user_id)}"}


def _upload(fake: FakeSupabase, user_id: UUID, *, filename: str = "agreement.pdf") -> UUID:
    content = pdf_bytes("\n".join([*AGREEMENT, f"RECORD-{uuid4().hex[:8]}"]))
    outcome = _document_service(fake).upload(
        user_id=user_id,
        filename=filename,
        content=content,
    )
    return outcome.id


def _upload_analyzed(fake: FakeSupabase, *, user_id: UUID | None = None) -> tuple[UUID, UUID]:
    """Upload and fully process a document through READY with analyses."""
    user_id = user_id or uuid4()
    document_id = _upload(fake, user_id)
    row = next(row for row in fake.rows_of("documents") if row["id"] == str(document_id))
    understanding = _understanding_service(fake, llm=_stub_fixtures())
    processing = _processing_service(fake, understanding=understanding)
    result = processing.process(row=row)
    assert result.status == "READY", "document must reach READY for read tests"
    return user_id, document_id


class TestListDocuments:
    def test_unauth_request_is_401(self, client):
        response = client.get("/api/v1/documents")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_empty_list_has_zero_pagination(self, client, read_env, jwt_secret):
        response = client.get("/api/v1/documents", headers=_auth(jwt_secret, str(uuid4())))
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["items"] == []
        assert body["data"]["pagination"] == {"page": 1, "limit": 30, "total": 0, "pages": 0}

    def test_lists_only_the_authenticated_users_documents(self, client, read_env, jwt_secret):
        owner_id = str(uuid4())
        owner_token = _auth(jwt_secret, owner_id)
        _upload(read_env, UUID(owner_id))
        _upload(read_env, UUID(owner_id))
        _upload(read_env, uuid4())

        response = client.get("/api/v1/documents", headers=owner_token)
        assert response.status_code == 200
        body = response.json()
        items = body["data"]["items"]
        assert len(items) == 2
        assert body["data"]["pagination"]["total"] == 2
        assert {"id", "filename", "mime_type", "status"} <= set(items[0])
        assert "storage_key" not in items[0]

    def test_pagination_slices_and_counts(self, client, read_env, jwt_secret):
        user_id = str(uuid4())
        token = _auth(jwt_secret, user_id)
        created = [_upload(read_env, UUID(user_id)) for _ in range(3)]

        first = client.get("/api/v1/documents?page=1&limit=2", headers=token).json()
        second = client.get("/api/v1/documents?page=2&limit=2", headers=token).json()

        first_ids = {item["id"] for item in first["data"]["items"]}
        second_ids = {item["id"] for item in second["data"]["items"]}
        assert first["data"]["pagination"] == {"page": 1, "limit": 2, "total": 3, "pages": 2}
        assert second["data"]["pagination"] == {"page": 2, "limit": 2, "total": 3, "pages": 2}
        assert len(first_ids) == 2
        assert len(second_ids) == 1
        assert first_ids | second_ids == {str(doc_id) for doc_id in created}

    def test_status_filter(self, client, read_env, jwt_secret):
        user_id = str(uuid4())
        token = _auth(jwt_secret, user_id)
        document_id = _upload(read_env, UUID(user_id))
        service = DocumentService(
            repository=DocumentRepository(client=read_env),
        )
        service.mark_failed(user_id=UUID(user_id), document_id=document_id, message="boom")

        response = client.get("/api/v1/documents?status=FAILED", headers=token)
        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]["items"]) == 1
        assert body["data"]["items"][0]["status"] == "FAILED"
        assert body["data"]["pagination"]["total"] == 1

    def test_invalid_limit_is_rejected(self, client, read_env, jwt_secret):
        response = client.get("/api/v1/documents?limit=0", headers=_auth(jwt_secret, str(uuid4())))
        assert response.status_code == 422


class TestSummaryEndpoint:
    def test_unauth_request_is_401(self, client):
        response = client.get(f"/api/v1/documents/{uuid4()}/summary")
        assert response.status_code == 401

    def test_unknown_document_is_404(self, client, read_env, jwt_secret):
        response = client.get(
            f"/api/v1/documents/{uuid4()}/summary", headers=_auth(jwt_secret, str(uuid4()))
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_cross_user_document_is_404_no_leak(self, client, read_env, jwt_secret):
        owner, document_id = _upload_analyzed(read_env)
        intruder = _auth(jwt_secret, str(uuid4()))

        response = client.get(f"/api/v1/documents/{document_id}/summary", headers=intruder)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_summary_returns_persisted_analysis(self, client, read_env, jwt_secret):
        owner, document_id = _upload_analyzed(read_env)
        token = _auth(jwt_secret, str(owner))

        response = client.get(f"/api/v1/documents/{document_id}/summary", headers=token)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["evidence_state"] == "DOCUMENT-GROUNDED"
        assert data["overview"]
        assert data["purpose"]
        assert data["parties"] == ["Acme Corp", "Jane Doe"]
        assert data["obligations"]
        assert data["key_terms"]
        assert {"title", "page_start", "page_end", "source"} <= set(data["evidence"][0])

    def test_summary_is_null_before_analysis(self, client, read_env, jwt_secret):
        owner_id = uuid4()
        document_id = _upload(read_env, owner_id)
        token = _auth(jwt_secret, str(owner_id))

        response = client.get(f"/api/v1/documents/{document_id}/summary", headers=token)

        assert response.status_code == 200
        assert response.json()["data"] is None


class TestAttentionEndpoint:
    def test_attention_returns_items(self, client, read_env, jwt_secret):
        owner, document_id = _upload_analyzed(read_env)
        token = _auth(jwt_secret, str(owner))

        response = client.get(f"/api/v1/documents/{document_id}/attention", headers=token)

        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert len(items) == 2
        assert all(item["attention_level"] in {"LOW", "MEDIUM", "HIGH"} for item in items)
        assert all(item["clause_id"] is not None for item in items)
        assert all(item["recommendation"] for item in items)

    def test_attention_is_empty_before_analysis(self, client, read_env, jwt_secret):
        owner_id = uuid4()
        document_id = _upload(read_env, owner_id)
        token = _auth(jwt_secret, str(owner_id))

        response = client.get(f"/api/v1/documents/{document_id}/attention", headers=token)

        assert response.status_code == 200
        assert response.json()["data"]["items"] == []

    def test_cross_user_document_is_404(self, client, read_env, jwt_secret):
        owner, document_id = _upload_analyzed(read_env)
        intruder = _auth(jwt_secret, str(uuid4()))

        response = client.get(f"/api/v1/documents/{document_id}/attention", headers=intruder)

        assert response.status_code == 404


class TestClausesEndpoint:
    def test_clauses_return_analyzed_clauses(self, client, read_env, jwt_secret):
        owner, document_id = _upload_analyzed(read_env)
        token = _auth(jwt_secret, str(owner))

        response = client.get(f"/api/v1/documents/{document_id}/clauses", headers=token)

        assert response.status_code == 200
        clauses = response.json()["data"]["clauses"]
        assert len(clauses) == 3
        assert all(clause["clause_number"] for clause in clauses)
        assert all(clause["clause_id"] is not None for clause in clauses)
        assert all(clause["explanation"] for clause in clauses)
        assert all(clause["original_text"] for clause in clauses)
        by_number = {clause["clause_number"]: clause for clause in clauses}
        assert by_number["1.1"]["clause_type"] == "Termination"
        assert by_number["3.1"]["clause_type"] == "Confidentiality"

    def test_clauses_empty_before_analysis(self, client, read_env, jwt_secret):
        owner_id = uuid4()
        document_id = _upload(read_env, owner_id)
        token = _auth(jwt_secret, str(owner_id))

        response = client.get(f"/api/v1/documents/{document_id}/clauses", headers=token)

        assert response.status_code == 200
        assert response.json()["data"]["clauses"] == []

    def test_cross_user_document_is_404(self, client, read_env, jwt_secret):
        owner, document_id = _upload_analyzed(read_env)
        intruder = _auth(jwt_secret, str(uuid4()))

        response = client.get(f"/api/v1/documents/{document_id}/clauses", headers=intruder)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


class TestUnderstandingServiceGranularReads:
    def test_granular_reads_match_full_understanding(self, fake_factory):
        fake = fake_factory()
        owner, document_id = _upload_analyzed(fake)
        understanding = _understanding_service(fake, llm=None)

        assert understanding.get_summary(document_id=document_id) is not None
        assert len(understanding.get_attention_items(document_id=document_id)) == 2
        assert len(understanding.get_important_clauses(document_id=document_id)) == 3

    @pytest.fixture()
    def fake_factory(self):
        def make() -> FakeSupabase:
            return FakeSupabase()

        return make