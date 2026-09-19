"""Structured output schemas for the versioned prompts.

These are the JSON contracts the LLM is asked to produce (AI-Architecture.md
§12, Prompt-Strategy.md §9-§11). Every schema supports **abstention**: when the
evidence does not support an answer, ``evidence_state`` is
``INSUFFICIENT-EVIDENCE`` and ``abstention_reason`` explains why — the model
must not invent content to fill the fields.

Citation ownership/existence is validated downstream by the citation validator
(AI-Architecture.md §13); the schemas only carry the IDs the prompt references.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class EvidenceState(StrEnum):
    DOCUMENT_GROUNDED = "DOCUMENT-GROUNDED"
    GENERAL_INFORMATION = "GENERAL-INFORMATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT-EVIDENCE"


class RelativeImportance(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ChangeType(StrEnum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    UNCHANGED = "UNCHANGED"


class ClauseType(StrEnum):
    Termination = "Termination"
    Payment = "Payment"
    Confidentiality = "Confidentiality"
    IntellectualProperty = "Intellectual Property"
    Liability = "Liability"
    Indemnification = "Indemnification"
    DisputeResolution = "Dispute Resolution"
    GoverningLaw = "Governing Law"
    Renewal = "Renewal"
    Notice = "Notice"
    Other = "Other"


class Citation(BaseModel):
    """A citation the model produced. ``chunk_id`` must match a supplied
    ``[Source N]`` block; existence and ownership are validated downstream."""

    chunk_id: str


class SummaryOutput(BaseModel):
    """Structured document summary (AI-Architecture.md §7)."""

    evidence_state: EvidenceState = Field(
        default=EvidenceState.DOCUMENT_GROUNDED,
        description="DOCUMENT-GROUNDED when the summary is supported by the supplied text.",
    )
    overview: str | None = None
    document_type: str | None = None
    purpose: str | None = None
    parties: list[str] = Field(default_factory=list, description="Named parties in the document.")
    key_terms: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    important_conditions: list[str] = Field(default_factory=list)
    abstention_reason: str | None = Field(
        default=None,
        description="Required whenever evidence_state is INSUFFICIENT-EVIDENCE.",
    )


class ClauseOutcome(BaseModel):
    """One analyzed clause (Clause Analysis, AI-Architecture.md §8)."""

    clause_number: str | None = None
    clause_type: ClauseType
    title: str | None = None
    original_text: str
    explanation: str


class ClauseExtractionOutput(BaseModel):
    """Clause classification + explanation (Prompt-Strategy.md §6)."""

    evidence_state: EvidenceState = Field(default=EvidenceState.DOCUMENT_GROUNDED)
    clauses: list[ClauseOutcome]
    abstention_reason: str | None = None


class AttentionItem(BaseModel):
    """One area requiring attention — a review signal, never a legal conclusion."""

    attention_level: RelativeImportance
    area: str
    reason: str
    source_support: str
    practical_question: str


class AttentionOutput(BaseModel):
    """Attention analysis outcome (AI-Architecture.md §9)."""

    evidence_state: EvidenceState = Field(default=EvidenceState.DOCUMENT_GROUNDED)
    attention_items: list[AttentionItem]
    abstention_reason: str | None = None


class QAOutput(BaseModel):
    """Grounding Q&A output (Prompt-Strategy.md §9)."""

    answer: str
    evidence_state: EvidenceState = Field(default=EvidenceState.DOCUMENT_GROUNDED)
    citations: list[Citation] = Field(default_factory=list)
    follow_up: str | None = None
    confidence: RelativeImportance = RelativeImportance.MEDIUM
    abstention_reason: str | None = Field(
        default=None,
        description="Required whenever evidence_state is INSUFFICIENT-EVIDENCE.",
    )


class ComparisonOutput(BaseModel):
    """One clause-level change between two document versions (Prompt-Strategy.md §10)."""

    change_type: ChangeType
    importance: RelativeImportance = RelativeImportance.MEDIUM
    before: str | None = None
    after: str | None = None
    explanation: str
    evidence_state: EvidenceState = Field(default=EvidenceState.DOCUMENT_GROUNDED)
    abstention_reason: str | None = None


class ActionItem(BaseModel):
    """A practical, non-directive next step for the user."""

    title: str
    priority: RelativeImportance
    reason: str
    source: dict[str, str] = Field(default_factory=dict)
    practical_question: str | None = None


class ActionOutput(BaseModel):
    """Action generation outcome (Prompt-Strategy.md §11)."""

    evidence_state: EvidenceState = Field(default=EvidenceState.DOCUMENT_GROUNDED)
    actions: list[ActionItem]
    abstention_reason: str | None = None


class ProfessionalItem(BaseModel):
    """A question to discuss with a qualified professional (FR-015)."""

    question: str
    source: dict[str, str] = Field(default_factory=dict)


class ProfessionalQuestionsOutput(BaseModel):
    """Professional-question generation outcome (Prompt-Strategy.md §9).

    Every question must reference the supplied evidence; the service drops any
    question whose source cannot be resolved to a real clause.
    """

    evidence_state: EvidenceState = Field(default=EvidenceState.DOCUMENT_GROUNDED)
    questions: list[ProfessionalItem]
    abstention_reason: str | None = None


EvidenceStateLiteral = Literal["DOCUMENT-GROUNDED", "GENERAL-INFORMATION", "INSUFFICIENT-EVIDENCE"]