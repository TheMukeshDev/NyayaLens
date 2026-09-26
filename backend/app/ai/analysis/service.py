"""Document understanding service (docs/04_AI/AI-Architecture.md §4-§9, FR-003).

Run three structured, schema-validated analyses against the deterministic
extraction output and persist ONLY validated results (Prompt-Strategy.md §18):

* ``SUMMARY`` — plain-language overview, parties, key terms, obligations and
  conditions (AI-Architecture.md §7).
* ``CLAUSE_EXTRACTION`` — clause classification + plain-language explanation.
* ``ATTENTION_ANALYSIS`` — areas requiring attention, normalized into
  ``attention_items`` rows, each linked to its matching clause when possible.

Honesty guarantees:

* The provider never fabricates (AI-Architecture.md §15): an unconfigured,
  unreachable, rate-limited, timed-out or schema-invalid provider records a
  ``FAILED`` analysis row with a controlled message. The document still
  becomes ``READY`` — the deterministic extraction results remain available.
* Important dates and monetary terms come from deterministic extraction with
  page references, not from the model.
* There is no legal score, no "safe"/"illegal" verdict and no outcome promise
  (Responsible-AI.md §6-§7). Every important output retains source references.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.ai.embeddings.repository import VectorRepository
from app.ai.llm.errors import LLMError
from app.ai.llm.models import ChatMessage
from app.ai.prompts.models import Prompt
from app.ai.prompts.prompts import (
    build_attention_prompt,
    build_clause_extraction_prompt,
    build_summary_prompt,
)
from app.ai.prompts.schemas import (
    AttentionItem,
    AttentionOutput,
    ClauseExtractionOutput,
    ClauseOutcome,
    EvidenceState,
    SummaryOutput,
)
from app.document_processing.models import ExtractedClause, ExtractedSection
from app.repositories.analysis import AnalysisRepository
from app.repositories.processing import ProcessingRepository
from app.schemas.analysis import (
    AnalysisType,
    AttentionItemOut,
    DocumentUnderstandingOut,
    EntityReference,
    EvidenceReference,
    ImportantClause,
    UnderstandingSummary,
)

logger = logging.getLogger("app.ai.analysis")

_MAX_INPUT_CHARACTERS = 24_000
_MAX_CLAUSES = 60
_MESSAGE_LIMIT = 500
_TITLE_LIMIT = 255
_NOT_CONFIGURED = "AI analysis is not configured for this environment."

_ANALYSIS_TYPES = (
    AnalysisType.SUMMARY,
    AnalysisType.CLAUSE_EXTRACTION,
    AnalysisType.ATTENTION_ANALYSIS,
)

_T = TypeVar("_T", bound=BaseModel)


class StructuredLLM(Protocol):
    """The narrow structured-generation interface the service relies on."""

    @property
    def model_name(self) -> str:
        ...

    def structured_generate[U: BaseModel](
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[U],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> U:
        ...


class DocumentUnderstandingService:
    """Runs and reads back the AI document-understanding feature set."""

    def __init__(
        self,
        *,
        llm: StructuredLLM | None,
        analyses: AnalysisRepository,
        processing: ProcessingRepository,
        vectors: VectorRepository,
    ) -> None:
        self._llm = llm
        self._analyses = analyses
        self._processing = processing
        self._vectors = vectors

    # -- write path (called after deterministic persistence) --------------

    def analyze(
        self,
        *,
        document_id: UUID,
        clauses: Sequence[ExtractedClause],
        sections: Sequence[ExtractedSection],
    ) -> None:
        """Run and persist all three analyses for one document (idempotent).

        Never raises for LLM failures: each failing analysis is recorded as a
        ``FAILED`` row with a controlled message, so the caller can still mark
        the document ``READY``.
        """
        self._analyses.delete_for_document(document_id)
        llm = self._llm
        if llm is None:
            for analysis_type in _ANALYSIS_TYPES:
                self._fail(document_id, analysis_type, _NOT_CONFIGURED)
            return
        content = _document_text(sections, clauses)
        self._run_summary(
            llm, document_id=document_id, content=content, sections=sections, clauses=clauses
        )
        self._run_clause_extraction(llm, document_id=document_id, clauses=clauses)
        self._run_attention(llm, document_id=document_id, content=content, clauses=clauses)

    def _run_summary(
        self,
        llm: StructuredLLM,
        *,
        document_id: UUID,
        content: str,
        sections: Sequence[ExtractedSection],
        clauses: Sequence[ExtractedClause],
    ) -> None:
        prompt = build_summary_prompt(content=_truncate(content), document_type=None)

        def evidence_for(_out: SummaryOutput) -> list[EvidenceReference]:
            return [_whole_document_ref(sections, clauses)]

        self._run(
            llm,
            document_id=document_id,
            analysis_type=AnalysisType.SUMMARY.value,
            prompt=prompt,
            schema=SummaryOutput,
            evidence_for=evidence_for,
        )

    def _run_clause_extraction(
        self,
        llm: StructuredLLM,
        *,
        document_id: UUID,
        clauses: Sequence[ExtractedClause],
    ) -> None:
        clause_texts = [clause.content for clause in clauses][:_MAX_CLAUSES]
        prompt = build_clause_extraction_prompt(clauses=clause_texts)

        def evidence_for(out: ClauseExtractionOutput) -> list[EvidenceReference]:
            return [_clause_ref(item, clauses) for item in out.clauses]

        self._run(
            llm,
            document_id=document_id,
            analysis_type=AnalysisType.CLAUSE_EXTRACTION.value,
            prompt=prompt,
            schema=ClauseExtractionOutput,
            evidence_for=evidence_for,
        )

    def _run_attention(
        self,
        llm: StructuredLLM,
        *,
        document_id: UUID,
        content: str,
        clauses: Sequence[ExtractedClause],
    ) -> None:
        prompt = build_attention_prompt(content=_truncate(content), document_type=None)

        def evidence_for(out: AttentionOutput) -> list[EvidenceReference]:
            return [
                _support_clause_ref(item.source_support, clauses)
                for item in out.attention_items
            ]

        completed = self._run(
            llm,
            document_id=document_id,
            analysis_type=AnalysisType.ATTENTION_ANALYSIS.value,
            prompt=prompt,
            schema=AttentionOutput,
            evidence_for=evidence_for,
        )
        if completed is None:
            return
        analysis_row, output = completed
        analysis_id = UUID(str(analysis_row["id"]))
        items = [_attention_item_row(item, clauses) for item in output.attention_items]
        self._analyses.replace_attention_items(
            document_id=document_id, analysis_id=analysis_id, items=items
        )

    def _run(
        self,
        llm: StructuredLLM,
        *,
        document_id: UUID,
        analysis_type: str,
        prompt: Prompt,
        schema: type[_T],
        evidence_for: Callable[[_T], list[EvidenceReference]],
    ) -> tuple[dict[str, Any], _T] | None:
        """Run one generation; record COMPLETED or FAILED, never fabricate."""
        try:
            output = llm.structured_generate(
                prompt.messages,
                schema=schema,
                max_tokens=prompt.max_tokens,
                temperature=prompt.temperature,
            )
        except LLMError as exc:
            logger.warning("AI analysis %s failed: %s", analysis_type, _message(exc))
            self._fail(document_id, AnalysisType(analysis_type), _message(exc))
            return None
        row = self._complete(
            document_id,
            analysis_type,
            prompt,
            output,
            [ref.model_dump(mode="json") for ref in evidence_for(output)],
        )
        return row, output

    def _complete(
        self,
        document_id: UUID,
        analysis_type: str,
        prompt: Prompt,
        output: BaseModel,
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Persist a validated output payload (schema-validated JSON only)."""
        state = getattr(output, "evidence_state", EvidenceState.DOCUMENT_GROUNDED)
        if not isinstance(state, EvidenceState):
            state = EvidenceState.DOCUMENT_GROUNDED
        result: dict[str, Any] = {
            "evidence_state": state.value,
            "output": output.model_dump(mode="json"),
            "evidence": evidence,
        }
        return self._analyses.create(
            document_id=document_id,
            analysis_type=analysis_type,
            model_name=self._llm.model_name if self._llm else None,
            prompt_version=prompt.version_id,
            status="COMPLETED",
            result=result,
            error_message=None,
            completed_at=_now_iso(),
        )

    def _fail(self, document_id: UUID, analysis_type: AnalysisType, message: str) -> None:
        self._analyses.create(
            document_id=document_id,
            analysis_type=analysis_type.value,
            model_name=None,
            prompt_version=None,
            status="FAILED",
            result=None,
            error_message=message[: _MESSAGE_LIMIT],
            completed_at=_now_iso(),
        )

    # -- read path (assembles the persisted feature set) -------------------

    def get_summary(self, *, document_id: UUID) -> UnderstandingSummary | None:
        """Return the persisted plain-language summary, or ``None``."""
        return _summary_of(
            self._analyses.latest(document_id, AnalysisType.SUMMARY.value)
        )

    def get_important_clauses(
        self, *, document_id: UUID
    ) -> list[ImportantClause]:
        """Return the persisted clause analysis with evidence references."""
        clause_row = self._analyses.latest(
            document_id, AnalysisType.CLAUSE_EXTRACTION.value
        )
        section_rows = self._processing.list_sections(document_id)
        clause_rows = self._processing.list_clauses(document_id)
        return _important_clauses_of(clause_row, section_rows, clause_rows)

    def get_attention_items(self, *, document_id: UUID) -> list[AttentionItemOut]:
        """Return the persisted areas requiring attention."""
        attention_row = self._analyses.latest(
            document_id, AnalysisType.ATTENTION_ANALYSIS.value
        )
        return self._attention_items(attention_row, document_id)

    def get_understanding(self, *, document_id: UUID) -> DocumentUnderstandingOut:
        """Assemble the full understanding feature set from persisted rows.

        Favored dates/monetary values come from deterministic extraction; clause
        analysis, summary and attention come from validated AI output.
        """
        summary_row = self._analyses.latest(document_id, AnalysisType.SUMMARY.value)
        clause_row = self._analyses.latest(
            document_id, AnalysisType.CLAUSE_EXTRACTION.value
        )
        attention_row = self._analyses.latest(
            document_id, AnalysisType.ATTENTION_ANALYSIS.value
        )
        section_rows = self._processing.list_sections(document_id)
        clause_rows = self._processing.list_clauses(document_id)
        chunk_rows = self._vectors.chunk_entities(document_id)

        summary = _summary_of(summary_row)
        clauses = _important_clauses_of(clause_row, section_rows, clause_rows)

        attention_items = self._attention_items(attention_row, document_id)
        rows = [
            row
            for row in (summary_row, clause_row, attention_row)
            if row is not None
        ]

        return DocumentUnderstandingOut(
            document_id=document_id,
            evidence_state=_document_state(summary_row, attention_row),
            summary=summary,
            parties=_parties_of(summary, chunk_rows),
            obligations=summary.obligations if summary else [],
            important_dates=_entities_of(chunk_rows, "DATE"),
            monetary_terms=_entities_of(chunk_rows, "AMOUNT"),
            termination=[c for c in clauses if c.clause_type == "Termination"],
            confidentiality=[c for c in clauses if c.clause_type == "Confidentiality"],
            important_clauses=clauses,
            attention_items=attention_items,
            abstention_reason=_abstention_reason(summary_row, attention_row),
            analysis_unavailable=_unavailable_message(rows),
        )

    def _attention_items(
        self, attention_row: dict[str, Any] | None, document_id: UUID
    ) -> list[AttentionItemOut]:
        if attention_row is None:
            return []
        return [
            AttentionItemOut(
                id=item.get("id"),
                analysis_id=item.get("analysis_id"),
                clause_id=item.get("clause_id"),
                title=item.get("title") or "",
                description=item.get("description") or "",
                attention_level=item.get("attention_level") or "LOW",
                category=item.get("category"),
                recommendation=item.get("recommendation"),
                status=item.get("status") or "OPEN",
                created_at=item.get("created_at"),
            )
            for item in self._analyses.attention_items_for(document_id)
        ]


