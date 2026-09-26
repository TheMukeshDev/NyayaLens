"""Two-document comparison orchestration.

Implements the comparison pipeline from the product FR-013 and
API-Specification.md §19 (persistence: Database-Schema.md §12):

    verify ownership -> load extracted sections/clauses ->
    match clauses (deterministic) -> classify ADDED/REMOVED/MODIFIED/UNCHANGED
    -> LLM explains each MODIFIED change (schema-validated) -> persist -> response

Honesty rules enforced here:

* The ownership gate covers BOTH documents: a request referencing any document
  the user does not own raises ``DocumentNotFoundError`` before any comparison
  work happens (API-Specification.md §19).
* Change detection is deterministic: a change exists only when clauses provably
  differ — two clauses with different text are MODIFIED, a clause present on
  one side only is ADDED/REMOVED, identical text is UNCHANGED. The model never
  adds, removes or reclassifies a change; it only supplies the explanation and
  importance of an already-detected MODIFIED pair.
* On LLM failure or abstention the service falls back to a fixed explanation
  and MEDIUM importance — it never fabricates a reason. With no LLM configured
  the comparison still completes with deterministic changes (FR-013).
* Citations are backend-resolved from the persisted clauses of the two
  documents; every citation points at a real clause on the correct side and is
  ``None`` when that side has no counterpart clause.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.ai.analysis.service import StructuredLLM
from app.ai.llm.errors import LLMError, LLMOutputValidationError
from app.ai.prompts.models import Prompt
from app.ai.prompts.prompts import build_comparison_prompt
from app.ai.prompts.schemas import ChangeType, ComparisonOutput, EvidenceState, RelativeImportance
from app.core.config import settings
from app.core.errors import ComparisonError, ComparisonNotFoundError, DocumentNotFoundError
from app.core.supabase import get_supabase_client
from app.repositories.comparisons import ComparisonRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.schemas.comparison import (
    ChangeCitationOut,
    ChangeOut,
    ComparisonChangesData,
    ComparisonOut,
)

logger = logging.getLogger("app.ai.comparison")

_MAX_LLM_CHANGES = 20
_MAX_INPUT_CHARACTERS = 4000

_NO_LLM_EXPLANATION = (
    "This clause text differs between the two versions; the AI explanation is "
    "not available right now."
)
_ADDED_EXPLANATION = (
    "This clause is new in the newer version and does not appear in the "
    "earlier version."
)
_REMOVED_EXPLANATION = (
    "This clause existed in the earlier version but is no longer present in "
    "the newer version."
)
_UNCHANGED_EXPLANATION = "This clause is identical in both versions."

_ClauseItem = tuple[dict[str, Any] | None, dict[str, Any]]


@dataclass
class _DetectedChange:
    """One provable change, with the exact clauses on each side."""

    kind: ChangeType
    section: str
    clause: str | None
    before: str | None
    after: str | None
    explanation: str
    importance: RelativeImportance | None
    left: _ClauseItem | None
    right: _ClauseItem | None


class DocumentComparisonService:
    """Compares two owned documents and persists the provable changes."""

    def __init__(
        self,
        *,
        llm: StructuredLLM | None,
        documents: DocumentRepository | None = None,
        processing: ProcessingRepository | None = None,
        comparisons: ComparisonRepository | None = None,
    ) -> None:
        self._llm = llm
        self._documents = documents or DocumentRepository()
        self._processing = processing or ProcessingRepository()
        self._comparisons = comparisons or ComparisonRepository()

    def compare(
        self,
        *,
        user_id: UUID,
        document_a_id: UUID,
        document_b_id: UUID,
    ) -> ComparisonOut:
        """Compare two owned documents and persist the result."""
        if document_a_id == document_b_id:
            raise ComparisonError()
        doc_a = self._documents.get_by_id_and_user(user_id, document_a_id)
        doc_b = self._documents.get_by_id_and_user(user_id, document_b_id)
        if doc_a is None or doc_b is None:
            raise DocumentNotFoundError()

        items_a = self._structure(document_a_id)
        items_b = self._structure(document_b_id)
        changes = self._detect(items_a, items_b)

        comparison = self._comparisons.create(
            user_id=user_id,
            document_a_id=document_a_id,
            document_b_id=document_b_id,
            status="PROCESSING",
        )
        comparison_id = UUID(str(comparison["id"]))
        self._comparisons.replace_changes(
            comparison_id=comparison_id,
            changes=[self._persist_row(change) for change in changes],
        )
        completed_at = _now_iso()
        summary = _summary(changes)
        updated = self._comparisons.mark(
            user_id=user_id,
            comparison_id=comparison_id,
            status="COMPLETED",
            summary=summary,
            completed_at=completed_at,
        )
        if updated is not None:
            comparison = updated
        return self._to_comparison_out(comparison)

    def get(self, user_id: UUID, comparison_id: UUID) -> ComparisonOut:
        """Return an owned comparison's metadata, or raise 404."""
        row = self._comparisons.get(user_id, comparison_id)
        if row is None:
            raise ComparisonNotFoundError()
        return self._to_comparison_out(row)

    def list_changes(self, user_id: UUID, comparison_id: UUID) -> ComparisonChangesData:
        """Return an owned comparison's persisted changes (full citations)."""
        row = self._comparisons.get(user_id, comparison_id)
        if row is None:
            raise ComparisonNotFoundError()
        stored = self._comparisons.list_changes(comparison_id)
        return ComparisonChangesData(
            comparison_id=comparison_id,
            changes=self._project_changes(row, stored),
        )

    # -- pipeline steps ------------------------------------------------------

    def _structure(self, document_id: UUID) -> list[_ClauseItem]:
        """Return ``(section, clause)`` pairs in document order."""
        sections = self._processing.list_sections(document_id)
        section_by_id = {str(row["id"]): row for row in sections}
        items: list[_ClauseItem] = []
        for clause in self._processing.list_clauses(document_id):
            section = None
            clause_section_id = clause.get("section_id")
            if clause_section_id:
                section = section_by_id.get(str(clause_section_id))
            items.append((section, clause))
        return items

    def _detect(
        self,
        items_a: list[_ClauseItem],
        items_b: list[_ClauseItem],
    ) -> list[_DetectedChange]:
        """Detect every provable change between the two clause collections."""
        pairs, matched_a, matched_b = self._match(items_a, items_b)
        changes: list[_DetectedChange] = []
        budget = _MAX_LLM_CHANGES

        for index_a, index_b in pairs:
            section_a, clause_a = items_a[index_a]
            section_b, clause_b = items_b[index_b]
            before = _content(clause_a)
            after = _content(clause_b)
            if _normalize(before) == _normalize(after):
                kind = ChangeType.UNCHANGED
                explanation = _UNCHANGED_EXPLANATION
                importance = None
            else:
                kind = ChangeType.MODIFIED
                if budget > 0:
                    explanation, importance = self._explain_modified(before, after)
                    budget -= 1
                else:
                    explanation, importance = _NO_LLM_EXPLANATION, RelativeImportance.MEDIUM
            section = _section_label(section_b) or _section_label(section_a)
            clause = _clause_label(clause_b) or _clause_label(clause_a)
            changes.append(
                _DetectedChange(
                    kind=kind,
                    section=section,
                    clause=clause,
                    before=before,
                    after=after,
                    explanation=explanation,
                    importance=importance,
                    left=items_a[index_a],
                    right=items_b[index_b],
                )
            )

        for index_a in _remaining(len(items_a), matched_a):
            section_a, clause_a = items_a[index_a]
            changes.append(
                _DetectedChange(
                    kind=ChangeType.REMOVED,
                    section=_section_label(section_a),
                    clause=_clause_label(clause_a),
                    before=_content(clause_a),
                    after=None,
                    explanation=_REMOVED_EXPLANATION,
                    importance=RelativeImportance.MEDIUM,
                    left=items_a[index_a],
                    right=None,
                )
            )

        for index_b in _remaining(len(items_b), matched_b):
            section_b, clause_b = items_b[index_b]
            changes.append(
                _DetectedChange(
                    kind=ChangeType.ADDED,
                    section=_section_label(section_b),
                    clause=_clause_label(clause_b),
                    before=None,
                    after=_content(clause_b),
                    explanation=_ADDED_EXPLANATION,
                    importance=RelativeImportance.MEDIUM,
                    left=None,
                    right=items_b[index_b],
                )
            )

        return changes

    def _match(
        self,
        items_a: list[_ClauseItem],
        items_b: list[_ClauseItem],
    ) -> tuple[list[tuple[int, int]], set[int], set[int]]:
        """Pair clauses by ``(section_number, clause_number)``, then by content.

        Structural identity is the primary key: clauses are matched when their
        section and clause numbers agree, so renumbered or renamed sections
        never collide. Clauses that cannot be identified structurally fall back
        to normalized-content equality, which only ever marks *identical text*
        as matching — never a guess.
        """
        by_key: dict[tuple[str, str], list[int]] = {}
        for index, (section, clause) in enumerate(items_b):
            key = _clause_key(section, clause)
            if key is not None:
                by_key.setdefault(key, []).append(index)

        matched_a: set[int] = set()
        matched_b: set[int] = set()
        pairs: list[tuple[int, int]] = []

        for index_a, (section, clause) in enumerate(items_a):
            key = _clause_key(section, clause)
            if key is None:
                continue
            for index_b in by_key.get(key, []):
                if index_b in matched_b:
                    continue
                pairs.append((index_a, index_b))
                matched_a.add(index_a)
                matched_b.add(index_b)
                break

        by_content: dict[str, list[int]] = {}
        for index_b in _remaining(len(items_b), matched_b):
            content_key = _normalize(_content(items_b[index_b][1]))
            if content_key:
                by_content.setdefault(content_key, []).append(index_b)

        for index_a in _remaining(len(items_a), matched_a):
            content_key = _normalize(_content(items_a[index_a][1]))
            if not content_key:
                continue
            for index_b in by_content.get(content_key, []):
                if index_b in matched_b:
                    continue
                pairs.append((index_a, index_b))
                matched_a.add(index_a)
                matched_b.add(index_b)
                break

        return pairs, matched_a, matched_b

    def _explain_modified(self, before: str, after: str) -> tuple[str, RelativeImportance]:
        """Explain one MODIFIED change, honest even when the model fails."""
        llm = self._llm
        if llm is None:
            return _NO_LLM_EXPLANATION, RelativeImportance.MEDIUM
        prompt = build_comparison_prompt(
            before=before[:_MAX_INPUT_CHARACTERS],
            after=after[:_MAX_INPUT_CHARACTERS],
        )
        output = self._generate(llm, prompt)
        if output is None or output.evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE:
            return _NO_LLM_EXPLANATION, RelativeImportance.MEDIUM
        explanation = output.explanation.strip()
        if not explanation:
            return _NO_LLM_EXPLANATION, RelativeImportance.MEDIUM
        return explanation, output.importance

    def _generate(self, llm: StructuredLLM, prompt: Prompt) -> ComparisonOutput | None:
        """Generate a schema-validated comparison with one retry.

        Any LLM failure returns ``None`` so the caller keeps the deterministic
        classification and a fixed explanation — the service never invents or
        drops a change to smooth over an error.
        """
        try:
            return llm.structured_generate(
                prompt.messages,
                schema=ComparisonOutput,
                max_tokens=prompt.max_tokens,
                temperature=prompt.temperature,
            )
        except LLMOutputValidationError:
            pass
        except LLMError as exc:
            logger.warning("comparison generation failed: %s", _message(exc))
            return None
        try:
            return llm.structured_generate(
                prompt.messages,
                schema=ComparisonOutput,
                max_tokens=prompt.max_tokens,
                temperature=prompt.temperature,
            )
        except LLMError as exc:
            logger.warning("comparison generation failed: %s", _message(exc))
            return None

    # -- persistence + projection -------------------------------------------

    def _persist_row(self, change: _DetectedChange) -> dict[str, Any]:
        return {
            "change_type": change.kind.value,
            "category": change.section[:100],
            "old_text": change.before,
            "new_text": change.after,
            "explanation": change.explanation,
            "importance": change.importance.value if change.importance else None,
            "old_clause_id": _row_id(change.left) if change.left else None,
            "new_clause_id": _row_id(change.right) if change.right else None,
        }

    def _project_changes(
        self,
        comparison: dict[str, Any],
        stored: list[dict[str, Any]],
    ) -> list[ChangeOut]:
        """Rebuild full change responses from stored rows + fresh structures."""
        document_a_id = UUID(str(comparison["document_a_id"]))
        document_b_id = UUID(str(comparison["document_b_id"]))
        names_a = self._names(document_a_id)
        names_b = self._names(document_b_id)

        def citation(
            document_id: UUID,
            clause_id: object,
            names: dict[str, _ClauseItem],
            text: object,
        ) -> ChangeCitationOut | None:
            if not clause_id:
                return None
            item = names.get(str(clause_id))
            if item is None:
                return None
            section, clause = item
            return ChangeCitationOut(
                document_id=document_id,
                section_id=UUID(str(section["id"])) if section else None,
                clause_id=UUID(str(clause["id"])),
                section=_section_label(section),
                clause=_clause_label(clause),
                page_start=_page_of(clause, section, "page_start"),
                page_end=_page_of(clause, section, "page_end"),
                source_text=(
                    str(text) if isinstance(text, str) and text else _content(clause)
                ),
            )

        changes: list[ChangeOut] = []
        for row in stored:
            citation_a = citation(
                document_a_id, row.get("old_clause_id"), names_a, row.get("old_text")
            )
            citation_b = citation(
                document_b_id, row.get("new_clause_id"), names_b, row.get("new_text")
            )
            section = (
                citation_a.section
                if citation_a
                else citation_b.section if citation_b else str(row.get("category") or "Preamble")
            )
            clause = (
                citation_a.clause
                if citation_a
                else citation_b.clause if citation_b else None
            )
            changes.append(
                ChangeOut(
                    type=ChangeType(str(row["change_type"])),
                    section=section,
                    clause=clause,
                    before=_text_of(row.get("old_text")),
                    after=_text_of(row.get("new_text")),
                    explanation=str(row.get("explanation") or ""),
                    importance=_importance_of(row.get("importance")),
                    citation_a=citation_a,
                    citation_b=citation_b,
                )
            )
        return changes

    def _names(self, document_id: UUID) -> dict[str, _ClauseItem]:
        """Index a document's clauses by id for citation resolution."""
        sections = self._processing.list_sections(document_id)
        section_by_id = {str(row["id"]): row for row in sections}
        names: dict[str, _ClauseItem] = {}
        for clause in self._processing.list_clauses(document_id):
            section = None
            clause_section_id = clause.get("section_id")
            if clause_section_id:
                section = section_by_id.get(str(clause_section_id))
            names[str(clause["id"])] = (section, clause)
        return names

    def _to_comparison_out(self, row: dict[str, Any]) -> ComparisonOut:
        return ComparisonOut(
            comparison_id=UUID(str(row["id"])),
            document_a_id=UUID(str(row["document_a_id"])),
            document_b_id=UUID(str(row["document_b_id"])),
            status=str(row["status"]),
            summary=str(row["summary"]) if row.get("summary") else None,
            created_at=str(row["created_at"]),
            completed_at=str(row["completed_at"]) if row.get("completed_at") else None,
        )


