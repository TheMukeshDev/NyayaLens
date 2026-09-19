"""Action Center orchestration (docs/02_UX/UI-UX.md Â§45-Â§47, FR-014..FR-016).

Turns a processed document's understanding into practical next steps:

* **Review checklist** â€” every open attention area becomes a review action
  (``REVIEW_CLAUSE``), traced to its attention item and clause. This is a
  deterministic conversion of the persisted attention analysis: the user
  story US-017 "review checklist" is always available and fully traceable.
* **Follow-up items** â€” schema-validated practical next steps from the model
  (existing ``action`` prompt, Prompt-Strategy.md Â§11). Each item must cite a
  clause or attention item; items that cannot be resolved to any document
  evidence are dropped (never fabricated). ``ASK_PROFESSIONAL`` when the model
  attaches a professional question.
* **Important dates** â€” deterministically extracted calendar dates from the
  persisted clauses/sections (``entities.py``). The model never invents dates.
* **Professional questions** â€” questions for a qualified legal professional
  (FR-015), each traceable to a real clause when document-grounded. Questions
  whose source cannot be resolved are dropped; if none survive the service
  abstains with ``INSUFFICIENT-EVIDENCE``.
* **Review report** â€” an assembled text report (FR-016) stored as a private
  object, downloads only via short-lived signed URLs.

Honesty guarantees (same as the rest of the pipeline): no random legal advice,
no instruction to take a legal position, no outcome predictions, and every
document-based output carries a resolvable evidence reference. With no LLM
configured the deterministic parts (checklist, dates, attention-derived
search) still work and the model-dependent parts abstain openly.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.ai.analysis.service import StructuredLLM
from app.ai.llm.errors import LLMError, LLMOutputValidationError
from app.ai.prompts.models import Prompt
from app.ai.prompts.prompts import build_action_prompt, build_professional_questions_prompt
from app.ai.prompts.schemas import (
    ActionItem,
    ActionOutput,
    EvidenceState,
    ProfessionalQuestionsOutput,
)
from app.core.config import settings
from app.core.errors import (
    ActionNotFoundError,
    DocumentNotFoundError,
    ReportGenerationError,
    ReportNotFoundError,
    StorageError,
)
from app.core.supabase import get_supabase_client
from app.document_processing.entities import extract_entities
from app.repositories.actions import ActionsRepository
from app.repositories.analysis import AnalysisRepository
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.repositories.reports import ReportsRepository
from app.schemas.action_center import (
    ActionCenterOut,
    ActionOut,
    ActionSource,
    ActionType,
    ImportantDate,
    MonetaryTerm,
    ProfessionalQuestion,
    ProfessionalQuestionsOut,
    ReportDownloadOut,
    ReportOut,
)
from app.services.storage import DocumentStorage
from app.services.storage.supabase import SupabaseDocumentStorage

logger = logging.getLogger("app.ai.action_center")

_MAX_LLM_ITEMS = 24
_MAX_EVIDENCE_CLAUSES = 40
_MAX_EVIDENCE_CHARACTERS = 4_000
_CLAUSE_CHAR_LIMIT = 350
_REPORT_DOWNLOAD_TTL_SECONDS = 30 * 60
_NONE = "AI generation is not configured for this environment."
_NO_FOLLOW_UPS = "Follow-up generation is not available for this document."
_FOLLOW_UPS_FAILED = "Follow-up generation could not be completed for this document."
_NO_QUESTIONS = (
    "No professional question could be traced to the document content."
)
_NO_LLM_QUESTIONS = "Professional question generation is not available for this document."

_STOP_TOKENS = {
    "agreement", "contract", "document", "party", "parties", "shall", "will", "must",
    "may", "within", "per", "days", "upon", "under", "above", "hereby", "thereof",
}

_ClauseItem = tuple[dict[str, Any] | None, dict[str, Any]]


class ActionCenterService:
    """Generates, tracks and reports the Action Center for owned documents."""

    def __init__(
        self,
        *,
        llm: StructuredLLM | None,
        documents: DocumentRepository | None = None,
        processing: ProcessingRepository | None = None,
        analyses: AnalysisRepository | None = None,
        actions: ActionsRepository | None = None,
        reports: ReportsRepository | None = None,
        storage: DocumentStorage | None = None,
        audit: AuditLogRepository | None = None,
    ) -> None:
        self._llm = llm
        self._documents = documents or DocumentRepository()
        self._processing = processing or ProcessingRepository()
        self._analyses = analyses or AnalysisRepository()
        self._actions = actions or ActionsRepository()
        self._reports = reports or ReportsRepository()
        self._storage = storage or SupabaseDocumentStorage()
        self._audit = audit or AuditLogRepository()

    # -- action board --------------------------------------------------------

    def generate(self, user_id: UUID, document_id: UUID) -> ActionCenterOut:
        """Generate (and persist) the Action Center board for a document.

        Regeneration is delete-then-insert per document: the board is rebuilt
        from the current attention analysis and never accumulates stale items.
        """
        self._require_document(user_id, document_id)
        attention = self._analyses.attention_items_for(document_id)
        structure = self._structure(document_id)

        checklist_rows = self._checklist_rows(attention, structure)
        follow_up_rows, follow_up_state, follow_up_reason = self._follow_up_rows(
            document_id, attention, checklist_rows
        )
        self._actions.replace_for_document(
            user_id=user_id, document_id=document_id, rows=checklist_rows + follow_up_rows
        )

        stored = self._actions.list(user_id, document_id=document_id)
        checklist = [
            row
            for row in stored
            if row.get("action_type") == ActionType.REVIEW_CLAUSE.value
        ]
        follow_ups = [
            row
            for row in stored
            if row.get("action_type") != ActionType.REVIEW_CLAUSE.value
        ]

        dates = self._important_dates(document_id, structure)
        return ActionCenterOut(
            document_id=document_id,
            checklist=[self._to_action_out(row) for row in checklist],
            follow_ups=[self._to_action_out(row) for row in follow_ups],
            important_dates=dates,
            evidence_state=follow_up_state,
            abstention_reason=follow_up_reason,
        )

    def list_actions(
        self,
        user_id: UUID,
        *,
        document_id: UUID | None = None,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[ActionOut]:
        """Return the user's actions (optionally filtered), oldest first."""
        rows = self._actions.list(
            user_id, document_id=document_id, status=status, priority=priority
        )
        return [self._to_action_out(row) for row in rows]

    def update_action_status(
        self, user_id: UUID, action_id: UUID, status: str
    ) -> ActionOut:
        """Update one action's status (e.g. markup COMPLETED), or raise 404."""
        row = self._actions.set_status(user_id, action_id, status)
        if row is None:
            raise ActionNotFoundError()
        return self._to_action_out(row)

    # -- professional questions ----------------------------------------------

    def questions(
        self,
        user_id: UUID,
        document_id: UUID,
        *,
        user_context: str | None = None,
    ) -> ProfessionalQuestionsOut:
        """Generate professional questions traceable to the document.

        Every question raised as document-grounded must resolve to a real
        clause; unresolvable ones are dropped (never invented). If nothing
        survives, the service abstains.
        """
        self._require_document(user_id, document_id)
        attention = self._analyses.attention_items_for(document_id)
        structure = self._structure(document_id)

        output = self._generate_questions(
            structured=structure, attention=attention, user_context=user_context
        )
        if output is None:
            return ProfessionalQuestionsOut(
                evidence_state=EvidenceState.INSUFFICIENT_EVIDENCE,
                abstention_reason=_NO_LLM_QUESTIONS,
            )
        if output.evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE:
            return ProfessionalQuestionsOut(
                evidence_state=EvidenceState.INSUFFICIENT_EVIDENCE,
                abstention_reason=output.abstention_reason or _NO_QUESTIONS,
            )

        index = self._clause_index(structure)
        questions: list[ProfessionalQuestion] = []
        for item in output.questions:
            source = self._resolve_source(item.question, item.source, index)
            if source is None:
                continue
            questions.append(
                ProfessionalQuestion(question=item.question.strip(), source=source)
            )
            if len(questions) >= _MAX_LLM_ITEMS:
                break
        if not questions:
            return ProfessionalQuestionsOut(
                evidence_state=EvidenceState.INSUFFICIENT_EVIDENCE,
                abstention_reason=_NO_QUESTIONS,
            )
        return ProfessionalQuestionsOut(
            evidence_state=EvidenceState.DOCUMENT_GROUNDED,
            questions=questions,
        )

    # -- reports -------------------------------------------------------------

    def list_reports(self, user_id: UUID, document_id: UUID | None = None) -> list[ReportOut]:
        """Return the user's reports, newest first."""
        rows = self._reports.list(user_id, document_id=document_id)
        return [self._to_report_out(row) for row in rows]

    def get_report(self, user_id: UUID, report_id: UUID) -> ReportOut:
        """Return one owned report, or raise 404."""
        row = self._reports.get(user_id, report_id)
        if row is None:
            raise ReportNotFoundError()
        return self._to_report_out(row)

    def generate_report(self, user_id: UUID, document_id: UUID) -> ReportOut:
        """Generate a downloadable review report for an owned document.

        The report text is assembled from persisted document understanding
        (summary, attention, clauses, actions, dates) plus freshly generated
        professional questions, stored as a private object and marked READY.
        """
        self._require_document(user_id, document_id)
        created = self._reports.create(
            user_id=user_id,
            document_id=document_id,
            report_type="DOCUMENT_REVIEW",
            status="GENERATING",
        )
        report_id = UUID(str(created["id"]))
        try:
            content = self._assemble_report(user_id=user_id, document_id=document_id)
            storage_key = self._storage.store_report(
                user_id=user_id,
                document_id=document_id,
                report_id=report_id,
                content=content.encode("utf-8"),
            )
        except StorageError as exc:
            logger.error("report storage failed for %s", report_id, exc_info=exc)
            self._reports.mark(
                user_id, report_id, status="FAILED",
            )
            raise ReportGenerationError("The report could not be stored for download.") from None
        except Exception as exc:
            logger.error("report generation failed for %s", report_id, exc_info=exc)
            self._reports.mark(user_id, report_id, status="FAILED")
            raise ReportGenerationError() from exc

        self._reports.mark(
            user_id,
            report_id,
            status="READY",
            storage_key=storage_key,
            completed_at=_now_iso(),
        )
        self._audit.insert(
            action="report_generated",
            user_id=user_id,
            resource_type="reports",
            resource_id=report_id,
        )
        return self._to_report_out(self._reports.get(user_id, report_id) or created)

    def report_download_url(self, user_id: UUID, report_id: UUID) -> ReportDownloadOut:
        """Return a short-lived signed download URL for an owned READY report."""
        row = self._reports.get(user_id, report_id)
        if row is None:
            raise ReportNotFoundError()
        storage_key = row.get("storage_key")
        if row.get("status") != "READY" or not isinstance(storage_key, str) or not storage_key:
            raise ReportGenerationError("The report is not ready for download.")
        url = self._storage.create_signed_url(
            storage_key,
            expires_in_seconds=_REPORT_DOWNLOAD_TTL_SECONDS,
            content_type="text/plain; charset=utf-8",
        )
        return ReportDownloadOut(report_id=report_id, download_url=url)

    # -- checklist + follow-up assembly ----------------------------------------

    def _checklist_rows(
        self,
        attention: list[dict[str, Any]],
        structure: list[_ClauseItem] | None = None,
    ) -> list[dict[str, Any]]:
        """Deterministic REVIEW_CLAUSE actions from open attention items."""
        index = self._clause_index(structure) if structure else {}
        rows: list[dict[str, Any]] = []
        for item in attention:
            if item.get("status") not in {"OPEN", "IN_PROGRESS"}:
                continue
            row: dict[str, Any] = {
                "attention_item_id": str(item["id"]),
                "action_type": ActionType.REVIEW_CLAUSE.value,
                "title": (str(item.get("title") or "")[:255]) or "Review attention area",
                "description": (
                    str(
                        item.get("recommendation")
                        or item.get("description")
                        or ""
                    )[:2000]
                    or None
                ),
                "priority": str(item.get("attention_level") or "MEDIUM"),
            }
            clause_id = item.get("clause_id")
            if clause_id and str(clause_id) in index:
                row["source"] = self._source_of(index[str(clause_id)]).model_dump()
            rows.append(row)
        return rows

    def _follow_up_rows(
        self,
        document_id: UUID,
        attention: list[dict[str, Any]],
        checklist_rows: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], EvidenceState, str | None]:
        """Schema-validated practical follow-ups, each resolved to evidence.

        Returns ``(rows, evidence_state, abstention_reason)`` so the board can
        report the model part honestly: an unavailable or failed generation is
        an open abstention, never fabricated follow-ups.
        """
        llm = self._llm
        if llm is None:
            return [], EvidenceState.INSUFFICIENT_EVIDENCE, _NO_FOLLOW_UPS
        used_attention = {UUID(str(row["attention_item_id"])) for row in checklist_rows}
        output = self._generate_actions(document_id)
        if output is None:
            return [], EvidenceState.INSUFFICIENT_EVIDENCE, _FOLLOW_UPS_FAILED
        if output.evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE:
            return (
                [],
                EvidenceState.INSUFFICIENT_EVIDENCE,
                output.abstention_reason or _NO_FOLLOW_UPS,
            )
        structure = self._structure(document_id)
        index = self._clause_index(structure)
        rows: list[dict[str, Any]] = []
        matched_attention: set[str] = set()
        for item in output.actions:
            source = self._resolve_source(
                f"{item.title} {item.practical_question or ''}".strip(),
                item.source,
                index,
            )
            attention_row = self._attention_for(
                attention, used_attention=used_attention, already=matched_attention, item=item
            )
            if attention_row is not None:
                matched_attention.add(str(attention_row["id"]))
                source = self._source_from_attention(attention_row, index)
            elif source is None:
                continue
            action_type = (
                ActionType.ASK_PROFESSIONAL.value
                if item.practical_question
                else ActionType.FOLLOW_UP.value
            )
            reason = (item.reason or "").strip()
            row: dict[str, Any] = {
                "action_type": action_type,
                "title": (item.title or "")[:255] or "Review item",
                "description": (reason[:2000] or None),
                "priority": item.priority.value,
                "source": source.model_dump(),
            }
            if attention_row is not None:
                row["attention_item_id"] = str(attention_row["id"])
            rows.append(row)
            if len(rows) >= _MAX_LLM_ITEMS:
                break
        return rows, EvidenceState.DOCUMENT_GROUNDED, None

    def _attention_for(
        self,
        attention: list[dict[str, Any]],
        *,
        used_attention: set[UUID],
        already: set[str],
        item: ActionItem,
    ) -> dict[str, Any] | None:
        """Match an LLM action to the attention item it elaborates on, if any."""
        tokens = {token for token in _tokens(f"{item.title} {item.reason}")}
        for candidate in attention:
            candidate_id = str(candidate["id"])
            if candidate_id in already:
                continue
            if UUID(candidate_id) in used_attention:
                continue
            candidate_tokens = _tokens(
                f"{candidate.get('title') or ''} {candidate.get('description') or ''}"
            )
            if tokens & candidate_tokens:
                return candidate
        return None

    def _generate_actions(self, document_id: UUID) -> ActionOutput | None:
        """Generate the follow-up action list (one retry, honest None)."""
        llm = self._llm
        if llm is None:
            return None
        attention = self._analyses.attention_items_for(document_id)
        structure = self._structure(document_id)
        summary = self._analyses.latest(document_id, "SUMMARY")
        prompt = build_action_prompt(
            summary=_summary_overview(summary),
            attention=_attention_brief(attention),
            key_clauses=_clause_brief(structure),
        )
        return self._generate(llm, prompt, ActionOutput)

    def _generate_questions(
        self,
        *,
        structured: list[_ClauseItem],
        attention: list[dict[str, Any]],
        user_context: str | None,
    ) -> ProfessionalQuestionsOutput | None:
        llm = self._llm
        if llm is None:
            return None
        prompt = build_professional_questions_prompt(
            attention=_attention_brief(attention),
            key_clauses=_clause_brief(structured),
            user_context=user_context,
        )
        return self._generate(llm, prompt, ProfessionalQuestionsOutput)

    def _generate(
        self,
        llm: StructuredLLM,
        prompt: Prompt,
        schema: type[Any],
    ) -> Any | None:
        """Schema-validated generation with one retry; ``None`` on failure.

        Any LLM failure means abstention â€” the caller never fabricates a
        substitute. (Mirrors the comparison service.)
        """
        try:
            return llm.structured_generate(
                prompt.messages,
                schema=schema,
                max_tokens=prompt.max_tokens,
                temperature=prompt.temperature,
            )
        except LLMOutputValidationError:
            pass
        except LLMError as exc:
            logger.warning("action-center generation failed: %s", _message(exc))
            return None
        try:
            return llm.structured_generate(
                prompt.messages,
                schema=schema,
                max_tokens=prompt.max_tokens,
                temperature=prompt.temperature,
            )
        except LLMError as exc:
            logger.warning("action-center generation failed: %s", _message(exc))
            return None

    # -- evidence resolution --------------------------------------------------

    def _resolve_source(
        self,
        text: str,
        source: dict[str, Any],
        index: dict[str, _ClauseItem],
    ) -> ActionSource | None:
        """Resolve a generated item's source to a persisted clause, or ``None``.

        Resolution order: exact clause number, then meaningful-token overlap
        with a clause title/content. ``None`` means the item is unattributable
        and is dropped â€” the service never invents a citation.
        """
        if not index:
            return None
        numbers = _clause_numbers(_string_values(source))
        for number in numbers:
            for _, item in index.items():
                if _clause_number(item[1]) == number:
                    return self._source_of(item)
        tokens = {token for token in _tokens(text) if token not in _STOP_TOKENS}
        if not tokens:
            return None
        for item in index.values():
            clause = item[1]
            title_tokens = {token for token in _tokens(str(clause.get("title") or ""))}
            content_tokens = {token for token in _tokens(str(clause.get("content") or ""))}
            if tokens & (title_tokens | content_tokens):
                return self._source_of(item)
        return None

    def _source_of(self, item: _ClauseItem) -> ActionSource:
        section, clause = item
        page_start = _page_of(clause, section, "page_start")
        page_end = _page_of(clause, section, "page_end")
        return ActionSource(
            section=_section_label(section),
            clause=_clause_label(clause),
            page_start=page_start,
            page_end=page_end,
        )

    def _source_from_attention(
        self, item: dict[str, Any], index: dict[str, _ClauseItem]
    ) -> ActionSource:
        clause_id = item.get("clause_id")
        if clause_id and str(clause_id) in index:
            return self._source_of(index[str(clause_id)])
        return self._source_from_strings(item)

    def _source_from_strings(self, item: dict[str, Any]) -> ActionSource:
        return ActionSource(
            section=_optional(item.get("category")),
            clause=_optional(item.get("title")),
        )

    def _clause_index(self, structure: list[_ClauseItem]) -> dict[str, _ClauseItem]:
        return {str(item[1]["id"]): item for item in structure}

    # -- important dates ------------------------------------------------------

    def _important_dates(
        self, document_id: UUID, structure: list[_ClauseItem]
    ) -> list[ImportantDate]:
        """Deterministically extract calendar dates from clauses and sections."""
        dates: list[ImportantDate] = []
        seen: set[str] = set()

        def add(text: str, item: _ClauseItem | None, section: dict[str, Any] | None) -> None:
            clause = item[1] if item else None
            page = _page_of(clause, section, "page_start")
            for entity in extract_entities(text, page=page):
                if entity.type != "DATE":
                    continue
                key = entity.normalized or entity.value
                if key in seen:
                    continue
                seen.add(key)
                label = _clause_label(clause) if clause else _section_label(section)
                source = (
                    self._source_of(item)
                    if item
                    else ActionSource(section=_section_label(section), page_start=page)
                )
                dates.append(
                    ImportantDate(
                        value=entity.value,
                        normalized=entity.normalized,
                        label=label,
                        source=source,
                    )
                )

        for item in structure:
            add(_content(item[1]), item, item[0])
        if len(dates) < 20:
            for section in self._processing.list_sections(document_id):
                if len(dates) >= 20:
                    break
                add(str(section.get("content") or ""), None, section)
        return dates[:20]

    def _monetary_terms(
        self, document_id: UUID, structure: list[_ClauseItem]
    ) -> list[MonetaryTerm]:
        """Deterministically extract monetary amounts from clauses and sections."""
        amounts: list[MonetaryTerm] = []
        seen: set[str] = set()

        def add(text: str, item: _ClauseItem | None, section: dict[str, Any] | None) -> None:
            clause = item[1] if item else None
            page = _page_of(clause, section, "page_start")
            for entity in extract_entities(text, page=page):
                if entity.type != "AMOUNT":
                    continue
                key = entity.normalized or entity.value
                if key in seen:
                    continue
                seen.add(key)
                label = _clause_label(clause) if clause else _section_label(section)
                source = (
                    self._source_of(item)
                    if item
                    else ActionSource(section=_section_label(section), page_start=page)
                )
                amounts.append(
                    MonetaryTerm(
                        value=entity.value,
                        normalized=entity.normalized,
                        label=label,
                        source=source,
                    )
                )

        for item in structure:
            add(_content(item[1]), item, item[0])
        if len(amounts) < 20:
            for section in self._processing.list_sections(document_id):
                if len(amounts) >= 20:
                    break
                add(str(section.get("content") or ""), None, section)
        return amounts[:20]

    # -- report assembly ------------------------------------------------------

    def _assemble_report(self, *, user_id: UUID, document_id: UUID) -> str:
        document = self._require_document(user_id, document_id)
        attention = self._analyses.attention_items_for(document_id)
        structure = self._structure(document_id)
        summary = self._analyses.latest(document_id, "SUMMARY")
        clause_row = self._analyses.latest(document_id, "CLAUSE_EXTRACTION")
        questions = self.questions(user_id=user_id, document_id=document_id)
        actions = self._actions.list(user_id, document_id=document_id)
        dates = self._important_dates(document_id, structure)
        monetary = self._monetary_terms(document_id, structure)

        doc_title = (
            document.get("display_name")
            or document.get("original_filename")
            or "Untitled Document"
        )
        gen_timestamp = _now_iso()

        lines: list[str] = [
            "================================================================================",
            "NyayaLens Document Review",
            "================================================================================",
            "",
            f"Document: {doc_title}",
            f"Document Title: {doc_title}",
            f"Document type: {_summary_field(summary, 'document_type') or 'Not detected'}",
            f"Date analyzed: {_now_date()}",
            f"Generated Timestamp: {gen_timestamp}",
            "",
            "--------------------------------------------------------------------------------",
            "Responsible AI Disclaimer",
            "AI & Privacy Disclaimer",
            "--------------------------------------------------------------------------------",
            "This tool provides informational assistance and does not provide "
            "legal advice or legal representation.",
            "",
            "This report was generated by NyayaLens for informational purposes only and does "
            "not constitute legal advice.",
            "It describes what the document says and areas that may deserve review; it does not "
            "predict any legal outcome.",
            "Documents remain private to you. Consult a qualified legal professional for advice "
            "about your situation.",
            "",
            "================================================================================",
            "=== DOCUMENT EVIDENCE ===",
            "================================================================================",
            "",
            "Key Clauses",
            "Important Clauses",
            "-----------------",
        ]

        extracted_clauses = _clauses_from_analysis(clause_row)
        if extracted_clauses:
            for item in extracted_clauses:
                type_prefix = f"[{item.get('clause_type')}] " if item.get("clause_type") else ""
                clause_title = item.get("title") or item.get("clause_number") or "Clause"
                lines.append(f"- {type_prefix}{clause_title}:")
                if item.get("explanation"):
                    lines.append(f"  Explanation: {item.get('explanation')}")
                original_text = item.get("original_text")
                if isinstance(original_text, str) and original_text:
                    lines.append(
                        f'  Original Text: "{original_text[:_CLAUSE_CHAR_LIMIT]}"'
                    )
        elif structure:
            for clause_pair in structure[: _MAX_EVIDENCE_CLAUSES]:
                section, clause = clause_pair
                label = _clause_label(clause) or _section_label(section)
                lines.append(f"- {label}: {_content(clause)[:_CLAUSE_CHAR_LIMIT]}")
        else:
            lines.append("Important Clauses: none extracted.")

        lines.extend(["", "Important Dates", "---------------"])
        if dates:
            for entry in dates:
                where = f" ({entry.label})" if entry.label else ""
                lines.append(f"- {entry.value}{where}")
        else:
            lines.append("- None detected.")

        lines.extend(["", "Monetary Terms", "--------------"])
        if monetary:
            for term in monetary:
                where = f" ({term.label})" if term.label else ""
                lines.append(f"- {term.value}{where}")
        else:
            lines.append("- None detected.")

        lines.extend(["", "Attention Items", "Areas to Review", "---------------"])
        if attention:
            for area in attention:
                lines.append(
                    f"- [{area.get('attention_level')}] {area.get('title')}: "
                    f"{area.get('description') or ''}"
                )
                if area.get("recommendation"):
                    lines.append(f"  Recommendation: {area.get('recommendation')}")
        else:
            lines.append("- None identified.")

        lines.extend(
            [
                "",
                "================================================================================",
                "=== AI-GENERATED INTERPRETATION ===",
                "================================================================================",
                "",
                "Summary",
                "-------",
            ]
        )
        overview = _summary_field(summary, "overview")
        if overview:
            lines.append(f"Executive Summary: {overview}")
        else:
            lines.append("Executive Summary: Not available.")

        purpose = _summary_field(summary, "purpose")
        if purpose:
            lines.append(f"Purpose: {purpose}")

        key_details = {
            "Parties": _summary_field(summary, "parties"),
            "Key terms": _summary_field(summary, "key_terms"),
            "Obligations": _summary_field(summary, "obligations"),
            "Important conditions": _summary_field(summary, "important_conditions"),
        }
        for label, value in key_details.items():
            if value:
                lines.append(f"{label}: {value}")

        lines.extend(["", "Review Checklist", "----------------"])
        checklist_items = [
            a for a in actions if a.get("action_type") == ActionType.REVIEW_CLAUSE.value
        ] or actions
        if checklist_items:
            for action in checklist_items:
                box = "[x]" if action.get("status") == "COMPLETED" else "[ ]"
                label = _clause_label_safe(action)
                lines.append(
                    f"{box} [{action.get('priority')}] {action.get('title')} "
                    f"({action.get('action_type')}){label}"
                )
        elif attention:
            for row in self._checklist_rows(attention, structure):
                label = _clause_label_safe(row)
                lines.append(f"[ ] [{row.get('priority')}] {row.get('title')}{label}")
        else:
            lines.append("[ ] Review full document terms and standard provisions.")

        lines.extend(
            [
                "",
                "Professional Questions",
                "Questions for Professional",
                "--------------------------",
            ]
        )
        if questions.evidence_state == EvidenceState.DOCUMENT_GROUNDED and questions.questions:
            for idx, question in enumerate(questions.questions, start=1):
                where = (
                    f" [source: {_source_text(question.source)}]"
                    if question.source.clause
                    else ""
                )
                lines.append(f"{idx}. {question.question}{where}")
        elif questions.abstention_reason:
            lines.append(f"- Not generated: {questions.abstention_reason}")
        else:
            lines.append("- None generated.")

        if actions:
            lines.extend(["", "Suggested Actions", "-----------------"])
            for action in actions:
                label = _clause_label_safe(action)
                lines.append(
                    f"- [{action.get('priority')}] {action.get('title')} "
                    f"({action.get('action_type')}){label}"
                )

        lines.extend(
            [
                "",
                "Citations",
                "---------",
                *([f"- {_citation(label)}" for label in _citations(structure)] or ["- None."]),
                "",
                "================================================================================",
                f"Generated: {gen_timestamp}",
                "================================================================================",
            ]
        )
        return "\n".join(lines)

    # -- shared helpers --------------------------------------------------------

    def _require_document(self, user_id: UUID, document_id: UUID) -> dict[str, Any]:
        row = self._documents.get_by_id_and_user(user_id, document_id)
        if row is None:
            raise DocumentNotFoundError()
        return row

    def _structure(self, document_id: UUID) -> list[_ClauseItem]:
        sections = self._processing.list_sections(document_id)
        by_id = {str(row["id"]): row for row in sections}
        items: list[_ClauseItem] = []
        for clause in self._processing.list_clauses(document_id):
            section = None
            section_id = clause.get("section_id")
            if section_id:
                section = by_id.get(str(section_id))
            items.append((section, clause))
        return items

    def _to_action_out(self, row: dict[str, Any]) -> ActionOut:
        attention_id = row.get("attention_item_id")
        source = row.get("source")
        output_attention_id: UUID | None = None
        if attention_id:
            try:
                output_attention_id = UUID(str(attention_id))
            except ValueError:
                output_attention_id = None
        source_model = _action_source(source, row)
        return ActionOut(
            id=UUID(str(row["id"])),
            document_id=UUID(str(row["document_id"])),
            attention_item_id=output_attention_id,
            action_type=ActionType(str(row.get("action_type") or ActionType.REVIEW_CLAUSE)),
            title=str(row.get("title") or ""),
            description=_optional(row.get("description")),
            priority=str(row.get("priority") or "MEDIUM"),
            status=str(row.get("status") or "TODO"),
            due_date=row.get("due_date") or None,
            source=source_model,
            created_at=row.get("created_at") or None,
        )

    def _to_report_out(self, row: dict[str, Any]) -> ReportOut:
        return ReportOut(
            report_id=UUID(str(row["id"])),
            document_id=UUID(str(row["document_id"])),
            report_type=str(row.get("report_type") or "DOCUMENT_REVIEW"),
            status=str(row.get("status") or "GENERATING"),
            created_at=row.get("created_at") or None,
            completed_at=row.get("completed_at") or None,
        )


