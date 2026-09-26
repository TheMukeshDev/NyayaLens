"""Secure document storage tests (hermetic).

Covers:

* file type validation (extension + magic bytes)
* file size validation
* filename sanitization
* private bucket object paths (per-user namespacing)
* short-lived signed URLs via the storage abstraction
* ``SupabaseDocumentStorage`` behavior using a fake Supabase client, so no
  network or real project is required
* error hygiene: storage failures surface as generic 503s, never raw details
"""

import uuid

import pytest

from app.core.errors import DocumentNotFoundError, ErrorCodes, StorageError
from app.services.file_validation import sanitize_filename, validate_uploaded_file
from app.services.storage.supabase import SupabaseDocumentStorage
from tests.fakes import BUCKET, DOCX, PDF, PNG, FakeSupabase


def _make(storage=None):
    client = storage or FakeSupabase()
    return SupabaseDocumentStorage(client=client, bucket=BUCKET)


# ---------------------------------------------------------------------------
# filename sanitization
# ---------------------------------------------------------------------------


class TestFilenameSanitization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (None, "document"),
            ("", "document"),
            ("   ", "document"),
            ("agreement.pdf", "agreement.pdf"),
            ("AGREEMENT.PDF", "AGREEMENT.PDF"),
            (r"C:\Users\mukes\Documents\agreement.pdf", "agreement.pdf"),
            ("/etc/passwd.pdf", "passwd.pdf"),
            ("../../lib/x.pdf", "x.pdf"),
            ('a"b.pdf', "ab.pdf"),
            ("a>b.pdf", "ab.pdf"),
            ("CON", "document-CON"),
            ("NUL.pdf", "document-NUL.pdf"),
            (".hidden.pdf", "hidden.pdf"),
        ],
    )
    def test_sanitizes(self, raw, expected):
        assert sanitize_filename(raw) == expected

    def test_removes_control_characters(self):
        assert sanitize_filename("a\nb\tc.pdf") == "abc.pdf"

    def test_dot_entries_become_document(self):
        assert sanitize_filename(".") == "document"
        assert sanitize_filename("..") == "document"

    def test_limits_length_while_preserving_extension(self):
        long_stem = "a" * 300
        name = sanitize_filename(f"{long_stem}.pdf")
        assert len(name) == 200
        assert name.endswith(".pdf")

    def test_only_path_separators_become_document(self):
        assert sanitize_filename("///\\\\") == "document"


# ---------------------------------------------------------------------------
# file type / size validation
# ---------------------------------------------------------------------------


class TestFileValidation:
    @pytest.mark.parametrize(
        "filename,content",
        [
            ("agreement.pdf", PDF),
            ("cv.docx", DOCX),
            ("scan.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"),
            ("photo.png", PNG),
        ],
    )
    def test_accepts_supported_types(self, filename, content):
        result = validate_uploaded_file(filename, content)
        assert result.valid
        assert result.mime_type

    def test_rejects_unknown_extension(self):
        result = validate_uploaded_file("virus.exe", b"MZ\x90\x00")
        assert not result.valid
        assert result.error_code == ErrorCodes.UNSUPPORTED_FILE_TYPE
        assert result.status_code == 415

    def test_rejects_no_extension(self):
        result = validate_uploaded_file("README", PDF)
        assert not result.valid
        assert result.error_code == ErrorCodes.UNSUPPORTED_FILE_TYPE

    def test_rejects_content_mismatching_extension(self):
        result = validate_uploaded_file("fake.pdf", PNG)
        assert not result.valid
        assert result.error_code == ErrorCodes.INVALID_FILE
        assert result.status_code == 400

    def test_rejects_empty_file(self):
        result = validate_uploaded_file("empty.pdf", b"")
        assert not result.valid
        assert result.error_code == ErrorCodes.INVALID_FILE

    def test_rejects_missing_filename(self):
        result = validate_uploaded_file("", PDF)
        assert not result.valid
        assert result.status_code == 400

    def test_rejects_oversized_file(self, monkeypatch):
        monkeypatch.setattr("app.services.file_validation.settings.max_upload_size_mb", 1)
        result = validate_uploaded_file("big.pdf", PDF + b"x" * (2 * 1024 * 1024))
        assert not result.valid
        assert result.error_code == ErrorCodes.FILE_TOO_LARGE
        assert result.status_code == 413


# ---------------------------------------------------------------------------
# SupabaseDocumentStorage behavior
# ---------------------------------------------------------------------------


