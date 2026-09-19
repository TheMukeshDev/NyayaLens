"""Document upload workflow tests (hermetic).

Covers

* authenticated upload: validation, private storage, DB record, status
* rejection of unsupported/mismatched file types and oversized files
* unauthenticated uploads
* cross-user access (no existence leak)
* duplicate (identical-content) uploads
* retry-safe processing states (FAILED -> UPLOADED)

All persistence and storage are in-memory fakes — no network or real DB.
"""

import time
from uuid import UUID, uuid4

import jwt
import pytest

from app.api.deps import get_audit_repository, get_document_repository, get_document_storage
from app.core.errors import DocumentNotFoundError
from app.main import app
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.services.documents import DocumentService
from app.services.storage.supabase import SupabaseDocumentStorage
from tests.fakes import BUCKET, JPG, PDF, PNG, FakeSupabase


@pytest.fixture()
def doc_env(client) -> FakeSupabase:
    """Wire the app to in-memory document repositories and storage."""
    fake = FakeSupabase()
    app.dependency_overrides[get_document_repository] = lambda: DocumentRepository(client=fake)
    app.dependency_overrides[get_document_storage] = lambda: SupabaseDocumentStorage(
        client=fake, bucket=BUCKET
    )
    app.dependency_overrides[get_audit_repository] = lambda: AuditLogRepository(client=fake)
    yield fake
    app.dependency_overrides.clear()


def _token(jwt_secret: str, user_id: str) -> str:
    payload = {"sub": user_id, "exp": time.time() + 3600}
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def _auth(jwt_secret: str, user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(jwt_secret, user_id)}"}


def _upload(client, token, *, filename="agreement.pdf", content=PDF):
    return client.post(
        "/api/v1/documents",
        headers=token,
        files={"file": (filename, content, "application/octet-stream")},
    )


