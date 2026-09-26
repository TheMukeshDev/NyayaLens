"""In-memory fakes for hermetic tests (no network, no database).

``FakeSupabase`` mimics the ``supabase.Client`` surface the application uses:
``table(...)`` for PostgREST queries/inserts/updates and ``storage`` for object
storage. State lives in process-local dicts so tests can assert on stored rows
and object layouts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

# Sample file bytes (all valid magic for their declared extensions).
PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x00IEND\xaeB`\x82"
)
DOCX = b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00"
JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"

BUCKET = "legal-documents"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors (0.0 when either is empty/zero)."""
    if len(a) != len(b) or not a:
        return 0.0
    magnitude_a_sq = sum(value * value for value in a)
    magnitude_b_sq = sum(value * value for value in b)
    if magnitude_a_sq == 0.0 or magnitude_b_sq == 0.0:
        return 0.0
    dot = sum(av * bv for av, bv in zip(a, b, strict=True))
    return dot / ((magnitude_a_sq * magnitude_b_sq) ** 0.5)


def _row_key(column: str) -> Any:
    """Sort key that groups missing values last, then orders by the value."""
    return lambda row: (row.get(column) is None, row.get(column))


class FakeResponse:
    """Mimics ``postgrest``'s response object: ``.data`` holds rows."""

    def __init__(self, data: list[dict[str, Any]], count: int | None = None) -> None:
        self.data = data
        self.count = count


