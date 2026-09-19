"""Citation validation for document-grounded Q&A.

The model may only cite chunks that were actually retrieved for the question;
the backend must be able to prove every claim about a citation from its own
data (docs/04_AI/CITATION-Strategy.md §7-§8). The validator here:

* restricts candidates to the retrieved chunk set (anti-fabrication),
* resolves them through the owner-scoped ``document_chunks`` query, so a chunk
  that does not exist, belongs to another document, or belongs to another user
  cannot validate, and
* requires section + page metadata so the citation is resolvable.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.ai.rag.models import RetrievedChunk
from app.repositories.citations import CitationRepository


@dataclass(frozen=True)
class ValidatedCitation:
    """A backend-proven citation that is safe to present in a response."""

    id: str
    chunk_id: UUID
    document_id: UUID
    section_id: UUID | None
    clause_id: UUID | None
    section: str
    clause: str | None
    page_start: int
    page_end: int | None
    source_text: str


class CitationValidator:
    """Resolve and verify model-produced chunk citations."""

    def __init__(self, repository: CitationRepository) -> None:
        self._repository = repository

    def validate(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        cited_ids: Sequence[str],
        retrieved: Sequence[RetrievedChunk],
    ) -> list[ValidatedCitation]:
        """Return the subset of *cited_ids* the backend can prove.

        *cited_ids* are the chunk ids the model cited; *retrieved* is the set of
        chunks actually retrieved for this question. The result keeps retrieval
        order so the first validated citation matches ``[Source 1]``.
        """
        eligible = {str(chunk.chunk_id) for chunk in retrieved}
        candidates = [
            chunk_id
            for chunk_id in dict.fromkeys(str(item) for item in cited_ids)
            if chunk_id in eligible
        ]
        rows = self._repository.owned_chunks(
            user_id=user_id, document_id=document_id, chunk_ids=candidates
        )
        validated = [
            citation for row in rows if (citation := _to_citation(user_id, document_id, row))
        ]
        order = {str(chunk.chunk_id): index for index, chunk in enumerate(retrieved)}
        validated.sort(key=lambda item: order.get(item.id, len(order)))
        return validated


def _to_citation(
    user_id: UUID, document_id: UUID, row: dict[str, Any]
) -> ValidatedCitation | None:
    """Build a citation from a resolved row, or ``None`` when it must be rejected."""
    if str(row.get("user_id")) != str(user_id):
        return None
    if str(row.get("document_id")) != str(document_id):
        return None
    metadata_value = row.get("metadata")
    metadata = metadata_value if isinstance(metadata_value, dict) else {}
    section = str(metadata.get("section") or "").strip()
    page_start = _page_start_or_none(row.get("page_start"))
    if not section or page_start is None:
        return None
    try:
        chunk_id = UUID(str(row["id"]))
    except (KeyError, TypeError, ValueError):
        return None
    return ValidatedCitation(
        id=str(chunk_id),
        chunk_id=chunk_id,
        document_id=UUID(str(document_id)),
        section_id=_uuid_or_none(row.get("section_id")),
        clause_id=_uuid_or_none(row.get("clause_id")),
        section=section,
        clause=_str_or_none(metadata.get("clause")),
        page_start=int(page_start),
        page_end=_int_or_none(row.get("page_end")),
        source_text=str(row.get("content") or ""),
    )


def _page_start_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return None


def _int_or_none(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _str_or_none(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _uuid_or_none(value: object) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except (TypeError, ValueError):
        return None