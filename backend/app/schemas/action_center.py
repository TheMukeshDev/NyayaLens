"""Action Center schemas (docs/02_UX/Screen-Specification.md §45-§47).

The Action Center converts document understanding into practical next steps:

* a review checklist and follow-up items (persisted as ``actions`` rows,
  Database-Schema.md §13) that the user can track and mark complete;
* important dates extracted deterministically from the document's clauses
  (never invented by the model);
* questions to discuss with a qualified professional, each traceable to
  document evidence when document-based;
* a downloadable review report (Database-Schema.md §14).

Safety contract (Responsible-AI.md §6-§7): nothing here gives legal advice or
tells the user which legal decision to make. Every action carries its source
attention item or clause reference, every question must resolve to a real
clause when document-grounded, and the report labels what comes from the
document versus what is AI-generated interpretation.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.prompts.schemas import EvidenceState


class ActionType(StrEnum):
    """Canonical action kinds (Database-Schema.md §13.1)."""

    REVIEW_CLAUSE = "REVIEW_CLAUSE"
    ASK_PROFESSIONAL = "ASK_PROFESSIONAL"
    COLLECT_DOCUMENT = "COLLECT_DOCUMENT"
    VERIFY_INFORMATION = "VERIFY_INFORMATION"
    NEGOTIATE_TERM = "NEGOTIATE_TERM"
    FOLLOW_UP = "FOLLOW_UP"


class ActionStatus(StrEnum):
    """Lifecycle of one action row (migration 20260917000000)."""

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"


class ActionSource(BaseModel):
    """The document evidence an action or question is grounded on."""

    section: str | None = None
    clause: str | None = None
    page_start: int | None = None
    page_end: int | None = None


class ActionOut(BaseModel):
    """One persisted action, with its evidence reference."""

    id: UUID
    document_id: UUID
    attention_item_id: UUID | None = None
    action_type: ActionType
    title: str
    description: str | None = None
    priority: str
    status: ActionStatus
    due_date: date | None = None
    source: ActionSource
    created_at: datetime | None = None


class ActionStatusUpdate(BaseModel):
    """Body for ``PATCH /actions/{action_id}`` (mark complete/dismiss)."""

    status: ActionStatus


class ImportantDate(BaseModel):
    """One deterministically extracted date with its document location."""

    value: str
    normalized: str | None = None
    label: str | None = None
    source: ActionSource


class MonetaryTerm(BaseModel):
    """One deterministically extracted monetary term with its document location."""

    value: str
    normalized: str | None = None
    label: str | None = None
    source: ActionSource


class ProfessionalQuestion(BaseModel):
    """A question for a qualified professional, traceable to evidence."""

    question: str
    source: ActionSource


class ProfessionalQuestionsOut(BaseModel):
    """Question generation outcome (docs/03_TECH/API-Specification.md §21)."""

    evidence_state: EvidenceState
    questions: list[ProfessionalQuestion] = Field(default_factory=list)
    abstention_reason: str | None = None


class ActionCenterOut(BaseModel):
    """The generated Action Center board for one document."""

    document_id: UUID
    checklist: list[ActionOut] = Field(default_factory=list)
    follow_ups: list[ActionOut] = Field(default_factory=list)
    important_dates: list[ImportantDate] = Field(default_factory=list)
    evidence_state: EvidenceState
    abstention_reason: str | None = None


class ReportOut(BaseModel):
    """Projection of one ``reports`` row (Database-Schema.md §14.1)."""

    report_id: UUID
    document_id: UUID
    report_type: str
    status: str
    created_at: datetime | None = None
    completed_at: datetime | None = None


class ReportDownloadOut(BaseModel):
    """Short-lived secure download link for a generated report."""

    report_id: UUID
    download_url: str