# -- assembly helpers -----------------------------------------------------------


def _summary_of(row: dict[str, Any] | None) -> UnderstandingSummary | None:
    if row is None or row.get("status") != "COMPLETED" or not row.get("result"):
        return None
    output = SummaryOutput.model_validate(row["result"]["output"])
    evidence = [
        EvidenceReference.model_validate(item) for item in row["result"].get("evidence", [])
    ]
    return UnderstandingSummary(
        evidence_state=output.evidence_state,
        overview=output.overview,
        document_type=output.document_type,
        purpose=output.purpose,
        parties=output.parties,
        key_terms=output.key_terms,
        obligations=output.obligations,
        important_conditions=output.important_conditions,
        evidence=evidence,
    )


def _important_clauses_of(
    row: dict[str, Any] | None,
    section_rows: list[dict[str, Any]],
    clause_rows: list[dict[str, Any]],
) -> list[ImportantClause]:
    if row is None or row.get("status") != "COMPLETED" or not row.get("result"):
        return []
    sections_by_id = {str(s.get("id")): s for s in section_rows if s.get("id")}
    result = [
        _important_clause(item, clause_rows, sections_by_id)
        for item in ClauseExtractionOutput.model_validate(row["result"]["output"]).clauses
    ]
    return result


def _important_clause(
    outcome: ClauseOutcome,
    clause_rows: list[dict[str, Any]],
    sections_by_id: dict[str, dict[str, Any]],
) -> ImportantClause:
    persisted = _row_by_number(clause_rows, outcome.clause_number)
    section = sections_by_id.get(str(persisted.get("section_id"))) if persisted else None
    return ImportantClause(
        clause_id=UUID(str(persisted["id"])) if persisted else None,
        clause_number=outcome.clause_number,
        title=outcome.title,
        clause_type=outcome.clause_type.value,
        original_text=outcome.original_text,
        explanation=outcome.explanation,
        section=section.get("title") if section else None,
        page_start=persisted.get("page_start") if persisted else None,
        page_end=persisted.get("page_end") if persisted else None,
        source="Stored clause" if persisted else None,
    )


