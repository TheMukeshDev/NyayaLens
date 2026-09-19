"""Deterministic section detection (heuristic, not AI).

Sections are contiguous line ranges headed by a heading line. Headings are
recognized from document structure only (numbering, section/article/clause
keywords, typography) — never from semantics. This is structural parsing, not
legal interpretation (docs/03_TECH/System-Architecture.md §19).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.document_processing.models import LineRef

_MAX_HEADING_TEXT = 120

_NUMBERED_KEYWORD = re.compile(
    r"^\s*(?:SECTION|ARTICLE|CLAUSE)\s+([0-9]+(?:\.[0-9]+)*)\s*[-–—:.)]*\s*(.*?)\s*$",
    re.IGNORECASE,
)
_NUMBERED_PLAIN = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)*)[.)]\s+(.+?)\s*$")
_ALL_CAPS = re.compile(r"^\s*([A-Z][A-Z0-9 &'()/-]{3,80}?)\s*$")


@dataclass(frozen=True)
class SectionHeading:
    """A detected heading: its line index, number (if any) and title."""

    line_index: int
    number: str | None
    title: str | None


def detect_sections(lines: list[LineRef]) -> list[SectionHeading]:
    """Return detected section headings in document order.

    A plain-numbered or all-caps heading is only accepted directly after a
    blank line (or the start of the document/page), which keeps body text out;
    explicit ``SECTION/ARTICLE/CLAUSE n`` headings are always accepted.
    """
    headings: list[SectionHeading] = []
    prev_blank = True
    prev_line_page: int | None = None

    for index, line in enumerate(lines):
        text = line.text.strip()
        if not text:
            prev_blank = True
            prev_line_page = None
            continue

        heading = _heading_for(text)
        if heading is not None:
            # A heading is accepted after a blank line or at the top of a new
            # page; explicit SECTION/ARTICLE/CLAUSE headings are always
            # accepted. Clearly-marked headings (all-caps or near-capitalized
            # titles such as "1. NON-COMPETE") are accepted even without a
            # preceding blank, because PDF text extraction often collapses the
            # blank lines pypdf's visitor would otherwise emit.
            at_gate = prev_blank or (
                line.page is not None
                and prev_line_page is not None
                and line.page != prev_line_page
            )
            if _is_force_heading(text) or at_gate or _is_strong_heading(heading):
                headings.append(
                    SectionHeading(
                        line_index=index, number=heading[0], title=heading[1]
                    )
                )

        prev_blank = False
        prev_line_page = line.page
    return headings


def section_bounds(
    lines: list[LineRef], headings: list[SectionHeading]
) -> list[tuple[int, int, str | None, str | None, bool]]:
    """Return ``(content_start, content_end, number, title, is_heading)`` spans.

    A preamble span (``is_heading=False``) covers leading text before the first
    heading, when there is any; one span is produced per heading, with the
    heading line itself excluded from the content.
    """
    spans: list[tuple[int, int, str | None, str | None, bool]] = []
    if headings:
        first_heading_index = headings[0].line_index
        if any(lines[index].text.strip() for index in range(first_heading_index)):
            spans.append((0, first_heading_index, None, "Preamble", False))
    if not headings:
        return [(0, len(lines), None, None, False)]
    for index, heading in enumerate(headings):
        end = headings[index + 1].line_index if index + 1 < len(headings) else len(lines)
        spans.append((heading.line_index + 1, end, heading.number, heading.title, True))
    return spans


def _heading_for(text: str) -> tuple[str | None, str | None] | None:
    match = _NUMBERED_KEYWORD.match(text)
    if match:
        return match.group(1), _clean_title(match.group(2))
    match = _NUMBERED_PLAIN.match(text)
    if match:
        number = match.group(1)
        title = match.group(2)
        # Bare sub-numbered items ("1.1 Restrictions...") are clause-level
        # markers, handled by clause_detector, not section headings.
        if "." in number:
            return None
        if len(text) > _MAX_HEADING_TEXT:
            return None
        if not _looks_like_heading_title(title):
            return None
        return number, _clean_title(title)
    if _ALL_CAPS.match(text):
        return None, text
    return None


def _is_strong_heading(heading: tuple[str | None, str | None]) -> bool:
    """True when a heading is clearly marked even without a blank-line gate.

    Accepts all-caps titles ("1. NON-COMPETE") and terse capitalized titles
    with at most one lowercase-initial word ("Definitions", "Intellectual
    Property"), while rejecting sentence fragments ("1. The parties shall pay
    the sum of...") that merely look numbered.
    """
    title = heading[1] or ""
    if not title:
        return False
    if title.isupper():
        return True
    words = [word for word in re.split(r"\W+", title) if word]
    lowercase_initial = sum(1 for word in words if word[0].islower())
    return lowercase_initial <= 1


def _is_force_heading(text: str) -> bool:
    """Explicit section/article/clause headings are always verbatim headings."""
    return bool(_NUMBERED_KEYWORD.match(text))


def _looks_like_heading_title(title: str) -> bool:
    if not title:
        return True
    # A heading title does not read like a sentence: it starts capitalized (or
    # quoted) and does not end with sentence punctuation unless very short.
    if not title[0].isupper() and title[0] not in '"\u201c(':
        return False
    stripped = title.rstrip(".?!;")
    return not (title != stripped and len(stripped) > 60)


def _clean_title(title: str) -> str | None:
    text = title.strip().rstrip(".?!;:").strip()
    return text or None