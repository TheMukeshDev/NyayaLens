"""Document-grounded Q&A schemas (docs/03_TECH/API-Specification.md §15-§16).

The response answers a question about a single owned document. Honesty contract:

* ``answer`` is ``None`` and ``evidence_state`` is ``INSUFFICIENT-EVIDENCE``
  whenever the service has no validated evidence to answer from — the backend
  never guesses.
* Every citation is backend-resolved and ownership-checked before it appears
  here; fabricated or cross-user chunks are dropped.
* ``related_sections`` is only populated when the answer is document-grounded.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.prompts.schemas import EvidenceState


class QuoteRequest(BaseModel):
    """A single document-grounded question about one owned document."""

    question: str = Field(
        min_length=1,
        max_length=2000,
        description="The question to answer from the document.",
    )


class CitationOut(BaseModel):
    """One backend-verified citation with its exact source location."""

    id: str
    chunk_id: UUID
    document_id: UUID
    section_id: UUID | None = None
    clause_id: UUID | None = None
    section: str
    clause: str | None = None
    page_start: int
    page_end: int | None = None
    source_text: str


class RelatedSectionOut(BaseModel):
    """A referenced section, for further reading (document-grounded only)."""

    label: str
    section_id: UUID | None = None
    page_start: int | None = None
    page_end: int | None = None


class QAAnswerOut(BaseModel):
    """The complete answer to one question, with provenance."""

    document_id: UUID
    answer: str | None = None
    evidence_state: EvidenceState
    citations: list[CitationOut] = Field(default_factory=list)
    related_sections: list[RelatedSectionOut] = Field(default_factory=list)
    abstention_reason: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None