class FakeQuery:
    """Minimal PostgREST builder: filters, select, limit, insert, update."""

    def __init__(self, store: dict[str, list[dict[str, Any]]], table: str) -> None:
        self._store = store
        self._table = table
        self._filters: list[tuple[str, str, Any]] = []
        self._orders: list[tuple[str, bool]] = []
        self._select: tuple[str, ...] | None = None
        self._limit: int | None = None
        self._range: tuple[int, int] | None = None
        self._count: str | None = None
        self._inserted: list[dict[str, Any]] | None = None
        self._update: dict[str, Any] | None = None
        self._delete = False

    def select(self, *columns: str, count: str | None = None) -> FakeQuery:
        if columns and list(columns) != ["*"]:
            self._select = tuple(columns)
        if count:
            self._count = count
        return self

    def eq(self, column: str, value: Any) -> FakeQuery:
        self._filters.append(("eq", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> FakeQuery:
        self._filters.append(("in", column, list(values)))
        return self

    def is_(self, column: str, value: str) -> FakeQuery:
        self._filters.append(("is", column, value))
        return self

    def limit(self, amount: int) -> FakeQuery:
        self._limit = amount
        return self

    def range(self, start: int, end: int) -> FakeQuery:
        self._range = (start, end)
        return self

    def order(self, column: str, *, desc: bool = False) -> FakeQuery:
        self._orders.append((column, desc))
        return self

    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> FakeQuery:
        rows = payload if isinstance(payload, list) else [payload]
        inserted: list[dict[str, Any]] = []
        for item in rows:
            row = dict(item)
            row.setdefault("id", str(uuid.uuid4()))
            row.setdefault("created_at", now_iso())
            row.setdefault("updated_at", now_iso())
            self._rows().append(row)
            inserted.append(row)
        self._inserted = inserted
        return self

    def update(self, payload: dict[str, Any]) -> FakeQuery:
        self._update = dict(payload)
        return self

    def delete(self) -> FakeQuery:
        self._delete = True
        return self

    def _rows(self) -> list[dict[str, Any]]:
        return self._store.setdefault(self._table, [])

    def _matches(self, row: dict[str, Any]) -> bool:
        for op, column, value in self._filters:
            actual = row.get(column)
            if op == "eq" and actual != value:
                return False
            if op == "in" and actual not in value:
                return False
            if op == "is":
                if value == "null" and actual is not None:
                    return False
                if value == "not null" and actual is None:
                    return False
        return True

    def execute(self) -> FakeResponse:
        if self._inserted is not None:
            inserted, self._inserted = self._inserted, None
            return FakeResponse([dict(row) for row in inserted])

        if self._delete:
            self._delete = False
            rows = self._rows()
            deleted = [row for row in rows if self._matches(row)]
            for row in deleted:
                rows.remove(row)
            return FakeResponse([dict(row) for row in deleted])

        rows = [row for row in self._rows() if self._matches(row)]
        total = len(rows) if self._count else None
        for column, desc in reversed(self._orders):
            rows.sort(key=_row_key(column), reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]

        if self._update is not None:
            payload, self._update = dict(self._update), None
            updated: list[dict[str, Any]] = []
            for row in rows:
                row.update(payload)
                row["updated_at"] = now_iso()
                updated.append(row)
            return FakeResponse([dict(row) for row in updated])

        if self._select is not None:
            return FakeResponse(
                [{column: row.get(column) for column in self._select} for row in rows],
                count=total,
            )

        return FakeResponse([dict(row) for row in rows], count=total)


# ---------------------------------------------------------------------------
# Storage fakes
# ---------------------------------------------------------------------------


class FakeBucket:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.removed: list[str] = []
        self.fail_next_upload = False
        self.fail_next_download = False
        self.fail_next_sign = False

    def upload(
        self, path: str, content: bytes, file_options: dict[str, Any] | None = None
    ) -> dict[str, str]:
        if self.fail_next_upload:
            self.fail_next_upload = False
            raise RuntimeError("network failure")
        self.objects[path] = content
        return {"Key": path}

    def download(self, path: str) -> bytes:
        if self.fail_next_download:
            self.fail_next_download = False
            raise RuntimeError("network failure")
        if path not in self.objects:
            raise Exception('Object not found: {"statusCode":"404"}')
        return self.objects[path]

    def create_signed_url(self, path: str, expires_in: int) -> dict[str, str]:
        if self.fail_next_sign:
            self.fail_next_sign = False
            raise RuntimeError("network failure")
        return {"signedURL": f"/object/sign/{path}?token=abc"}

    def create_signed_upload_url(self, path: str) -> dict[str, str]:
        """Mimic Supabase's single-use upload ticket (a PUT target for bytes)."""
        if self.fail_next_sign:
            self.fail_next_sign = False
            raise RuntimeError("network failure")
        return {
            "path": path,
            "token": "upload-token",
            "signedUrl": f"/object/upload/sign/{path}?token=upload-token",
        }

    def remove(self, paths: list[str]) -> list[dict[str, str]]:
        self.removed.extend(paths)
        for path in paths:
            self.objects.pop(path, None)
        return [{"name": path} for path in paths]


class FakeStorage:
    def __init__(self) -> None:
        self.buckets: dict[str, FakeBucket] = {}

    def from_(self, bucket: str) -> FakeBucket:
        return self.buckets.setdefault(bucket, FakeBucket())


class FakeRpc:
    """Mimics PostgREST's RPC builder: exposes ``execute()`` returning a response."""

    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    def execute(self) -> FakeResponse:
        return self._response


class FakeSupabase:
    """Rough stand-in for the ``supabase.Client`` used by the application."""

    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}
        self.storage = FakeStorage()
        self.embedding_index: dict[str, int] | None = None

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self._store, name)

    def rows_of(self, table: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self._store.get(table, [])]

    def rpc(self, fn: str, params: dict[str, Any]) -> FakeRpc:
        """Mimic the PostgREST RPC surface the application relies on."""
        if fn == "match_documents":
            return FakeRpc(self._match_documents(params))
        if fn == "ensure_embedding_index":
            self.embedding_index = {"dimension": int(params["dim"])}
            return FakeRpc(FakeResponse([]))
        raise ValueError(f"unknown rpc function: {fn}")

    def _match_documents(self, params: dict[str, Any]) -> FakeResponse:
        """Ownership-scoped cosine search over stored document_chunks."""
        query = list(params["query_embedding"])
        match_count = int(params["match_count"])
        owner = str(params["p_user_id"])
        document_id = params.get("p_document_id")

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in self._store.get("document_chunks", []):
            if str(row.get("user_id")) != owner:
                continue
            if row.get("embedding") is None:
                continue
            if document_id is not None and str(row.get("document_id")) != str(document_id):
                continue
            similarity = _cosine_similarity(query, list(row["embedding"]))
            scored.append((similarity, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        scored = scored[:match_count]
        result: list[dict[str, Any]] = []
        for similarity, row in scored:
            result.append(
                {
                    "id": row["id"],
                    "document_id": row.get("document_id"),
                    "user_id": row.get("user_id"),
                    "section_id": row.get("section_id"),
                    "clause_id": row.get("clause_id"),
                    "chunk_index": row.get("chunk_index"),
                    "content": row.get("content"),
                    "page_start": row.get("page_start"),
                    "page_end": row.get("page_end"),
                    "token_count": row.get("token_count"),
                    "metadata": row.get("metadata") or {},
                    "similarity": similarity,
                    "embedding_model": row.get("embedding_model"),
                    "embedding_dimension": row.get("embedding_dimension"),
                }
            )
        return FakeResponse(result)
