"""Clause-aware chunking that preserves source metadata (RAG-Architecture §4-§5).

Chunks follow document semantics instead of blind fixed-size splits: a chunk is
one clause (or one clause-less section, or the preamble) when short enough,
and only oversized blocks are split further at natural boundaries. Every chunk
carries its section/clause ids and labels, page range, source location,
confidence, recorded uncertainties and extracted entities — the fields required
for traceable citations (AI-Architecture.md §6 and §31).
"""

from __future__ import annotations

import re
from uuid import UUID

from app.document_processing.models import (
    ExtractedChunk,
    ExtractedClause,
    ExtractedSection,
)

DEFAULT_MAX_CHARS = 4000  # ~500-1000 tokens (RAG-Architecture.md §5)
_MIN_CHARS = 700
_SENTENCE_BOUNDARY = re.compile(r"[.!?]\s+")


def section_label(section: ExtractedSection | None) -> str | None:
    if section is None:
        return None
    if section.number and section.title:
        return f"{section.number} {section.title}".strip()
    return section.title or section.number or "Preamble"


def clause_label(clause: ExtractedClause | None) -> str | None:
    if clause is None:
        return None
    if clause.number and clause.title:
        return f"{clause.number} {clause.title}".strip()
    return clause.number or clause.title


class Chunker:
    """Builds retrieval chunks from detected sections and clauses."""

    def __init__(self, *, max_chunk_chars: int = DEFAULT_MAX_CHARS) -> None:
        self._max_chunk_chars = max_chunk_chars

    def chunk(
        self,
        *,
        document_id: UUID,
        sections: list[ExtractedSection],
        clauses: list[ExtractedClause],
    ) -> list[ExtractedChunk]:
        blocks = self._build_blocks(sections, clauses)
        chunks: list[ExtractedChunk] = []
        index = 0
        for section, clause in blocks:
            for piece in self._split_section_text(
                self._block_text(section, clause), self._max_chunk_chars
            ):
                chunk = self._make_chunk(
                    document_id=document_id,
                    section=section,
                    clause=clause,
                    content=piece,
                    index=index,
                )
                chunks.append(chunk)
                index += 1
        return chunks

    # -- block assembly ----------------------------------------------------------

    def _build_blocks(
        self,
        sections: list[ExtractedSection],
        clauses: list[ExtractedClause],
    ) -> list[tuple[ExtractedSection | None, ExtractedClause | None]]:
        """Pair each section with its clauses (or itself) in document order."""
        clauses_by_section: dict[int, list[ExtractedClause]] = {}
        for clause in clauses:
            clauses_by_section.setdefault(clause.section_sequence, []).append(clause)

        blocks: list[tuple[ExtractedSection | None, ExtractedClause | None]] = []
        for section in sections:
            own_clauses = clauses_by_section.get(section.sequence, [])
            if own_clauses:
                blocks.extend((section, clause) for clause in own_clauses)
            else:
                blocks.append((section, None))
        return blocks

    def _block_text(self, section: ExtractedSection | None, clause: ExtractedClause | None) -> str:
        if clause is not None:
            return clause.content
        if section is not None:
            return section.content
        return ""

    # -- splitting ---------------------------------------------------------------

    def _split_section_text(self, text: str, max_chars: int) -> list[str]:
        """Split a block into chunks, cutting only at natural boundaries."""
        pieces: list[str] = []
        remaining = text
        min_chars = min(_MIN_CHARS, max_chars // 2)
        while len(remaining) > max_chars:
            window = remaining[:max_chars]
            boundary = _best_boundary(window, min_chars)
            if boundary < min_chars:
                boundary = max_chars
            pieces.append(remaining[:boundary].strip())
            remaining = remaining[boundary:].lstrip("\n")
        pieces.append(remaining.strip())
        return [piece for piece in pieces if piece]

    def _make_chunk(
        self,
        *,
        document_id: UUID,
        section: ExtractedSection | None,
        clause: ExtractedClause | None,
        content: str,
        index: int,
    ) -> ExtractedChunk:
        page_start = _range_start(section, clause)
        page_end = _range_end(section, clause)
        uncertainties: list[str] = []
        split = False
        if len(content) > self._max_chunk_chars:
            split = True
            uncertainties.append(
                "The clause exceeded the chunk size limit and was split at a "
                "natural boundary; review the surrounding chunks for full context."
            )
        metadata: dict[str, object] = {
            "document_id": str(document_id),
            "section": section_label(section),
            "section_id": (str(section.id) if section and section.id else None),
            "clause": clause_label(clause),
            "clause_id": (str(clause.id) if clause and clause.id else None),
            "page_start": page_start,
            "page_end": page_end,
            "source_location": _source_location(section, clause, page_start),
            "confidence": _confidence(clause),
            "uncertainties": uncertainties,
            "split": split,
            "entities": _entities_payload(section, clause),
        }
        return ExtractedChunk(
            document_id=document_id,
            section_id=section.id if section else None,
            clause_id=clause.id if clause else None,
            content=content,
            page_start=page_start,
            page_end=page_end,
            index=index,
            token_count=len(content.split()),
            metadata=metadata,
        )


# -- helpers -------------------------------------------------------------------

def _range_start(
    section: ExtractedSection | None, clause: ExtractedClause | None
) -> int | None:
    candidates = [
        page
        for page in (
            clause.page_start if clause else None,
            section.page_start if section else None,
        )
        if page is not None
    ]
    return min(candidates) if candidates else None


def _range_end(section: ExtractedSection | None, clause: ExtractedClause | None) -> int | None:
    candidates = [
        page
        for page in (
            clause.page_end if clause else None,
            section.page_end if section else None,
        )
        if page is not None
    ]
    return max(candidates) if candidates else None


def _confidence(clause: ExtractedClause | None) -> float | None:
    return clause.confidence if clause else None


def _source_location(
    section: ExtractedSection | None,
    clause: ExtractedClause | None,
    page: int | None,
) -> str:
    parts: list[str] = []
    if page is not None:
        parts.append(f"Page {page}")
    section_text = section_label(section)
    if section_text:
        parts.append(f"Section: {section_text}")
    clause_text = clause_label(clause)
    if clause_text:
        parts.append(f"Clause: {clause_text}")
    return " · ".join(parts) or "Unknown source"


def _entities_payload(
    section: ExtractedSection | None, clause: ExtractedClause | None
) -> list[dict[str, object]]:
    entities = (
        clause.entities
        if clause is not None
        else (section.entities if section is not None else [])
    )
    return [
        {
            "type": entity.type,
            "value": entity.value,
            "normalized": entity.normalized,
        }
        for entity in entities
    ]


def _best_boundary(window: str, min_chars: int) -> int:
    """Return the split position for *window*: farthest natural boundary."""
    paragraph = window.rfind("\n\n")
    if paragraph >= min_chars:
        return max(paragraph, min_chars)
    sentence = _last_sentence_end(window, min_chars)
    if sentence >= min_chars:
        return max(sentence, min_chars)
    space = window.rfind(" ")
    return space if space >= min_chars else -1


def _last_sentence_end(window: str, min_chars: int) -> int:
    positions = [
        match.end()
        for match in _SENTENCE_BOUNDARY.finditer(window)
        if match.end() >= min_chars
    ]
    return positions[-1] if positions else -1