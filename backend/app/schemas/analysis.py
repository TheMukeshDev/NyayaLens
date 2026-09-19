"""Document-understanding schemas: persistence contract and read model.

The AI document-understanding layer (docs/04_AI/AI-Architecture.md §4-§9)
persists validated structured outputs into ``analyses`` and ``attention_items``
(Database-Schema.md §9) and returns them through the read model below.

Safety contract:

* Every important output retains evidence references (clause ids, section
  labels, page ranges).
* There is no legal score, no validity judgment and no outcome guarantee:
  clauses are surfaced as plain-language analysis with sources, and attention is
  framed as *areas requiring attention* (Responsible-AI.md §6-§7).
* Uncertainty is explicit through the evidence states DOCUMENT-GROUNDED,
  GENERAL-INFORMATION and INSUFFICIENT-EVIDENCE, and ``analysis_unavailable``
  carries a controlled message when the AI provider could not produce content.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.prompts.schemas import EvidenceState


class AnalysisType(StrEnum):
    """Canonical analysis kinds (Database-Schema.md §9)."""

    SUMMARY = "SUMMARY"
    CLAUSE_EXTRACTION = "CLAUSE_EXTRACTION"
    ATTENTION_ANALYSIS = "ATTENTION_ANALYSIS"
    ENTITY_EXTRACTION = "ENTITY_EXTRACTION"
    ACTION_GENERATION = "ACTION_GENERATION"


class AnalysisStatus(StrEnum):
    """Lifecycle of one analysis row (migration 20260917000000)."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvidenceReference(BaseModel):
    """One source location an analysis output is grounded on."""

    clause_id: UUID | None = None
    clause_number: str | None = None
    title: str | None = None
    section: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    source: str | None = None


class AnalysisRecordOut(BaseModel):
    """Projection of one ``analyses`` row (safe for clients)."""

    id: UUID
    document_id: UUID
    analysis_type: AnalysisType
    model_name: str | None = None
    prompt_version: str | None = None
    status: AnalysisStatus
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class AttentionItemOut(BaseModel):
    """One area requiring attention — a review signal, never a legal conclusion."""

    id: UUID
    analysis_id: UUID
    clause_id: UUID | None = None
    title: str
    description: str
    attention_level: str
    category: str | None = None
    recommendation: str | None = None
    status: str
    created_at: datetime | None = None


class EntityReference(BaseModel):
    """A deterministically extracted entity with its source location."""

    type: str
    value: str
    normalized: str | None = None
    clause_id: UUID | None = None
    page_start: int | None = None
    page_end: int | None = None


class UnderstandingSummary(BaseModel):
    """Plain-language summary block (features: overview, parties, conditions)."""

    evidence_state: EvidenceState
    overview: str | None = None
    document_type: str | None = None
    purpose: str | None = None
    parties: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    important_conditions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class ImportantClause(BaseModel):
    """One clause with its plain-language analysis and evidence reference."""

    clause_id: UUID | None = None
    clause_number: str | None = None
    title: str | None = None
    clause_type: str | None = None
    original_text: str
    explanation: str
    section: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    source: str | None = None


class DocumentUnderstandingOut(BaseModel):
    """The complete, evidence-referenced document-understanding feature set.

    No legal score, no "safe"/"illegal" verdict and no outcome promise. Dates and
    monetary terms come from deterministic extraction (with page references),
    termination/confidentiality/important clauses come from validated AI clause
    analysis, and attention is reported as neutral areas requiring attention.
    """

    document_id: UUID
    evidence_state: EvidenceState
    summary: UnderstandingSummary | None = None
    parties: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    important_dates: list[EntityReference] = Field(default_factory=list)
    monetary_terms: list[EntityReference] = Field(default_factory=list)
    termination: list[ImportantClause] = Field(default_factory=list)
    confidentiality: list[ImportantClause] = Field(default_factory=list)
    important_clauses: list[ImportantClause] = Field(default_factory=list)
    attention_items: list[AttentionItemOut] = Field(default_factory=list)
    abstention_reason: str | None = None
    analysis_unavailable: str | None = None