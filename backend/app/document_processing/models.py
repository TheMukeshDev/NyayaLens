"""Types produced by the document processing pipeline.

The pipeline is strictly an *extraction* pipeline: it turns uploaded bytes into
structured sections, clauses, entities and retrieval chunks. It never performs
legal interpretation — no risk/attention/legality classification happens here
(docs/04_AI/AI-Architecture.md §4-§9, FR-003).

Uncertainty is first-class: every step that cannot be confident (empty pages,
poor OCR confidence, unsupported content) records an :class:`ExtractionUncertainty`
instead of guessing or fabricating text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class ExtractionUncertainty:
    """A recorded, non-fatal doubt raised while extracting content.

    ``code`` is machine-readable (see below) so downstream systems can surface
    the uncertainty instead of pretending certainty.
    """

    page: int | None
    code: str
    message: str


# Canonical uncertainty codes.
NO_TEXT = "NO_TEXT"  # a page/section produced no readable text
LOW_OCR_CONFIDENCE = "LOW_OCR_CONFIDENCE"  # OCR confidence below threshold
OCR_UNAVAILABLE = "OCR_UNAVAILABLE"  # the OCR engine could not run
EXTRACTION_FAILED = "EXTRACTION_FAILED"  # extractor error on a page
SPLIT_TRUNCATED = "SPLIT_TRUNCATED"  # a chunk had to be split and a boundary cut text


@dataclass(frozen=True)
class ExtractedPage:
    """Text extracted from a single logical page.

    For formats without real pagination (DOCX) the page is an approximation
    derived from explicit page breaks; ``page_number`` is then best-effort.
    """

    page_number: int
    text: str
    source: Literal["text", "ocr"]
    confidence: float | None = None
    uncertainties: list[ExtractionUncertainty] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractedText:
    """All text extraction output for one uploaded file."""

    format: Literal["pdf", "docx", "image"]
    pages: list[ExtractedPage] = field(default_factory=list)
    ocr_used: bool = False
    uncertainties: list[ExtractionUncertainty] = field(default_factory=list)

    def total_text(self) -> str:
        return "\n".join(page.text for page in self.pages)

    def page_count(self) -> int:
        return len(self.pages)


@dataclass(frozen=True)
class ExtractedEntity:
    """A deterministically extracted entity (never a legal judgment)."""

    type: str  # DATE | AMOUNT | PARTY | CROSS_REFERENCE
    value: str
    normalized: str | None = None
    page: int | None = None


@dataclass
class ExtractedSection:
    """A detected document section and its line range in the extracted text."""

    number: str | None
    title: str | None
    content: str
    page_start: int | None
    page_end: int | None
    sequence: int
    id: UUID | None = None
    parent_section_id: UUID | None = None
    entities: list[ExtractedEntity] = field(default_factory=list)


@dataclass
class ExtractedClause:
    """A detected clause within a section."""

    section_sequence: int
    number: str | None
    title: str | None
    content: str
    page_start: int | None
    page_end: int | None
    sequence: int
    clause_type: str | None = None
    confidence: float | None = None
    entities: list[ExtractedEntity] = field(default_factory=list)
    id: UUID | None = None
    section_id: UUID | None = None


@dataclass
class ExtractedChunk:
    """A retrieval chunk that preserves its exact source location.

    ``metadata`` carries: document_id, section/clause labels and ids, page
    start/end, source location, extraction confidence and uncertainties — the
    fields required for traceable citations (AI-Architecture.md §6, §31).
    """

    document_id: UUID
    section_id: UUID | None
    clause_id: UUID | None
    content: str
    page_start: int | None
    page_end: int | None
    index: int
    token_count: int
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LineRef:
    """A single line of extracted text with its page number (when known)."""

    page: int | None
    text: str


@dataclass
class ProcessingResult:
    """Everything the pipeline produced for one document."""

    document_id: UUID
    format: str
    page_count: int
    uncertainties: list[ExtractionUncertainty]
    sections: list[ExtractedSection]
    clauses: list[ExtractedClause]
    chunks: list[ExtractedChunk]