class TestSupabaseDocumentStorage:
    def test_store_original_namespaces_key_per_user(self):
        user_id = uuid.uuid4()
        document_id = uuid.uuid4()
        storage = _make()

        key = storage.store_original(
            user_id=user_id,
            document_id=document_id,
            filename="agreement.pdf",
            content=PDF,
            content_type="application/pdf",
        )

        expected = f"users/{user_id}/documents/{document_id}/original"
        assert key == expected
        assert storage._bucket_api().objects == {expected: PDF}

    def test_store_original_passes_content_type_option(self):
        storage = _make()
        bucket = storage._bucket_api()
        captured = {}
        bucket.upload = lambda path, content, file_options=None: captured.update(
            {"path": path, "options": file_options}
        )

        storage.store_original(
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            filename="a.pdf",
            content=PDF,
            content_type="application/pdf",
        )

        assert captured["options"]["content-type"] == "application/pdf"
        assert captured["options"]["upsert"] == "true"

    def test_original_key_is_derived_not_supplied(self):
        user_id = uuid.uuid4()
        document_id = uuid.uuid4()
        storage = _make()
        assert storage.original_key(user_id=user_id, document_id=document_id) == (
            f"users/{user_id}/documents/{document_id}/original"
        )

    def test_create_signed_upload_url_returns_single_object_ticket(self):
        storage = _make()
        key = storage.original_key(user_id=uuid.uuid4(), document_id=uuid.uuid4())

        ticket = storage.create_signed_upload_url(key)

        assert ticket.path == key
        assert ticket.token == "upload-token"
        assert ticket.signed_url == f"/object/upload/sign/{key}?token=upload-token"
        # Signing must not create or read an object.
        assert storage._bucket_api().objects == {}

    def test_create_signed_upload_url_failure_raises_generic_storage_error(self):
        storage = _make()
        storage._bucket_api().fail_next_sign = True

        with pytest.raises(StorageError):
            storage.create_signed_upload_url("users/u/documents/d/original")

    def test_read_returns_object_bytes(self):
        storage = _make()
        key = storage.store_original(
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            filename="a.pdf",
            content=PDF,
            content_type="application/pdf",
        )
        assert storage.read(key) == PDF

    def test_read_missing_raises_not_found(self):
        storage = _make()
        with pytest.raises(DocumentNotFoundError):
            storage.read("users/u/documents/d/original")

    def test_create_signed_url_parses_url(self):
        storage = _make()
        key = "users/u/documents/d/original"
        url = storage.create_signed_url(key, expires_in_seconds=900)
        assert f"/object/sign/{key}?token=abc" in url

    def test_delete_removes_object(self):
        storage = _make()
        key = storage.store_original(
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            filename="a.pdf",
            content=PDF,
            content_type="application/pdf",
        )
        storage.delete(key)
        assert storage._bucket_api().objects == {}
        assert key in storage._bucket_api().removed

    def test_delete_on_missing_object_is_idempotent(self):
        storage = _make()
        with pytest.raises(DocumentNotFoundError):
            storage.read("users/u/documents/d/original")
        storage.delete("users/u/documents/d/original")

    @pytest.mark.parametrize(
        "fail,op",
        [
            (
                "upload",
                lambda s, k: s.store_original(
                    user_id=uuid.uuid4(),
                    document_id=uuid.uuid4(),
                    filename="a.pdf",
                    content=PDF,
                    content_type="application/pdf",
                ),
            ),
            ("download", lambda s, k: s.read(k)),
            ("sign", lambda s, k: s.create_signed_url(k, expires_in_seconds=900)),
        ],
        ids=["upload", "download", "sign"],
    )
    def test_backend_failure_raises_generic_storage_error(self, fail, op):
        storage = _make()
        bucket = storage._bucket_api()
        key = storage.store_original(
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            filename="a.pdf",
            content=PDF,
            content_type="application/pdf",
        )
        if fail == "upload":
            bucket.fail_next_upload = True
            with pytest.raises(StorageError):
                op(storage, key)
        elif fail == "download":
            bucket.fail_next_download = True
            with pytest.raises(StorageError):
                op(storage, key)
        else:
            bucket.fail_next_sign = True
            with pytest.raises(StorageError):
                op(storage, key)

    def test_error_message_never_leaks_backend_details(self):
        storage = _make()
        bucket = storage._bucket_api()
        bucket.fail_next_download = True
        key = storage.store_original(
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            filename="a.pdf",
            content=PDF,
            content_type="application/pdf",
        )
        try:
            storage.read(key)
        except StorageError as exc:
            assert "network" not in str(exc).lower()
            assert "legal-documents" not in str(exc)
        else:
            pytest.fail("expected StorageError")