# -- assembly -----------------------------------------------------------------


def build_action_center_service(
    *, client: Any | None = None, storage: DocumentStorage | None = None
) -> ActionCenterService:
    """Assemble the service from settings + the Supabase client."""
    client = client or get_supabase_client()
    return ActionCenterService(
        llm=_build_llm(),
        documents=DocumentRepository(client=client),
        processing=ProcessingRepository(client=client),
        analyses=AnalysisRepository(client=client),
        actions=ActionsRepository(client=client),
        reports=ReportsRepository(client=client),
        storage=storage or SupabaseDocumentStorage(client=client),
        audit=AuditLogRepository(client=client),
    )


def _build_llm() -> StructuredLLM | None:
    """Build the configured LLM provider, or ``None`` when not configured."""
    if not settings.llm_model or not settings.llm_api_url:
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


# -- small helpers -------------------------------------------------------------


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{4,}", value.lower())}


def _clause_numbers(values: list[str]) -> list[str]:
    numbers: list[str] = []
    for value in values:
        numbers.extend(re.findall(r"\b\d+(?:\.\d+)+\b", value))
        numbers.extend(re.findall(r"\b\d+\b", value))
    return numbers


def _string_values(source: dict[str, Any]) -> list[str]:
    return [str(value) for value in source.values() if isinstance(value, str) and value]