# -- assembly -----------------------------------------------------------------


def build_comparison_service(*, client: Any | None = None) -> DocumentComparisonService:
    """Assemble the comparison service from settings + the Supabase client."""
    client = client or get_supabase_client()
    return DocumentComparisonService(
        llm=_build_llm(),
        documents=DocumentRepository(client=client),
        processing=ProcessingRepository(client=client),
        comparisons=ComparisonRepository(client=client),
    )


def _build_llm() -> StructuredLLM | None:
    """Build the configured LLM provider, or ``None`` when not configured."""
    if not settings.llm_enabled or not settings.llm_model or not settings.llm_api_url:
        return None
    from app.ai.llm.provider import build_llm_provider

    return build_llm_provider(
        provider=settings.llm_provider,
        model_name=settings.llm_model,
        api_url=settings.llm_api_url,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_request_timeout_seconds,
        max_attempts=settings.llm_max_attempts,
        retry_base_delay_seconds=settings.llm_retry_base_delay_seconds,
        retry_max_delay_seconds=settings.llm_retry_max_delay_seconds,
        retry_jitter_seconds=settings.llm_retry_jitter_seconds,
        requests_per_minute=settings.llm_max_requests_per_minute,
    )


# -- helpers ------------------------------------------------------------------


def _clause_key(section: dict[str, Any] | None, clause: dict[str, Any]) -> tuple[str, str] | None:
    section_number = _value_or_none(section.get("section_number")) if section else None
    clause_number = _value_or_none(clause.get("clause_number"))
    if section_number and clause_number:
        return (section_number, clause_number)
    return None


