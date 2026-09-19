"""Pipeline orchestrator: extract -> map -> sections -> clauses -> entities -> chunks.

Implements the processing pipeline described in docs/03_TECH/System-Architecture.md
§19 and docs/01_PRODUCT/FEATURE-REQUIREMENTS.md FR-003 (the deterministic part,
up to and including chunking). No AI interpretation occurs here, and no text is
ever invented: empty or unreliable pages become recorded uncertainties, and a
document with no extractable text raises :class:`ProcessingTextEmptyError` so
the caller can fail it honestly.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.document_processing.chunker import Chunker
from app.document_processing.clause_detector import (
    clause_type_from_title,
    detect_clause_markers,
)
from app.document_processing.entities import extract_entities
from app.document_processing.extractor import (
    TextExtractor,
    aggregate_uncertainties,
)
from app.document_processing.models import (
    ExtractedChunk,
    ExtractedClause,
    ExtractedSection,
    ExtractedText,
    LineRef,
    ProcessingResult,
)
from app.document_processing.section_parser import (
    detect_sections,
    section_bounds,
)


class ProcessingTextEmptyError(RuntimeError):
    """Raised when a document yields no extractable text at all."""


class DocumentProcessingPipeline:
    """Runs the deterministic document-processing steps end to end."""

    def __init__(self, *, extractor: TextExtractor, chunker: Chunker | None = None) -> None:
        self._extractor = extractor
        self._chunker = chunker or Chunker()

    def process(
        self,
        *,
        document_id: UUID,
        content: bytes,
        mime_type: str,
    ) -> ProcessingResult:
        extracted = self._extractor.extract(content=content, mime_type=mime_type)
        if not extracted.total_text().strip():
            raise ProcessingTextEmptyError(
                "No extractable text was found. The file may be a scanned image "
                "requiring OCR or it may be unreadable. No text was fabricated."
            )

        lines = _line_map(extracted)
        headings = detect_sections(lines)
        spans = section_bounds(lines, headings)

        sections = _build_sections(lines, spans)
        clauses = _build_clauses(lines, sections, spans)

        for section in sections:
            section.entities = extract_entities(section.content, page=section.page_start)
        for clause in clauses:
            clause.entities = extract_entities(clause.content, page=clause.page_start)

        chunks = self._chunker.chunk(
            document_id=document_id, sections=sections, clauses=clauses
        )
        attach_page_uncertainties(chunks, extracted)

        return ProcessingResult(
            document_id=document_id,
            format=extracted.format,
            page_count=extracted.page_count(),
            uncertainties=aggregate_uncertainties(extracted),
            sections=sections,
            clauses=clauses,
            chunks=chunks,
        )


def _line_map(extracted: ExtractedText) -> list[LineRef]:
    """Flatten extracted pages into ordered lines carrying their page numbers."""
    lines: list[LineRef] = []
    for page in extracted.pages:
        for line_text in page.text.split("\n"):
            lines.append(LineRef(page=page.page_number, text=line_text))
    return lines


def _build_sections(
    lines: list[LineRef], spans: list[tuple[int, int, str | None, str | None, bool]]
) -> list[ExtractedSection]:
    """Build one section per span; ``sequence`` equals the span index so that
    clauses can be re-associated by position without risking drift."""
    sections: list[ExtractedSection] = []
    for index, (start, end, number, title, _is_heading) in enumerate(spans):
        body_lines = lines[start:end]
        sections.append(
            ExtractedSection(
                number=number,
                title=title,
                content=_join_lines(body_lines),
                page_start=_min_page(body_lines),
                page_end=_max_page(body_lines),
                sequence=index,
                id=uuid4(),
            )
        )
    return sections


def _build_clauses(
    lines: list[LineRef],
    sections: list[ExtractedSection],
    spans: list[tuple[int, int, str | None, str | None, bool]],
) -> list[ExtractedClause]:
    """Detect clauses within each section's content span."""
    clauses: list[ExtractedClause] = []
    for span_index, (start, end, _number, _title, _is_heading) in enumerate(spans):
        section = sections[span_index]
        markers = detect_clause_markers(lines, start, end)
        for marker_index, marker in enumerate(markers):
            clause_start = marker.line_index
            clause_end = (
                markers[marker_index + 1].line_index
                if marker_index + 1 < len(markers)
                else end
            )
            body_lines = lines[clause_start:clause_end]
            body = _join_lines(body_lines)
            if not body.strip():
                continue
            marker_page = lines[marker.line_index].page
            clauses.append(
                ExtractedClause(
                    section_sequence=section.sequence,
                    number=marker.number,
                    title=marker.title,
                    content=body,
                    page_start=marker_page,
                    page_end=_max_page(body_lines) or marker_page,
                    sequence=len(clauses),
                    clause_type=clause_type_from_title(marker.title),
                    confidence=None,
                    entities=[],
                    id=uuid4(),
                    section_id=section.id,
                )
            )
    return clauses


def _join_lines(lines: list[LineRef]) -> str:
    return "\n".join(line.text for line in lines)


def _min_page(lines: list[LineRef]) -> int | None:
    pages = [line.page for line in lines if line.page is not None]
    return min(pages) if pages else None


def _max_page(lines: list[LineRef]) -> int | None:
    pages = [line.page for line in lines if line.page is not None]
    return max(pages) if pages else None


def attach_page_uncertainties(chunks: list[ExtractedChunk], extracted: ExtractedText) -> None:
    """Propagate page-level uncertainties onto chunks covering those pages."""
    pages_by_number = {page.page_number: page for page in extracted.pages}
    for chunk in chunks:
        covered: list[int] = []
        if chunk.page_start is not None and chunk.page_end is not None:
            covered = list(range(chunk.page_start, chunk.page_end + 1))
        existing: set[str] = set()
        messages: list[str] = []
        raw = chunk.metadata.get("uncertainties")
        if isinstance(raw, list):
            for item in raw:
                messages.append(str(item))
                existing.add(str(item))
        for number in covered:
            source = pages_by_number.get(number)
            if source is None:
                continue
            for uncertainty in source.uncertainties:
                if uncertainty.message not in existing:
                    messages.append(uncertainty.message)
        chunk.metadata["uncertainties"] = messages