def _summary_overview(row: dict[str, Any] | None) -> str:
    value = _summary_output(row).get("overview")
    return str(value) if isinstance(value, str) else ""


def _summary_field(row: dict[str, Any] | None, key: str) -> str | None:
    output = _summary_output(row)
    value = output.get(key)
    if isinstance(value, list):
        rendered = " ".join(str(v) for v in value)
        return rendered.strip() or None
    if isinstance(value, str) and value:
        return value
    return None


def _summary_output(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    result = row.get("result")
    if isinstance(result, dict):
        output = result.get("output")
        if isinstance(output, dict):
            return output
    return {}


def _clauses_from_analysis(row: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not row or row.get("status") != "COMPLETED":
        return []
    result = row.get("result")
    if isinstance(result, dict):
        output = result.get("output")
        if isinstance(output, dict):
            clauses = output.get("clauses")
            if isinstance(clauses, list):
                return [c for c in clauses if isinstance(c, dict)]
    return []


def _attention_brief(attention: list[dict[str, Any]]) -> list[str]:
    brief: list[str] = []
    for item in attention[: _MAX_EVIDENCE_CLAUSES]:
        note = item.get("title")
        if item.get("recommendation"):
            note = f"{note} â€” {item.get('recommendation')}"
        brief.append(f"[{item.get('attention_level')}] {note or item.get('description')}")
    return brief


def _clause_brief(structure: list[_ClauseItem]) -> list[str]:
    brief: list[str] = []
    for item in structure[:_MAX_EVIDENCE_CLAUSES]:
        section, clause = item
        label = _clause_label(clause) or _section_label(section)
        text = _content(clause)
        if len(text) > _MAX_EVIDENCE_CHARACTERS:
            text = text[:_MAX_EVIDENCE_CHARACTERS] + "â€¦"
        brief.append(f"{label}: {text}")
    return brief


def _content(clause: dict[str, Any]) -> str:
    value = clause.get("content")
    return str(value) if isinstance(value, str) else ""


def _clause_label(clause: dict[str, Any]) -> str | None:
    number = _optional(clause.get("clause_number"))
    title = _optional(clause.get("title"))
    labeled = f"{number} {title}".strip() if number else None
    return labeled or title or number


def _section_label(section: dict[str, Any] | None) -> str:
    if section is None:
        return "Preamble"
    number = _optional(section.get("section_number"))
    title = _optional(section.get("title"))
    labeled = f"{number} {title}".strip() if number else None
    return labeled or title or number or "Preamble"


def _clause_number(clause: dict[str, Any]) -> str:
    value = _optional(clause.get("clause_number"))
    return value or ""


def _page_of(
    clause: dict[str, Any] | None,
    section: dict[str, Any] | None,
    column: str,
) -> int | None:
    if clause is not None:
        value = clause.get(column)
        if isinstance(value, int):
            return value
    if section is not None:
        value = section.get(column)
        if isinstance(value, int):
            return value
    return None


def _optional(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _action_source(source: object, row: dict[str, Any]) -> ActionSource:
    if isinstance(source, dict):
        return ActionSource(
            section=_string(source, "section"),
            clause=_string(source, "clause"),
            page_start=_int(source, "page_start"),
            page_end=_int(source, "page_end"),
        )
    return ActionSource()


def _string(source: dict[str, Any], key: str) -> str | None:
    value = source.get(key)
    return str(value) if isinstance(value, str) and value else None


def _int(source: dict[str, Any], key: str) -> int | None:
    value = source.get(key)
    return value if isinstance(value, int) else None


def _source_text(source: ActionSource) -> str:
    values: list[str] = []
    if source.section:
        values.append(source.section)
    if source.clause:
        values.append(source.clause)
    if source.page_start:
        values.append(f"p.{source.page_start}")
    return ", ".join(values)


def _clause_label_safe(row: dict[str, Any]) -> str:
    source = row.get("source")
    if isinstance(source, dict):
        label = _string(source, "clause")
        if label:
            return f" [{label}]"
    return ""


def _citation(label: str) -> str:
    return f"Clause reference: {label}"


def _citations(structure: list[_ClauseItem]) -> list[str]:
    labels: list[str] = []
    for item in structure[:_MAX_EVIDENCE_CLAUSES]:
        section, clause = item
        label = _clause_label(clause) or _section_label(section)
        if label not in labels:
            labels.append(label)
    return labels


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _now_date() -> str:
    return datetime.now(UTC).date().isoformat()


def _message(exc: Exception) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text[:500]