def _content(clause: dict[str, Any]) -> str:
    value = clause.get("content")
    return str(value) if isinstance(value, str) else ""


def _row_id(item: _ClauseItem) -> str | None:
    clause = item[1]
    value = clause.get("id")
    return str(value) if value else None


def _section_label(section: dict[str, Any] | None) -> str:
    if section is None:
        return "Preamble"
    number = _value_or_none(section.get("section_number"))
    title = _value_or_none(section.get("title"))
    labeled = f"{number} {title}".strip() if number else None
    return labeled or title or number or "Preamble"


def _clause_label(clause: dict[str, Any]) -> str | None:
    number = _value_or_none(clause.get("clause_number"))
    title = _value_or_none(clause.get("title"))
    labeled = f"{number} {title}".strip() if number else None
    return labeled or title or number


def _page_of(clause: dict[str, Any], section: dict[str, Any] | None, column: str) -> int | None:
    value = clause.get(column)
    if isinstance(value, int):
        return value
    if section is not None:
        value = section.get(column)
        if isinstance(value, int):
            return value
    return None


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _remaining(total: int, matched: set[int]) -> list[int]:
    return [index for index in range(total) if index not in matched]


def _value_or_none(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _text_of(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _importance_of(value: object) -> RelativeImportance | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return RelativeImportance(value)
    except ValueError:
        return None


def _summary(changes: list[_DetectedChange]) -> str:
    counts = Counter(change.kind for change in changes)
    return (
        f"{counts[ChangeType.MODIFIED]} modified, {counts[ChangeType.ADDED]} added, "
        f"{counts[ChangeType.REMOVED]} removed, {counts[ChangeType.UNCHANGED]} unchanged."
    )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _message(exc: Exception) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text[:500]