def _entities_of(
    chunk_rows: list[dict[str, Any]], entity_type: str
) -> list[EntityReference]:
    references: list[EntityReference] = []
    for row in chunk_rows:
        for entity in _metadata_entities(row):
            if entity.get("type") != entity_type:
                continue
            value = str(entity.get("value") or "")
            if not value:
                continue
            references.append(
                EntityReference(
                    type=entity_type,
                    value=value,
                    normalized=entity.get("normalized"),
                    clause_id=_uuid_of(row.get("clause_id")),
                    page_start=row.get("page_start"),
                    page_end=row.get("page_end"),
                )
            )
    return references


def _parties_of(
    summary: UnderstandingSummary | None, chunk_rows: list[dict[str, Any]]
) -> list[str]:
    if summary and summary.parties:
        return list(summary.parties)
    parties: list[str] = []
    for row in chunk_rows:
        for entity in _metadata_entities(row):
            if entity.get("type") == "PARTY" and entity.get("value"):
                value = str(entity["value"])
                if value not in parties:
                    parties.append(value)
    return parties


def _metadata_entities(row: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = row.get("metadata")
    entities = metadata.get("entities") if isinstance(metadata, dict) else None
    return [dict(item) for item in entities] if isinstance(entities, list) else []


def _document_state(
    summary_row: dict[str, Any] | None, attention_row: dict[str, Any] | None
) -> EvidenceState:
    for row in (summary_row, attention_row):
        if row is not None and row.get("status") == "COMPLETED" and row.get("result"):
            state = row["result"].get("evidence_state")
            try:
                return EvidenceState(state)
            except ValueError:
                continue
    return EvidenceState.INSUFFICIENT_EVIDENCE


def _abstention_reason(
    summary_row: dict[str, Any] | None, attention_row: dict[str, Any] | None
) -> str | None:
    for row in (summary_row, attention_row):
        if row is not None and row.get("status") == "COMPLETED" and row.get("result"):
            reason = row["result"].get("output", {}).get("abstention_reason")
            if isinstance(reason, str) and reason:
                return reason
    return None


def _unavailable_message(rows: list[dict[str, Any]]) -> str | None:
    """Return a controlled message when none of the analyses produced output."""
    if any(row.get("status") == "COMPLETED" for row in rows):
        return None
    for row in rows:
        message = row.get("error_message")
        if isinstance(message, str) and message:
            return message
    return "AI analysis is not available for this document."


# -- evidence reference builders -----------------------------------------------


def _whole_document_ref(
    sections: Sequence[ExtractedSection], clauses: Sequence[ExtractedClause]
) -> EvidenceReference:
    starts = [s.page_start for s in sections if s.page_start]
    ends = [s.page_end for s in sections if s.page_end]
    if not starts and clauses:
        starts = [c.page_start for c in clauses if c.page_start]
        ends = [c.page_end for c in clauses if c.page_end]
    return EvidenceReference(
        title="Full document",
        page_start=min(starts) if starts else None,
        page_end=max(ends) if ends else None,
        source="Deterministic extraction (sections and clauses)",
    )


def _clause_ref(
    outcome: ClauseOutcome, clauses: Sequence[ExtractedClause]
) -> EvidenceReference:
    matched = _row_by_number_persisted(clauses, outcome.clause_number)
    return EvidenceReference(
        clause_id=matched.id if matched else None,
        clause_number=outcome.clause_number,
        title=outcome.title,
        page_start=matched.page_start if matched else None,
        page_end=matched.page_end if matched else None,
        source="Stored clause" if matched else "Model-provided clause text",
    )


def _support_clause_ref(
    source_support: str, clauses: Sequence[ExtractedClause]
) -> EvidenceReference:
    matched = _match_clause(source_support, clauses)
    return EvidenceReference(
        clause_id=matched.id if matched else None,
        clause_number=matched.number if matched else None,
        title=matched.title if matched else None,
        page_start=matched.page_start if matched else None,
        page_end=matched.page_end if matched else None,
        source="Stored clause" if matched else "Model-provided source text",
    )


def _attention_item_row(
    item: AttentionItem, clauses: Sequence[ExtractedClause]
) -> dict[str, Any]:
    matched = _match_clause(item.source_support, clauses)
    return {
        "clause_id": str(matched.id) if matched else None,
        "title": item.area[:_TITLE_LIMIT],
        "description": item.reason,
        "attention_level": item.attention_level.value,
        "category": matched.clause_type if matched and matched.clause_type else None,
        "recommendation": item.practical_question,
        "status": "OPEN",
    }


def _match_clause(
    source_support: str, clauses: Sequence[ExtractedClause]
) -> ExtractedClause | None:
    """Find the clause whose text best supports an attention observation."""
    needle = _normalize(source_support)
    best: ExtractedClause | None = None
    best_span = 0
    for clause in clauses:
        haystack = _normalize(clause.content)
        if not haystack:
            continue
        if (haystack in needle or needle in haystack) and len(haystack) > best_span:
            best = clause
            best_span = len(haystack)
    return best


def _row_by_number_persisted(
    clauses: Sequence[ExtractedClause], clause_number: str | None
) -> ExtractedClause | None:
    number = (clause_number or "").strip()
    if not number:
        return None
    for clause in clauses:
        if (clause.number or "").strip() == number:
            return clause
    return None


def _row_by_number(
    clause_rows: list[dict[str, Any]], clause_number: str | None
) -> dict[str, Any] | None:
    number = (clause_number or "").strip()
    if not number:
        return None
    for row in clause_rows:
        if str(row.get("clause_number") or "").strip() == number:
            return row
    return None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", text)).strip().lower()


def _uuid_of(value: Any) -> UUID | None:
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _document_text(
    sections: Sequence[ExtractedSection], clauses: Sequence[ExtractedClause]
) -> str:
    if sections:
        return "\n\n".join(section.content for section in sections if section.content)
    return "\n\n".join(clause.content for clause in clauses if clause.content)


def _truncate(text: str) -> str:
    if len(text) <= _MAX_INPUT_CHARACTERS:
        return text
    return (
        text[:_MAX_INPUT_CHARACTERS]
        + "\n\n[The document was truncated at "
        + str(_MAX_INPUT_CHARACTERS)
        + " characters for analysis.]"
    )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _message(exc: Exception) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text[: _MESSAGE_LIMIT]