class TestUpload:
    def test_valid_upload_returns_document_record(self, doc_env, client, jwt_secret):
        user_id = str(uuid4())
        response = _upload(client, _auth(jwt_secret, user_id), filename="agreement.pdf")

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        document = body["data"]["document"]
        document_id = document["id"]
        UUID(document_id)
        assert document["filename"] == "agreement.pdf"
        assert document["mime_type"] == "application/pdf"
        assert document["file_size_bytes"] == len(PDF)
        assert document["status"] == "UPLOADED"
        assert document["processing_error"] is None
        assert "storage_key" not in document

        rows = doc_env.rows_of("documents")
        assert len(rows) == 1
        assert rows[0]["user_id"] == user_id
        assert rows[0]["storage_key"] == f"users/{user_id}/documents/{document_id}/original"

        objects = list(doc_env.storage.from_(BUCKET).objects.keys())
        assert objects == [f"users/{user_id}/documents/{document_id}/original"]

        audits = doc_env.rows_of("audit_logs")
        assert len(audits) == 1
        assert audits[0]["action"] == "DOCUMENT_UPLOAD"
        assert audits[0]["resource_id"] == document_id
        assert audits[0]["user_id"] == user_id

    @pytest.mark.parametrize(
        "filename,content,expected_status,expected_code",
        [
            ("virus.exe", b"MZ\x90\x00", 415, "UNSUPPORTED_FILE_TYPE"),
            ("fake.pdf", PNG, 400, "INVALID_FILE"),
            (".exe", PDF, 415, "UNSUPPORTED_FILE_TYPE"),
            ("doc.docx", PNG, 400, "INVALID_FILE"),
            ("photo.png", JPG, 400, "INVALID_FILE"),
        ],
        ids=[
            "unknown-extension",
            "pdf-content-mismatch",
            "no-extension",
            "docx-content-mismatch",
            "png-content-mismatch",
        ],
    )
    def test_rejects_unusable_file_types(
        self, doc_env, client, jwt_secret, filename, content, expected_status, expected_code
    ):
        user_id = str(uuid4())
        response = _upload(client, _auth(jwt_secret, user_id), filename=filename, content=content)

        assert response.status_code == expected_status
        assert response.json()["error"]["code"] == expected_code
        assert doc_env.rows_of("documents") == []
        assert doc_env.storage.from_(BUCKET).objects == {}

    def test_rejects_oversized_file(self, doc_env, client, jwt_secret, monkeypatch):
        monkeypatch.setattr("app.services.file_validation.settings.max_upload_size_mb", 1)
        user_id = str(uuid4())
        big = PDF + b"x" * (2 * 1024 * 1024)

        response = _upload(client, _auth(jwt_secret, user_id), content=big)

        assert response.status_code == 413
        assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
        assert doc_env.rows_of("documents") == []
        assert doc_env.storage.from_(BUCKET).objects == {}

    def test_unauthenticated_upload_returns_401(self, client):
        response = client.post(
            "/api/v1/documents", files={"file": ("a.pdf", PDF, "application/pdf")}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"


class TestDuplicateUpload:
    def test_identical_content_returns_409_and_no_second_object(self, doc_env, client, jwt_secret):
        user_id = str(uuid4())
        token = _auth(jwt_secret, user_id)

        first = _upload(client, token)
        assert first.status_code == 201
        first_id = first.json()["data"]["document"]["id"]

        second = _upload(client, token, filename="renamed.pdf")
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "DUPLICATE_DOCUMENT"

        rows = doc_env.rows_of("documents")
        assert len(rows) == 1
        assert rows[0]["id"] == first_id
        assert len(doc_env.storage.from_(BUCKET).objects) == 1

    def test_same_content_by_different_users_is_allowed(self, doc_env, client, jwt_secret):
        token_a = _auth(jwt_secret, str(uuid4()))
        token_b = _auth(jwt_secret, str(uuid4()))

        assert _upload(client, token_a).status_code == 201
        assert _upload(client, token_b).status_code == 201
        assert len(doc_env.rows_of("documents")) == 2


class TestAccessControl:
    def test_cross_user_read_is_404_no_existence_leak(self, doc_env, client, jwt_secret):
        owner_id = str(uuid4())
        owner_token = _auth(jwt_secret, owner_id)
        intruder_token = _auth(jwt_secret, str(uuid4()))

        created = _upload(client, owner_token)
        document_id = created.json()["data"]["document"]["id"]

        response = client.get(f"/api/v1/documents/{document_id}", headers=intruder_token)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

        status_response = client.get(
            f"/api/v1/documents/{document_id}/status", headers=intruder_token
        )
        assert status_response.status_code == 404

    def test_owner_can_read_metadata_and_status(self, doc_env, client, jwt_secret):
        token = _auth(jwt_secret, str(uuid4()))
        created = _upload(client, token)
        document_id = created.json()["data"]["document"]["id"]

        document = client.get(f"/api/v1/documents/{document_id}", headers=token)
        assert document.status_code == 200
        assert document.json()["data"]["id"] == document_id

        status = client.get(f"/api/v1/documents/{document_id}/status", headers=token)
        assert status.status_code == 200
        assert status.json()["data"]["status"] == "UPLOADED"
        assert status.json()["data"]["message"]


class TestProcessingStates:
    def test_failed_then_retry_resets_to_uploaded(self, doc_env, client, jwt_secret):
        user_id = str(uuid4())
        token = _auth(jwt_secret, user_id)
        created = _upload(client, token)
        document_id = UUID(created.json()["data"]["document"]["id"])

        service = DocumentService(
            repository=DocumentRepository(client=doc_env),
            storage=SupabaseDocumentStorage(client=doc_env, bucket=BUCKET),
            audit=AuditLogRepository(client=doc_env),
        )
        failed = service.mark_failed(
            user_id=UUID(user_id), document_id=document_id, message="ocr failed"
        )
        assert failed.status == "FAILED"
        assert failed.processing_error == "ocr failed"

        status = client.get(f"/api/v1/documents/{document_id}/status", headers=token)
        assert status.json()["data"]["status"] == "FAILED"
        assert status.json()["data"]["message"] == "ocr failed"

        retried = client.post(f"/api/v1/documents/{document_id}/retry", headers=token)
        assert retried.status_code == 200
        assert retried.json()["data"]["status"] == "UPLOADED"
        assert retried.json()["data"]["processing_error"] is None

        status_after = client.get(f"/api/v1/documents/{document_id}/status", headers=token)
        assert status_after.json()["data"]["status"] == "UPLOADED"

    def test_retry_on_non_failed_document_returns_409(self, doc_env, client, jwt_secret):
        token = _auth(jwt_secret, str(uuid4()))
        created = _upload(client, token)
        document_id = created.json()["data"]["document"]["id"]

        response = client.post(f"/api/v1/documents/{document_id}/retry", headers=token)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"
        assert doc_env.rows_of("documents")[0]["processing_status"] == "UPLOADED"

    def test_mark_failed_on_missing_document_returns_404(self, doc_env, jwt_secret):
        user_id = uuid4()
        document_id = uuid4()
        service = DocumentService(
            repository=DocumentRepository(client=doc_env),
            storage=SupabaseDocumentStorage(client=doc_env, bucket=BUCKET),
            audit=AuditLogRepository(client=doc_env),
        )

        with pytest.raises(DocumentNotFoundError):
            service.mark_failed(user_id=user_id, document_id=document_id, message="boom")


class TestStatusFailureInvariant:
    def test_retry_clears_processing_error(self, doc_env, client, jwt_secret):
        user_id = str(uuid4())
        token = _auth(jwt_secret, user_id)
        created = _upload(client, token)
        document_id = UUID(created.json()["data"]["document"]["id"])

        service = DocumentService(repository=DocumentRepository(client=doc_env))
        service.mark_failed(user_id=UUID(user_id), document_id=document_id, message="x")

        retried = client.post(f"/api/v1/documents/{document_id}/retry", headers=token)
        row = doc_env.rows_of("documents")[0]
        assert retried.status_code == 200
        assert row["processing_error"] is None
        assert row["processing_status"] == "UPLOADED"
